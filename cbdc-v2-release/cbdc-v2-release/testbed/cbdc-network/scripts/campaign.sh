#!/usr/bin/env bash
# Reportable campaign driver (agreed 2026-10-20; final host = new laptop). One BLOCK per call:
#   ./scripts/campaign.sh A            main sweep 25,50,100,150,200,250,300 TPS + noop 150 (B=50, 2s, Q=3)
#   (B, T, Q and D blocks run at 50, 150, 200 TPS; B10 at 25, 50, 100)
#   ./scripts/campaign.sh B10H          B=10 at 150 and 200 TPS (added 2026-10-21: B10 healthy at 100)
#   ./scripts/campaign.sh B10|B100|B500  block size 10/100/500 at 2 s        ./scripts/campaign.sh T025|T1   timeout 0.25/1 s at B=50
#   ./scripts/campaign.sh Q1|Q2|Q4|Q5   endorsement policy OutOf(Q,5) at B=50, 2 s
#   ./scripts/campaign.sh D            contention: zipf s=0.8, zipf s=1.2, uniform over 100 accounts (B=50, 2s, Q=3)
#   ./scripts/campaign.sh E            2-of-5 peer failure at 150 TPS, policy Q=3 then Q=4 (5 reps each)
#   ./scripts/campaign.sh F            surge 100 -> 250 -> 100 TPS (100 s each)
# Every block starts from a FRESH network (08_rebuild.sh), sets selective logging, then runs REPS (default 5)
# repetitions; within a repetition the load order is shuffled (seeded, recorded). Rounds 300 s (ROUND_S), steady
# window skips the first 60 s (STEADY_SKIP_S). STOP_AT_SATURATION=0. 07_benchmark.sh drops the page cache each rep.
# Env: REPS=5 ROUND_S=300 NOREBUILD=1 (skip the rebuild, e.g. to resume a block).
set -euo pipefail
cd "$(dirname "$0")/.."
BLK="${1:?usage: campaign.sh <A|B10|B10H|B10C|B100|B500|T025|T1|Q1|Q2|Q4|Q5|D|E|F>}"
REPS="${REPS:-5}"; RS="${ROUND_S:-300}"; export STEADY_SKIP_S="${STEADY_SKIP_S:-60}" STOP_AT_SATURATION=0 ROUND_PAUSE="${ROUND_PAUSE:-30}" FSYNC_LIMIT_MS="${FSYNC_LIMIT_MS:-50}"
B=50; TAU=2s; Q=3; LOADS="50 150 200"; CASES="uniform"   # top load 200 (decided 2026-10-21 after block A)
case "$BLK" in
  A) LOADS="25 50 100 150 200 250 300";;
  B10) B=10; LOADS="25 50 100";; B10H) B=10; LOADS="150 200";; B10C) B=10; LOADS="150";;   # B10C: drift check, 150 TPS only B100) B=100;; B500) B=500;;
  T025) TAU=250ms;; T1) TAU=1s;;
  Q1|Q2|Q4|Q5) B=100; Q="${BLK#Q}";;
  D) B=100; CASES="zipf0.8 zipf1.2 n100";;
  E|F) B=100;;   # Q, D, E, F at B=100 (decided 2026-10-21: stable at 200 TPS; block B100 is the Q=3 reference)
  *) echo "unknown block $BLK"; exit 1;;
esac
LOG="caliper/results/campaign.log"; mkdir -p caliper/results
say() { echo "$(date -u +%FT%TZ) [$BLK] $*" | tee -a "$LOG"; }
setlog() { for p in 9443 9444 9445 9446 9447 9448 9449 9450; do
  curl -s -X PUT "localhost:$p/logspec" -d '{"spec":"warning:kvledger,committer.txvalidator,orderer.consensus.etcdraft=info"}' >/dev/null; done
  curl -s localhost:9443/logspec | grep -q "kvledger=info" || { say "selective logging NOT set"; exit 1; }; }
wl() { case "$1" in
  uniform) echo "{ module: workload/transfer.js, arguments: { accounts: 10000, distribution: uniform$2 } }";;
  zipf0.8) echo "{ module: workload/transfer.js, arguments: { accounts: 10000, distribution: zipf, zipfS: 0.8 } }";;
  zipf1.2) echo "{ module: workload/transfer.js, arguments: { accounts: 10000, distribution: zipf, zipfS: 1.2 } }";;
  n100)    echo "{ module: workload/transfer.js, arguments: { accounts: 100, distribution: uniform } }";;
  noop)    echo "{ module: workload/noop.js }";; esac; }
hdr() { printf 'test:\n  name: %s\n  description: campaign block %s\n  workers: { number: 4 }\n  rounds:\n' "$1" "$BLK"
  echo "    - { label: warmup-50tps, txDuration: 30, rateControl: { type: fixed-rate, opts: { tps: 50 } }, workload: $(wl uniform "$2") }"; }

if [ "${NOREBUILD:-0}" != 1 ]; then
  say "fresh network B=$B TAU=$TAU"; ./scripts/08_rebuild.sh "$B" "$TAU"
  [ "$Q" != 3 ] && { say "policy OutOf($Q,5)"; ./scripts/09_policy.sh "$Q"; }
fi
setlog
BD="caliper/benchmarks/campaign"; mkdir -p "$BD"

if [ "$BLK" = E ]; then
  ORGS=", orgs: [Inst1MSP, Inst2MSP, Inst3MSP]"
  for q in 3 4; do
    [ "$q" = 4 ] && { say "policy OutOf(4,5) for the second half"; ./scripts/09_policy.sh 4; setlog; }
    F="$BD/E-q$q.yaml"; { hdr "cbdc-E-q$q" "$ORGS"
      echo "    - { label: failure-150tps-150s, txDuration: 150, rateControl: { type: fixed-rate, opts: { tps: 150 } }, workload: $(wl uniform "$ORGS") }"; } > "$F"
    for r in $(seq 1 "$REPS"); do say "E q=$q rep $r"
      FAIL_BENCH="benchmarks/campaign/E-q$q.yaml" FAIL_LABEL="E-q$q-rep$r-failure" ./scripts/10_failure.sh
      sleep 20; setlog   # restarted peers come back with default logging
    done
  done
  say "block done"; exit 0
fi

for r in $(seq 1 "$REPS"); do
  F="$BD/$BLK-rep$r.yaml"; SEED="$BLK-$r"
  if [ "$BLK" = F ]; then
    { hdr "cbdc-F" ""; cat <<EOF
    - label: surge-100-250-100
      txDuration: $RS
      rateControl: { type: composite-rate, opts: { weights: [1, 1, 1], logChange: true, rateControllers: [ { type: fixed-rate, opts: { tps: 100 } }, { type: fixed-rate, opts: { tps: 250 } }, { type: fixed-rate, opts: { tps: 100 } } ] } }
      workload: $(wl uniform "")
EOF
    } > "$F"
  else
    ITEMS=""; for c in $CASES; do for l in $LOADS; do ITEMS="$ITEMS $c:$l"; done; done
    [ "$BLK" = A ] && ITEMS="$ITEMS noop:150"
    # rounds at the block's TOP load can overload the network and degrade later rounds (A, 2026-10-20), so they are
    # shuffled among themselves and run LAST; all other rounds are shuffled
    TOP=$(echo $LOADS | tr ' ' '\n' | sort -n | tail -1)
    ORDER=$(python3 -c "import random,sys; r=random.Random(sys.argv[1]); t=sys.argv[2]; it=sys.argv[3:]; a=[x for x in it if not x.endswith(':'+t)]; b=[x for x in it if x.endswith(':'+t)]; r.shuffle(a); r.shuffle(b); print(' '.join(a+b))" "$SEED" "$TOP" $ITEMS)
    { hdr "cbdc-$BLK-rep$r" ""
      for i in $ORDER; do c="${i%%:*}"; l="${i##*:}"
        echo "    - { label: $c-${l}tps, txDuration: $RS, rateControl: { type: fixed-rate, opts: { tps: $l } }, workload: $(wl "$c" "") }"; done; } > "$F"
    say "rep $r order: $(echo $ORDER)"
  fi
  ./scripts/07_benchmark.sh "benchmarks/campaign/$BLK-rep$r.yaml" "$BLK-rep$r" 2>&1 | tee "caliper/results/console-$BLK-rep$r.txt"
  grep -A12 "== Summary" "caliper/results/console-$BLK-rep$r.txt" >> "$LOG" || true
done
say "block done"
