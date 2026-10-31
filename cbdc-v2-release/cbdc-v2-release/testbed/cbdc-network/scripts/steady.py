#!/usr/bin/env python3
"""
steady.py <rounddir> [bin_seconds]   (step 8c)
Time series of one round in bins (default 10 s): committed transactions per second at peer inst1, mean gateway Endorse
and CommitStatus durations (CommitStatus = time from submit until the client learns the commit, a per-call latency proxy),
and inst1 per-block validate+commit time. Then the MSER-5 rule (White 1997) on the CommitStatus series: the warm-up cut d
that minimises the variance of the mean of the remaining batches, sum((x - mean)^2) / (n - d)^2, with batches of 5 bins,
searched over the first half. Writes steady_series.csv in the round folder.
"""
import sys, os, csv, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import collect as c

rd = sys.argv[1]; w = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
bp = [r for r in c.read_csv(os.path.join(rd, 'blocks_peer.csv')) if r['peer'] == 'peer0.inst1.cbdc.example']
gw = c.read_csv(os.path.join(rd, 'gateway_calls.csv'))
t0 = min(float(r['committed_utc']) for r in bp)
nb = int((max(float(r['committed_utc']) for r in bp) - t0) // w) + 1
B = [dict(tx=0, blk=[], endorse=[], cstat=[]) for _ in range(nb)]
k = lambda t: int((t - t0) // w)
for r in bp:
    i = k(float(r['committed_utc'])); B[i]['tx'] += int(r['n_tx']); B[i]['blk'].append(float(r['validate_ms'] or 0) + float(r['commit_ms']))
for r in gw:
    i = k(float(r['end_utc']))
    if 0 <= i < nb and r['code'] == 'OK':
        if r['method'] == 'Endorse': B[i]['endorse'].append(float(r['duration_ms']))
        if r['method'] == 'CommitStatus': B[i]['cstat'].append(float(r['duration_ms']))
mean = lambda v: st.fmean(v) if v else float('nan')
rows = [dict(t_start_s=i * w, tps=b['tx'] / w, endorse_ms=mean(b['endorse']), commitstatus_ms=mean(b['cstat']),
             block_ms=mean(b['blk'])) for i, b in enumerate(B)]
rows = rows[:-1]   # last bin is partial (drain)
with open(os.path.join(rd, 'steady_series.csv'), 'w', newline='') as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
print(f"   {'t (s)':>6s} {'TPS':>6s} {'Endorse':>8s} {'CommitStatus':>12s} {'block':>7s}   (ms)")
for r in rows:
    print(f"   {r['t_start_s']:6.0f} {r['tps']:6.1f} {r['endorse_ms']:8.1f} {r['commitstatus_ms']:12.1f} {r['block_ms']:7.1f}")
x = [r['commitstatus_ms'] for r in rows if r['commitstatus_ms'] == r['commitstatus_ms']]
bat = [st.fmean(x[i:i + 5]) for i in range(0, len(x) - len(x) % 5, 5)]
ev = os.path.join(rd, 'events.txt')
if os.path.exists(ev):
    from datetime import datetime
    print('   events (seconds on the same axis):')
    for ln in open(ev):
        t, what = ln.split(' ', 1)
        print(f"     t = {datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp() - t0:6.0f} s  {what.strip()}")
best = None
for d in range(0, len(bat) // 2 + 1 if len(bat) >= 2 else 0):
    rest = bat[d:]; m = st.fmean(rest); v = sum((y - m) ** 2 for y in rest) / len(rest) ** 2
    if best is None or v < best[1]: best = (d, v, m)
if best:
    d = best[0]
    print(f"   MSER-5 warm-up cut: {d} batches = {d * 5 * w:.0f} s; mean CommitStatus after the cut {best[2]:.1f} ms "
          f"(batches of {5 * w:.0f} s: " + ' '.join(f'{y:.0f}' for y in bat) + ")")
