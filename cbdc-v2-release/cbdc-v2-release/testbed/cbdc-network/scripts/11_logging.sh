#!/usr/bin/env bash
# Step 8h: cost of the instrumentation (INFO log lines of every block and every gateway call).
# Runs benchmarks/logging.yaml once per log setting in LEVELS (default "info warning info": A-B-A against drift).
# Settings: info      everything at INFO (what steps 7-8g used)
#           warning   per-event lines off (no per-event CSVs; the metrics-based numbers remain)
#           selective WARNING except the per-BLOCK lines (kvledger, committer.txvalidator, orderer.consensus.etcdraft):
#                     keeps blocks_peer.csv / blocks_orderer.csv, drops the per-call gateway lines
# The level is changed on the running nodes through the operations service (PUT /logspec), no restart.
# Usage: ./scripts/11_logging.sh            LEVELS="selective warning selective" ./scripts/11_logging.sh
set -euo pipefail
cd "$(dirname "$0")/.."
LEVELS="${LEVELS:-info warning info}"
spec() { case "$1" in info) echo info;; warning) echo warning;;
         selective) echo "warning:kvledger,committer.txvalidator,orderer.consensus.etcdraft=info";; *) echo "$1";; esac; }
setlog() { local s; s=$(spec "$1"); for p in 9443 9444 9445 9446 9447 9448 9449 9450; do
             curl -s -X PUT "localhost:$p/logspec" -d "{\"spec\":\"$s\"}" -o /dev/null -w "%{http_code} "; done; echo; }
n=0; RUNS=()
for L in $LEVELS; do
  n=$((n+1)); echo -n "== log setting $L: "; setlog "$L"; curl -s localhost:9446/logspec; echo
  STOP_AT_SATURATION=0 ./scripts/07_benchmark.sh benchmarks/logging.yaml "logging-$n-$L"
  RUNS+=("$(ls -d caliper/results/*-logging-$n-$L | tail -1)")
done
setlog info >/dev/null; echo "== log level set back to INFO"
echo "== Comparison (100 TPS round; from metrics, so valid for every setting)"
python3 - "${RUNS[@]}" <<'PY'
import glob, json, os, sys, re
for run in sys.argv[1:]:
    rd = glob.glob(run + '/02-*/')[0]; S = json.load(open(rd + 'summary.json'))
    pe = S['endorse_ms_peer_mean']; gw = [p['gateway'].get('Endorse_OK', {}).get('mean_s') for p in S['peers'].values()]
    gw = [g for g in gw if g]; bpt = [p['block_processing_s']['mean'] for p in S['peers'].values() if p['block_processing_s']['mean']]
    cpu = sum(S.get('cpu_percent_mean', {}).values())
    print(f"   {os.path.basename(run)[16:]:22s} peer endorse {pe:6.1f} ms | gateway Endorse {1000*sum(gw)/len(gw):6.1f} ms | "
          f"block processing {1000*sum(bpt)/len(bpt):5.1f} ms | MVCC {S['mvcc_conflicts']:4.0f} | CPU {cpu:4.0f}%")
PY
