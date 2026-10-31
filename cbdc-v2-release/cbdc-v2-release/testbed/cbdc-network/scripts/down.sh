#!/usr/bin/env bash
# Stop the CBDC network and delete its containers and data volumes (ledgers). Identities and the genesis block
# in organizations/ and channel-artifacts/ are kept; run step 1 again to regenerate them.
set -euo pipefail
cd "$(dirname "$0")/.."
docker rm -f $(docker ps -aq --filter name=_wallet_ccaas) >/dev/null 2>&1 || true
docker compose -f compose/docker-compose.yaml down -v
echo "== network stopped; peer, orderer and chaincode containers and ledger volumes removed"
