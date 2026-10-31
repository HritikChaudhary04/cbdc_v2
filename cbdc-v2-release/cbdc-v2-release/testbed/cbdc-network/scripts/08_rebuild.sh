#!/usr/bin/env bash
# Step 8d: rebuild the whole network from scratch with new block parameters (fresh ledger, new identities).
# Usage: ./scripts/08_rebuild.sh <MAX_MESSAGE_COUNT> <BATCH_TIMEOUT>     e.g. ./scripts/08_rebuild.sh 50 2s
# Runs: down.sh -> 01_generate.sh B TAU -> 02_up.sh -> 03_channel.sh -> 04_chaincode.sh -> 06_init_accounts.sh.
# A fresh network per configuration is what the spec (E1) calls "fresh network", and keeps ledgers comparable.
set -euo pipefail
cd "$(dirname "$0")/.."
B="${1:?usage: 08_rebuild.sh <MAX_MESSAGE_COUNT> <BATCH_TIMEOUT>}"; TAU="${2:?usage: 08_rebuild.sh <MAX_MESSAGE_COUNT> <BATCH_TIMEOUT>}"
echo "== Rebuilding the network with MaxMessageCount=$B, BatchTimeout=$TAU (about 5 minutes)"
./scripts/down.sh
./scripts/01_generate.sh "$B" "$TAU"
./scripts/02_up.sh
./scripts/03_channel.sh
./scripts/04_chaincode.sh
./scripts/06_init_accounts.sh
echo "== Waiting 20 s for gossip to settle, then checking membership"
sleep 20
docker logs peer0.inst1.cbdc.example 2>&1 | grep "Membership view has changed" | tail -1 | grep -oE "current view:.*" || echo "   (no membership line yet)"
echo "== Rebuild complete: MaxMessageCount=$B, BatchTimeout=$TAU"
