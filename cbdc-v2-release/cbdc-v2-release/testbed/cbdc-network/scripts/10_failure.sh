#!/usr/bin/env bash
# Step 8g: two-of-five endorsing-peer failure on the real network (spec G1).
# Runs benchmarks/failure.yaml; 50 s after the 150 s round starts it stops peer0.inst4 and peer0.inst5 (docker stop),
# 50 s later starts them again, and records the event times in events.txt in the round folder. With the policy
# OutOf(3 of 5), the 3 remaining peers can still endorse every transaction: the gateways must notice the failure
# (service discovery) and send all endorsements to Inst1-3. After the restart, peers 4 and 5 catch up the missed blocks.
# Usage: ./scripts/10_failure.sh      (env: STOP_AT=50 DOWN_FOR=50 FAIL="4 5")
set -euo pipefail
cd "$(dirname "$0")/.."
STOP_AT="${STOP_AT:-50}"; DOWN_FOR="${DOWN_FOR:-50}"; FAIL="${FAIL:-4 5}"
MARK=$(mktemp); touch "$MARK"; sleep 1
STOP_AT_SATURATION=0 ./scripts/07_benchmark.sh "${FAIL_BENCH:-benchmarks/failure.yaml}" "${FAIL_LABEL:-failure}" &   # FAIL_LABEL must end in -failure
BP=$!
echo "== [failure test] waiting for the failure round to start"
RD=""
until [ -n "$RD" ]; do
  sleep 1
  kill -0 "$BP" 2>/dev/null || { echo "benchmark ended early"; exit 1; }
  for f in $(find caliper/results -maxdepth 3 -path '*-failure/02-*/caliper.log' -newer "$MARK" 2>/dev/null); do
    grep -q "Started round" "$f" && RD=$(dirname "$f")
  done
done
EV="$RD/events.txt"; ts() { date -u +%Y-%m-%dT%H:%M:%S.%3NZ; }
echo "$(ts) round started" > "$EV"
sleep "$STOP_AT"
for i in $FAIL; do docker stop -t 2 "peer0.inst$i.cbdc.example" >/dev/null; done
echo "$(ts) stopped peers: $FAIL" >> "$EV"; echo "== [failure test] $(tail -1 "$EV")"
sleep "$DOWN_FOR"
for i in $FAIL; do docker start "peer0.inst$i.cbdc.example" >/dev/null; done
echo "$(ts) started peers: $FAIL" >> "$EV"; echo "== [failure test] $(tail -1 "$EV")"
wait "$BP" || true
echo "== [failure test] ledger heights after the run (all 5 should be equal once peers 4 and 5 have caught up)"
sleep 10
for p in 9446 9447 9448 9449 9450; do echo -n "   port $p: "; curl -s "localhost:$p/metrics" | grep "^ledger_blockchain_height{channel=\"cbdc\"}" | awk "{print \$2}" || echo "?"; done
echo "== [failure test] events"; cat "$EV"
python3 scripts/steady.py "$RD"
