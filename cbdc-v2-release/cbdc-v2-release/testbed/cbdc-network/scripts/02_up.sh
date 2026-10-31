#!/usr/bin/env bash
# Step 2: start the 3 orderers and 5 peers and check that every node is healthy.
# Run from ~/cbdc-network after step 1.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f channel-artifacts/cbdc.block ] && [ -d organizations ] || { echo "Step 1 has not been run: ./scripts/01_generate.sh"; exit 1; }
echo "== 2a. Generating compose/docker-compose.yaml from scripts/nodes.py (Fabric containers on cores ${SUT_CPUS:-0-5})"
python3 scripts/gen_compose.py
echo "== 2b. Starting containers"
docker compose -f compose/docker-compose.yaml up -d
echo "== 2c. Waiting 15 s for start-up, then checking each node's health endpoint"
sleep 15
ok=0
for p in 9443 9444 9445 9446 9447 9448 9449 9450; do
  h=$(curl -s "http://localhost:$p/healthz" || echo "no response")
  case "$h" in *'"status":"OK"'*) s="healthy"; ok=$((ok+1));; *) s="NOT HEALTHY: $h";; esac
  echo "   operations port $p: $s"
done
docker ps --filter network=cbdc_net --format '   {{.Names}}  {{.Status}}'
echo "== $ok of 8 nodes healthy"
[ "$ok" -eq 8 ] && echo "== Step 2 complete" || { echo "Some nodes are not healthy; see: docker logs <container name>"; exit 1; }
