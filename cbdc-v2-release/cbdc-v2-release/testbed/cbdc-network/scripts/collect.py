#!/usr/bin/env python3
"""
collect.py : measurement collection for the CBDC prototype (step 7b). Called by 07_benchmark.sh, once per round.

  split    <bench.yaml> <outdir>          write one benchmark file per round (each round is run as its own Caliper launch,
                                          so metrics snapshots and log windows have exact boundaries)
  env      <outdir>                       record versions, host, Raft leader
  snapshot <dir>                          save /metrics of all 8 nodes (A: before/after snapshots)
  extract  <rounddir> <t0> <t1>           save container logs for [t0, t1] (UTC, RFC3339) and parse them into CSV files (C)
  summarize <rounddir>                    per-round summary.json from snapshots, CSVs and docker_stats.csv (D)
  report   <outdir>                       one table over all rounds, with the send-rate check

Sources (verified on Fabric 2.5.14, build log entry 7a):
  metrics : endorser_proposal_duration, grpc_server_unary_request_duration (gateway Endorse/Submit/CommitStatus),
            ledger_transaction_count (by validation_code), blockcutter_block_fill_duration (leader only),
            consensus_etcdraft_is_leader, consensus_etcdraft_leader_changes, consensus_etcdraft_data_persist_duration,
            ledger_block_processing_time, ledger_statedb_commit_time
  logs    : peer "Validated block [N] in Xms", peer "Committed block [N] with K transaction(s) in Yms (...)",
            leader "Created block [N]", orderer "Writing block [N] (Raft index: I)",
            gateway "unary call completed grpc.service=gateway.Gateway grpc.method=M ... grpc.code=C grpc.call_duration=D"
Log timestamps have 1 ms resolution; durations below a few ms are therefore quantised (stated in the paper).
"""
import csv, gzip, json, math, os, re, statistics, subprocess, sys, time
from datetime import datetime, timezone

PEERS = [(f"peer0.inst{i}.cbdc.example", 9445 + i) for i in range(1, 6)]      # ops ports 9446..9450
ORDERERS = [(f"orderer{k}.cb.cbdc.example", 9442 + k) for k in range(1, 4)]  # ops ports 9443..9445
NODES = ORDERERS + PEERS

# ---------------------------------------------------------------- Prometheus text format
LINE = re.compile(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{(.*)\})?\s+(\S+)$')
LABEL = re.compile(r'(\w+)="((?:[^"\\]|\\.)*)"')

def parse_metrics(text):
    """List of (name, labels dict, value) for every sample line."""
    out = []
    for ln in text.splitlines():
        if not ln or ln.startswith('#'):
            continue
        m = LINE.match(ln)
        if m:
            out.append((m.group(1), dict(LABEL.findall(m.group(3) or '')), float(m.group(4))))
    return out

def total(samples, name, **want):
    return sum(v for n, l, v in samples if n == name and all(l.get(k) == x for k, x in want.items()))

def load_snap(d, host):
    p = os.path.join(d, host + '.txt')
    return parse_metrics(open(p).read()) if os.path.exists(p) else []

# ---------------------------------------------------------------- log parsing
TS = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3}) UTC')
R_VAL = re.compile(r'Validated block \[(\d+)\] in (\d+)ms')
R_COM = re.compile(r'Committed block \[(\d+)\] with (\d+) transaction\(s\) in (\d+)ms \(state_validation=(\d+)ms '
                   r'block_and_pvtdata_commit=(\d+)ms state_commit=(\d+)ms\)')
R_CRE = re.compile(r'Created block \[(\d+)\]')
R_WRI = re.compile(r'Writing block \[(\d+)\] \(Raft index: (\d+)\)')
R_GW = re.compile(r'unary call completed grpc\.service=gateway\.Gateway grpc\.method=(\w+) .*?grpc\.code=(\w+) '
                  r'grpc\.call_duration=([0-9.]+)(ns|µs|us|ms|s)\b')
UNIT = {'ns': 1e-6, 'µs': 1e-3, 'us': 1e-3, 'ms': 1.0, 's': 1000.0}

ANSI = re.compile(r'\x1b\[[0-9;]*m')   # Fabric's default log format colours the time and level

def ts_of(line):
    m = TS.match(line)
    if not m:
        return None
    return datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc).timestamp()

def parse_logs(texts):
    """texts: {host: log text}. Returns rows for blocks_peer, blocks_orderer, gateway_calls."""
    bp, bo, gw = [], {}, []
    for host, text in texts.items():
        val = {}
        for ln in text.splitlines():
            ln = ANSI.sub('', ln)
            t = ts_of(ln)
            if t is None:
                continue
            if host.startswith('peer'):
                m = R_VAL.search(ln)
                if m:
                    val[int(m.group(1))] = (t, int(m.group(2))); continue
                m = R_COM.search(ln)
                if m:
                    b = int(m.group(1)); v = val.get(b, (None, None))
                    bp.append(dict(peer=host, block=b, n_tx=int(m.group(2)), validated_utc=v[0], validate_ms=v[1],
                                   committed_utc=t, commit_ms=int(m.group(3)), state_validation_ms=int(m.group(4)),
                                   block_commit_ms=int(m.group(5)), state_commit_ms=int(m.group(6))))
                    continue
                m = R_GW.search(ln)
                if m:
                    gw.append(dict(peer=host, method=m.group(1), code=m.group(2), end_utc=t,
                                   duration_ms=float(m.group(3)) * UNIT[m.group(4)]))
            else:
                m = R_CRE.search(ln)
                if m:
                    bo.setdefault(int(m.group(1)), {})['created_utc'] = t; bo[int(m.group(1))]['leader'] = host; continue
                m = R_WRI.search(ln)
                if m:
                    r = bo.setdefault(int(m.group(1)), {})
                    r.setdefault('written_utc', {})[host] = t
    orows = []
    for b in sorted(bo):
        r = bo[b]; w = r.get('written_utc', {}); ld = r.get('leader')
        orows.append(dict(block=b, leader=ld, created_utc=r.get('created_utc'),
                          written_leader_utc=w.get(ld) if ld else None,
                          written_first_utc=min(w.values()) if w else None, written_last_utc=max(w.values()) if w else None))
    return bp, orows, gw

def write_csv(path, rows):
    if not rows:
        open(path, 'w').close(); return
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

def read_csv(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return []
    with open(path) as f:
        return list(csv.DictReader(f))

# ---------------------------------------------------------------- statistics
def describe(xs):
    xs = [float(x) for x in xs if x not in (None, '')]
    if not xs:
        return None
    xs.sort(); n = len(xs); m = statistics.fmean(xs)
    v = statistics.variance(xs) if n > 1 else 0.0
    q = lambda p: xs[min(n - 1, int(math.ceil(p * n)) - 1)]
    return dict(n=n, mean=m, sd=math.sqrt(v), scv=(v / m ** 2) if m > 0 else None, p50=q(.5), p95=q(.95), p99=q(.99), max=xs[-1])

# ---------------------------------------------------------------- commands
def cmd_split(bench, outdir):
    import yaml
    b = yaml.safe_load(open(bench))
    rounds = b['test']['rounds']; os.makedirs(outdir, exist_ok=True); paths = []
    for i, r in enumerate(rounds, 1):
        one = json.loads(json.dumps(b)); one['test']['rounds'] = [r]
        p = os.path.join(outdir, f"{i:02d}-{r['label']}.yaml")
        yaml.safe_dump(one, open(p, 'w'), sort_keys=False); paths.append(p)
    print('\n'.join(paths))

def cmd_snapshot(d):
    import urllib.request
    os.makedirs(d, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'   # RFC3339, as docker logs --since expects
    for host, port in NODES:
        try:
            txt = urllib.request.urlopen(f'http://localhost:{port}/metrics', timeout=5).read().decode()
        except Exception as e:
            txt = f'# SCRAPE FAILED: {e}\n'
            print(f'   WARNING: metrics of {host} (port {port}) could not be read: {e}')
        open(os.path.join(d, host + '.txt'), 'w').write(txt)
    open(os.path.join(d, 'time_utc.txt'), 'w').write(stamp + '\n')

def leader_from(d):
    for host, _ in ORDERERS:
        if total(load_snap(d, host), 'consensus_etcdraft_is_leader', channel='cbdc') == 1:
            return host
    return None

def block_params():
    """MaxMessageCount and BatchTimeout from config/configtx.yaml (written by 01_generate.sh)."""
    try:
        t = open('config/configtx.yaml').read()
        b = re.search(r'MaxMessageCount:\s*(\d+)', t); tau = re.search(r'BatchTimeout:\s*(\S+)', t)
        return f"MaxMessageCount={b.group(1) if b else '?'} BatchTimeout={tau.group(1) if tau else '?'}"
    except OSError:
        return 'unknown (config/configtx.yaml not found)'

def cmd_env(outdir):
    def run(c):
        try:
            return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception as e:
            return f'error: {e}'
    tmp = os.path.join(outdir, 'env_metrics'); cmd_snapshot(tmp)
    c_cpu = 'grep -m1 "model name" /proc/cpuinfo'
    c_img = 'docker ps --format {{.Image}} | sort -u | tr "\\n" " "'
    c_dock = 'docker version --format {{.Server.Version}}'
    c_cal = 'cd caliper && npx caliper --version'
    cpus = os.environ.get('CLIENT_CPUS', '6,7')
    lines = [f'utc: {datetime.now(timezone.utc).isoformat()}', f'cpu: {run(c_cpu)}',
             f'threads: {run("nproc --all")}', f'mem: {run("free -m | grep Mem")}', f'kernel: {run("uname -r")}',
             f'docker: {run(c_dock)}', f'node: {run("node -v")}',
             f'npm: {run("npm -v")}', f'caliper: {run(c_cal)}',
             f'fabric images: {run(c_img)}',
             f'raft leader: {leader_from(tmp)}', f'block parameters: {block_params()}', f'client cpus: {cpus}']
    open(os.path.join(outdir, 'env.txt'), 'w').write('\n'.join(lines) + '\n'); print('\n'.join('   ' + l for l in lines))

def cmd_extract(rd, t0, t1):
    ld = os.path.join(rd, 'logs'); os.makedirs(ld, exist_ok=True); texts = {}
    for host, _ in NODES:
        p = subprocess.run(['docker', 'logs', host, '--since', t0, '--until', t1], capture_output=True, text=True)
        texts[host] = p.stdout + p.stderr
        with gzip.open(os.path.join(ld, host + '.log.gz'), 'wt') as f:
            f.write(texts[host])
    parse_and_write(rd, texts)

def parse_and_write(rd, texts):
    bp, bo, gw = parse_logs(texts)
    if not (bp or bo or gw):
        for h, t in texts.items():
            first = t.splitlines()[0] if t.strip() else ''
            print(f'   DIAGNOSTIC {h}: {len(t.splitlines())} log lines in window; first line: {first[:120]!r}')
    write_csv(os.path.join(rd, 'blocks_peer.csv'), bp); write_csv(os.path.join(rd, 'blocks_orderer.csv'), bo)
    write_csv(os.path.join(rd, 'gateway_calls.csv'), gw)
    print(f'   logs parsed: {len(bo)} blocks at the orderers, {len(bp)} peer commits, {len(gw)} gateway calls')

def cmd_reparse(rd):
    """Parse the logs already saved in <rounddir>/logs again (after a parser fix), without rerunning the round."""
    texts = {}
    for host, _ in NODES:
        p = os.path.join(rd, 'logs', host + '.log.gz')
        texts[host] = gzip.open(p, 'rt').read() if os.path.exists(p) else ''
    parse_and_write(rd, texts)

RESTARTED = set()

def delta(rd, host, name, **want):
    """after - before; if the node restarted during the round its counters began again from 0 (after < before),
    so only the part since the restart is known: return 'after' and remember the node as restarted."""
    a = total(load_snap(os.path.join(rd, 'metrics_after'), host), name, **want)
    b = total(load_snap(os.path.join(rd, 'metrics_before'), host), name, **want)
    if a < b:
        RESTARTED.add(host); return a
    return a - b

def hist_mean(rd, host, name, **want):
    c = delta(rd, host, name + '_count', **want); s = delta(rd, host, name + '_sum', **want)
    return (s / c, c) if c > 0 else (None, 0)

def cmd_summarize(rd):
    S = {}
    before = os.path.join(rd, 'metrics_before'); after = os.path.join(rd, 'metrics_after')
    S['leader_before'], S['leader_after'] = leader_from(before), leader_from(after)
    if not S['leader_after']:
        print('   WARNING: no Raft leader found in the metrics snapshot: counters below are not usable for this round')
    if S['leader_before'] != S['leader_after']:
        print(f"   NOTE: Raft leader changed during the round ({S['leader_before']} -> {S['leader_after']})")
    S['leader_changes'] = {h: delta(rd, h, 'consensus_etcdraft_leader_changes', channel='cbdc') for h, _ in ORDERERS}
    ld = S['leader_after'] or S['leader_before']
    if ld:
        m, c = hist_mean(rd, ld, 'blockcutter_block_fill_duration', channel='cbdc')
        S['block_fill_s'] = dict(mean=m, blocks=c)
        m, c = hist_mean(rd, ld, 'consensus_etcdraft_data_persist_duration', channel='cbdc')
        S['raft_persist_s_leader'] = dict(mean=m, n=c)
        m, c = hist_mean(rd, ld, 'etcd_disk_wal_fsync_duration_seconds')
        S['raft_fsync_ms_leader'] = dict(mean=1000 * m if m is not None else None, n=c)   # disk health indicator
    per = {}
    for h, _ in PEERS:
        e = {}
        for ok in ('true', 'false'):
            m, c = hist_mean(rd, h, 'endorser_proposal_duration', chaincode='wallet', channel='cbdc', success=ok)
            e[ok] = dict(count=c, mean_s=m)
        g = {}
        for meth in ('Endorse', 'Submit', 'CommitStatus'):
            for code in ('OK', 'Aborted'):
                m, c = hist_mean(rd, h, 'grpc_server_unary_request_duration', service='gateway_Gateway', method=meth, code=code)
                if c:
                    g[f'{meth}_{code}'] = dict(count=c, mean_s=m)
        v = {code: delta(rd, h, 'ledger_transaction_count', chaincode='wallet:1.0', channel='cbdc', validation_code=code)
             for code in ('VALID', 'MVCC_READ_CONFLICT', 'ENDORSEMENT_POLICY_FAILURE', 'PHANTOM_READ_CONFLICT')}
        m, c = hist_mean(rd, h, 'ledger_block_processing_time', channel='cbdc')
        per[h] = dict(endorsements=e, gateway=g, validation_codes=v, block_processing_s=dict(mean=m, blocks=c))
    S['peers'] = per
    allend = sum(p['endorsements']['true']['count'] + p['endorsements']['false']['count'] for p in per.values())
    S['endorsement_share'] = {h: (p['endorsements']['true']['count'] + p['endorsements']['false']['count']) / allend
                              if allend else None for h, p in per.items()}
    calls = sum(p['gateway'].get('Endorse_OK', {}).get('count', 0) + p['gateway'].get('Endorse_Aborted', {}).get('count', 0)
                for p in per.values())
    S['endorsements_per_tx'] = allend / calls if calls else None   # = Q of the endorsement policy
    S['endorse_ms_peer_mean'] = (1000 * sum((p['endorsements']['true']['mean_s'] or 0) * p['endorsements']['true']['count'] for p in per.values())
                                 / max(1, sum(p['endorsements']['true']['count'] for p in per.values())))
    S['endorse_mismatch_aborted'] = sum(p['gateway'].get('Endorse_Aborted', {}).get('count', 0) for p in per.values())
    S['mvcc_conflicts'] = per[PEERS[0][0]]['validation_codes']['MVCC_READ_CONFLICT']
    S['valid'] = per[PEERS[0][0]]['validation_codes']['VALID']
    S['restarted_nodes'] = sorted(RESTARTED)   # counters of these nodes cover only the time since their restart
    S['peers_agree_on_validation'] = len({json.dumps(p['validation_codes'], sort_keys=True)
                                          for h, p in per.items() if h not in RESTARTED}) == 1
    # per-event distributions (milliseconds)
    bp = read_csv(os.path.join(rd, 'blocks_peer.csv')); bo = read_csv(os.path.join(rd, 'blocks_orderer.csv'))
    gw = read_csv(os.path.join(rd, 'gateway_calls.csv'))
    wb = {int(r['block']): r for r in bo}
    raft = [1000 * (float(r['written_leader_utc']) - float(r['created_utc'])) for r in bo
            if r['created_utc'] and r['written_leader_utc']]
    S['dist_ms'] = dict(raft_cut_to_written=describe(raft))
    sizes = [int(r['n_tx']) for r in bp if r['peer'] == PEERS[0][0]]
    # throughput over a steady window: blocks committed at inst1 more than 5 s after the first and 5 s before the last
    # commit (excludes start-up and the final drain, when the last block waits for the batch timeout)
    c1 = sorted((float(r['committed_utc']), int(r['n_tx'])) for r in bp if r['peer'] == PEERS[0][0])
    if len(c1) > 2 and c1[-1][0] - c1[0][0] > 15:
        a, b = c1[0][0] + float(os.environ.get('STEADY_SKIP_S', '5')), c1[-1][0] - 5  # campaign: STEADY_SKIP_S=60 (spec E2)
        ins = [n for t, n in c1 if a < t <= b]
        S['steady_window'] = dict(start_utc=a, end_utc=b, seconds=b - a, tx=sum(ins), blocks=len(ins), tps=sum(ins) / (b - a))
    else:
        S['steady_window'] = None
    S['block_size'] = dict(describe=describe(sizes), counts={str(k): sizes.count(k) for k in sorted(set(sizes))})
    for h, _ in PEERS:
        rows = [r for r in bp if r['peer'] == h]
        lag = [1000 * (float(r['committed_utc']) - float(wb[int(r['block'])]['written_leader_utc'])) for r in rows
               if int(r['block']) in wb and wb[int(r['block'])]['written_leader_utc']]
        S['dist_ms'][h] = dict(validate=describe([r['validate_ms'] for r in rows]), commit=describe([r['commit_ms'] for r in rows]),
                               written_to_committed=describe(lag))
    for meth in ('Endorse', 'Submit', 'CommitStatus'):
        S['dist_ms'][f'gateway_{meth}_OK'] = describe([r['duration_ms'] for r in gw if r['method'] == meth and r['code'] == 'OK'])
    # per-block spread of commit times across the 5 peers (the cause of endorsement mismatches)
    by = {}
    for r in bp:
        by.setdefault(int(r['block']), []).append(float(r['committed_utc']))
    S['dist_ms']['commit_spread_across_peers'] = describe([1000 * (max(v) - min(v)) for v in by.values() if len(v) == 5])
    # resources (D)
    st = read_csv(os.path.join(rd, 'docker_stats.csv')); cpu = {}
    for r in st:
        try:
            cpu.setdefault(r['container'], []).append(float(r['cpu_percent'].rstrip('%')))
        except (ValueError, KeyError):
            pass
    S['cpu_percent_mean'] = {k: round(statistics.fmean(v), 1) for k, v in sorted(cpu.items())}
    S['cpu_samples'] = max((len(v) for v in cpu.values()), default=0)
    json.dump(S, open(os.path.join(rd, 'summary.json'), 'w'), indent=1, default=str)
    f = lambda d, k='mean': (f"{d[k]:.1f}" if d and d.get(k) is not None else '-')
    print(f"   leader {S['leader_after']}  leader changes {sum(S['leader_changes'].values()):.0f}  "
          f"valid {S['valid']:.0f}  MVCC {S['mvcc_conflicts']:.0f}  mismatch {S['endorse_mismatch_aborted']:.0f}  "
          f"peers agree: {S['peers_agree_on_validation']}"
          + (f"  (restarted, counters partial: {', '.join(h.split('.')[0] + '.' + h.split('.')[1] for h in S['restarted_nodes'])})" if S['restarted_nodes'] else ''))
    fs = S.get('raft_fsync_ms_leader', {}).get('mean')
    lim = float(os.environ.get('FSYNC_LIMIT_MS', '10'))
    warm = os.path.basename(os.path.normpath(rd)).split('-', 1)[-1].startswith('warmup')
    if warm:   # disk health is judged on the warm-up round only: under heavy load fsync rises BECAUSE of the load (8b, 8d)
        S['disk_ok'] = None if fs is None else fs <= lim
        print(f"   disk health (warm-up): Raft fsync mean {fs:.1f} ms" if fs is not None else "   disk health: Raft fsync not available",
              f"  WARNING: above {lim:.0f} ms, disk slow: do not use this run" if S['disk_ok'] is False else "")
    else:
        S['disk_ok'] = None
        print(f"   Raft fsync mean {fs:.1f} ms (load-dependent; disk health is judged on the warm-up round)" if fs is not None else "   Raft fsync -")
    json.dump(S, open(os.path.join(rd, 'summary.json'), 'w'), indent=1, default=str)
    ept = S.get('endorsements_per_tx')
    print(f"   endorsements per transaction {ept:.2f}; mean time per endorsement at a peer {S['endorse_ms_peer_mean']:.1f} ms" if ept else "   endorsements per transaction -")
    print(f"   endorsement share per peer: " + ' '.join(f"{v:.3f}" if v is not None else '-' for v in S['endorsement_share'].values()))
    print(f"   mean ms: gateway Endorse {f(S['dist_ms']['gateway_Endorse_OK'])}, Raft cut->written {f(S['dist_ms']['raft_cut_to_written'])}, "
          f"inst1 written->committed {f(S['dist_ms'][PEERS[0][0]]['written_to_committed'])}, "
          f"commit spread across peers {f(S['dist_ms']['commit_spread_across_peers'])} (p99 {f(S['dist_ms']['commit_spread_across_peers'], 'p99')})")
    sw = S['steady_window']
    swt = f"{sw['tps']:.1f} TPS over {sw['seconds']:.0f} s" if sw else '-'
    print(f"   block size mean {f(S['block_size']['describe'])}; steady-window throughput {swt} "
          f"(all transactions in blocks, valid or not); CPU samples {S['cpu_samples']}")

def send_rate_rows(report_html, bench):
    import yaml
    html = open(report_html).read(); b = yaml.safe_load(open(bench))
    target = {r['label']: r['rateControl']['opts'].get('tps') for r in b['test']['rounds'] if r['rateControl']['type'] == 'fixed-rate'}
    summary = html.split('id="benchmarksummary"')[1].split('</table>')[0]
    out = []
    for r in re.findall(r'<tr>\s*(.*?)\s*</tr>', summary, re.S)[1:]:
        c = [re.sub('<.*?>', '', x).strip() for x in re.findall(r'<td>(.*?)</td>', r)]
        name, succ, fail, send, mx, mn, avg, thr = c[:8]
        out.append(dict(name=name, succ=succ, fail=fail, send=send, max=mx, avg=avg, thr=thr, target=target.get(name)))
    return out

def cmd_saturated(rd):
    """Exit 0 (stop the sweep) if this round saturated: steady throughput below 95% of the target rate, or the client
    could not reach the target send rate. Warm-up rounds never stop the sweep."""
    import yaml
    r = yaml.safe_load(open(os.path.join(rd, 'round.yaml')))['test']['rounds'][0]
    if r['label'].startswith('warmup'):
        sys.exit(1)
    target = r['rateControl']['opts'].get('tps')
    S = json.load(open(os.path.join(rd, 'summary.json'))); sw = S.get('steady_window') or {}
    rows = send_rate_rows(os.path.join(rd, 'report.html'), os.path.join(rd, 'round.yaml'))
    send = float(rows[0]['send']) if rows else 0.0
    tps = sw.get('tps')
    why = []
    if target and tps is not None and tps < 0.95 * target:   # no steady window = no per-block logs (e.g. log level WARNING): skip
        why.append(f'steady throughput {tps:.1f} TPS < 95% of target {target}')
    if target and send < 0.98 * target:
        why.append(f'client send rate {send:.1f} < 98% of target {target}')
    if why:
        print('   SATURATED: ' + '; '.join(why)); sys.exit(0)
    sys.exit(1)

def cmd_report(outdir):
    rows, ok, disk_bad = [], True, False
    for d in sorted(os.listdir(outdir)):
        rd = os.path.join(outdir, d)
        if not (os.path.isdir(rd) and os.path.exists(os.path.join(rd, 'report.html'))):
            continue
        S = json.load(open(os.path.join(rd, 'summary.json'))) if os.path.exists(os.path.join(rd, 'summary.json')) else {}
        for r in send_rate_rows(os.path.join(rd, 'report.html'), os.path.join(rd, 'round.yaml')):
            flag = ''
            if r['target']:
                short = (r['target'] - float(r['send'])) / r['target']
                flag = 'OK' if short <= 0.02 else f'INVALID: send rate {100 * short:.1f}% below target'
                ok &= short <= 0.02
            if S.get('disk_ok') is False:
                disk_bad = True
            rows.append((r, S, flag))
    print("== Summary (Caliper latencies in s; conflicts from peer counters)")
    print(f"   {'round':18s} {'succ':>6s} {'fail':>5s} {'target':>6s} {'sent':>6s} {'avg':>6s} {'max':>6s} {'MVCC':>5s} {'mism':>5s} {'fsync':>6s}  check")
    for r, S, flag in rows:
        print(f"   {r['name']:18s} {r['succ']:>6s} {r['fail']:>5s} {str(r['target']):>6s} {r['send']:>6s} {r['avg']:>6s} {r['max']:>6s} "
              f"{S.get('mvcc_conflicts', 0):>5.0f} {S.get('endorse_mismatch_aborted', 0):>5.0f} "
              f"{(S.get('raft_fsync_ms_leader') or {}).get('mean') or float('nan'):>6.1f}  {flag}")
    if disk_bad:
        print("== DISK SLOW in the warm-up round: the disk was unhealthy at the start; do not use this run")
    print("== All rounds reached their target send rate" if ok else "== Some rounds did NOT reach their target send rate: do not use them")
    print("   Use the steady-window throughput in each round's summary.json, not Caliper's whole-round figure (2 s drain).")

if __name__ == '__main__':
    c, a = sys.argv[1], sys.argv[2:]
    {'split': cmd_split, 'env': cmd_env, 'snapshot': cmd_snapshot, 'extract': cmd_extract,
     'summarize': cmd_summarize, 'report': cmd_report, 'reparse': cmd_reparse,
     'saturated': cmd_saturated}[c](*a)
