#!/usr/bin/env bash
# Step 6b + 7b: run a Caliper benchmark, ONE ROUND PER CALIPER LAUNCH, and for every round collect:
#   A  /metrics snapshots of all 8 nodes just before and just after the round (per-round means and counts = after - before)
#   C  the containers' logs for exactly that window, parsed into blocks_peer.csv, blocks_orderer.csv, gateway_calls.csv
#   D  docker stats (CPU, memory per container) every ~2 s during the round
# then summary.json per round and one table with the send-rate check (a round >2% below target is INVALID).
# Usage: ./scripts/07_benchmark.sh benchmarks/<file>.yaml [label]      (benchmark path relative to caliper/)
#  - Caliper and the samplers run on CPU cores 6-7 (taskset); Fabric containers on cores 0-5 (cpuset).
set -euo pipefail
cd "$(dirname "$0")/.."; R="$PWD"
BENCH="${1:?usage: 07_benchmark.sh benchmarks/<file>.yaml [label]}"; LABEL="${2:-$(basename "$BENCH" .yaml)}"
export CLIENT_CPUS="${CLIENT_CPUS:-6,7}"
NCPU=$(nproc --all)
for c in ${CLIENT_CPUS//,/ }; do [ "$c" -lt "$NCPU" ] || { echo "CPU core $c does not exist (this machine has $NCPU); set CLIENT_CPUS"; exit 1; }; done
[ -f "caliper/$BENCH" ] || { echo "benchmark file caliper/$BENCH not found"; exit 1; }
if [ ! -d caliper/node_modules/@hyperledger/caliper-cli ]; then
  echo "== Installing Caliper 0.7.1 and binding the Fabric gateway connector (first time only)"
  (cd caliper && npm install --no-audit --no-fund --loglevel=error && npx caliper bind --caliper-bind-sut fabric:fabric-gateway)
fi
OUT="$R/caliper/results/$(date +%Y%m%d-%H%M%S)-$LABEL"; mkdir -p "$OUT"
cp "caliper/$BENCH" "$OUT/benchmark.yaml"
# Page-cache guard (2026-10-20): a large WSL page cache pushed Windows to 95% memory, Windows paged, and Raft fsync
# went from ~2.5 ms to 10-200 ms (invalid runs). Drop the cache before every run; needs sudo (asks once, or set NOPASSWD).
sync; if echo 3 | sudo -n tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || { sudo -v && echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null; }; then echo "== Page cache dropped"; else echo "== WARNING: page cache NOT dropped"; fi
echo "== Environment"; python3 scripts/collect.py env "$OUT"
mapfile -t ROUNDS < <(python3 scripts/collect.py split "caliper/$BENCH" "$OUT/rounds")
for RY in "${ROUNDS[@]}"; do
  NAME=$(basename "$RY" .yaml); RD="$OUT/$NAME"; mkdir -p "$RD"; cp "$RY" "$RD/round.yaml"
  echo "== Round $NAME"
  # per-ROUND cache drop and memory record (2026-10-20: within a 50-min campaign rep the cache regrew and an
  # overloaded round degraded every later round of the same rep)
  sync; echo 3 | sudo -n tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || echo "   WARNING: page cache not dropped before this round"
  free -m > "$RD/mem_before.txt"
  python3 scripts/collect.py snapshot "$RD/metrics_before"; T0=$(cat "$RD/metrics_before/time_utc.txt")
  taskset -c "$CLIENT_CPUS" scripts/stats_sampler.sh "$RD/docker_stats.csv" & SP=$!
  (cd caliper && taskset -c "$CLIENT_CPUS" npx caliper launch manager \
     --caliper-workspace . --caliper-networkconfig networks/cbdc-network.yaml --caliper-benchconfig "$RD/round.yaml" \
     --caliper-flow-only-test --caliper-report-path "$RD/report.html") > "$RD/caliper.log" 2>&1 || echo "   Caliper exited with an error (see $RD/caliper.log)"
  kill "$SP" 2>/dev/null || true; wait "$SP" 2>/dev/null || true
  sleep 3   # let the last block's commit lines and counters settle
  python3 scripts/collect.py snapshot "$RD/metrics_after"; T1=$(cat "$RD/metrics_after/time_utc.txt")
  grep -E "Failed to perform" "$RD/caliper.log" | cut -c1-200 | head -5 || true
  python3 scripts/collect.py extract "$RD" "$T0" "$T1"
  python3 scripts/collect.py summarize "$RD"
  if [ "${STOP_AT_SATURATION:-1}" = 1 ] && python3 scripts/collect.py saturated "$RD"; then
    echo "== Saturation reached in $NAME: remaining rounds skipped (set STOP_AT_SATURATION=0 to run them all)"; break
  fi
  sleep "${ROUND_PAUSE:-5}"   # pause between rounds; campaign uses 30 s so queues and disk settle
done
python3 scripts/collect.py report "$OUT" | tee "$OUT/summary.txt"
echo "== Results in ${OUT#$R/}"
