#!/usr/bin/env bash
# Step 6a: create N benchmark accounts (default 10000) with a large balance (default 1e9), in chunks of 1000 per
# transaction (InitAccounts), as Inst1's administrator, endorsed by Inst1-3 peers. The large balance means Transfer
# never fails for lack of funds, so every failure in a benchmark is a genuine conflict or error.
set -euo pipefail
cd "$(dirname "$0")/.."
N="${1:-10000}"; BAL="${2:-1000000000}"; CHUNK=1000
R="$PWD"; BIN="${FABRIC_BIN:-$HOME/fabric-samples/bin}"; export PATH="$BIN:$PATH"
export FABRIC_CFG_PATH="$R/config/peercfg" CORE_PEER_TLS_ENABLED=true
ORDERER_CA="$R/organizations/ordererOrganizations/cb.cbdc.example/tlsca/tlsca.cb.cbdc.example-cert.pem"
P1="$R/organizations/peerOrganizations/inst1.cbdc.example"
export CORE_PEER_LOCALMSPID=Inst1MSP CORE_PEER_MSPCONFIGPATH="$P1/users/Admin@inst1.cbdc.example/msp" \
       CORE_PEER_TLS_ROOTCERT_FILE="$P1/peers/peer0.inst1.cbdc.example/tls/ca.crt" CORE_PEER_ADDRESS=localhost:7051
PEERS=()
for i in 1 2 3; do P="$R/organizations/peerOrganizations/inst$i.cbdc.example"; PEERS+=(--peerAddresses "localhost:$((7051 + 1000*(i-1)))" --tlsRootCertFiles "$P/peers/peer0.inst$i.cbdc.example/tls/ca.crt"); done
echo "== Creating accounts 0..$((N-1)) with balance $BAL, $CHUNK per transaction"
for ((s=0; s<N; s+=CHUNK)); do
  c=$(( N-s < CHUNK ? N-s : CHUNK ))
  out=$(peer chaincode invoke -o localhost:7050 --tls --cafile "$ORDERER_CA" -C cbdc -n wallet "${PEERS[@]}" --waitForEvent \
        -c "{\"function\":\"InitAccounts\",\"Args\":[\"$s\",\"$c\",\"$BAL\"]}" 2>&1 | grep -o -E "committed with status \([A-Z_]+\)|Error.*" | head -1)
  echo "   accounts $s..$((s+c-1)): $out"
done
echo -n "== Check: balance of account $((N-1)) = "
peer chaincode query -C cbdc -n wallet -c "{\"function\":\"Balance\",\"Args\":[\"$((N-1))\"]}" 2>&1 | tail -1
