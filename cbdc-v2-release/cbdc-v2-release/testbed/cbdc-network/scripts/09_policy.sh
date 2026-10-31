#!/usr/bin/env bash
# Step 8e: change the wallet chaincode's endorsement policy to OutOf(Q of 5 peers) on the RUNNING network
# (a chaincode definition upgrade: same package, same chaincode containers, sequence + 1; ledger kept).
# Usage: ./scripts/09_policy.sh <Q>        Q = 3, 4 or 5
# How it works: every institution's admin approves the new definition (sequence N+1 with the new policy); once a
# majority has approved (the channel's LifecycleEndorsement rule), Inst1 commits it; from the next block on, peers
# validate transactions against the new policy, and the gateways read it through service discovery and ask Q peers.
set -euo pipefail
cd "$(dirname "$0")/.."
Q="${1:?usage: 09_policy.sh <Q>}"; [[ "$Q" =~ ^[1-5]$ ]] || { echo "Q must be 1..5"; exit 1; }
CC=wallet; VER=1.0
R="$PWD"; BIN="${FABRIC_BIN:-$HOME/fabric-samples/bin}"; export PATH="$BIN:$PATH"
export FABRIC_CFG_PATH="$R/config/peercfg" CORE_PEER_TLS_ENABLED=true
ORDERER_CA="$R/organizations/ordererOrganizations/cb.cbdc.example/tlsca/tlsca.cb.cbdc.example-cert.pem"
POLICY="OutOf($Q,'Inst1MSP.peer','Inst2MSP.peer','Inst3MSP.peer','Inst4MSP.peer','Inst5MSP.peer')"
PACKAGE_ID=$(cat build/package_id)
retry() { local n=0 out; until out=$("$@" 2>&1); do n=$((n+1)); [ $n -ge 6 ] && { echo "$out"; return 1; }; sleep 5; done; echo "$out"; }
as_inst() { local i=$1 P="$R/organizations/peerOrganizations/inst$1.cbdc.example"
  export CORE_PEER_LOCALMSPID="Inst${i}MSP" CORE_PEER_MSPCONFIGPATH="$P/users/Admin@inst$i.cbdc.example/msp" \
         CORE_PEER_TLS_ROOTCERT_FILE="$P/peers/peer0.inst$i.cbdc.example/tls/ca.crt" CORE_PEER_ADDRESS="localhost:$((7051 + 1000*(i-1)))"; }
as_inst 1
CUR=$(peer lifecycle chaincode querycommitted --channelID cbdc --name $CC --output json)
SEQ=$(( $(echo "$CUR" | jq -r .sequence) + 1 ))
echo "== Current definition: sequence $(echo "$CUR" | jq -r .sequence); new: sequence $SEQ with policy $POLICY"
echo "== Approvals (each institution's admin, same package $PACKAGE_ID)"
for i in 1 2 3 4 5; do
  as_inst $i; echo -n "   Inst${i}MSP: "
  retry peer lifecycle chaincode approveformyorg -o localhost:7050 --tls --cafile "$ORDERER_CA" --channelID cbdc --name $CC \
    --version $VER --package-id "$PACKAGE_ID" --sequence $SEQ --signature-policy "$POLICY" | grep -o -E "status \(VALID\)|Error.*" | head -1
done
as_inst 1
echo -n "== Commit readiness: "
retry peer lifecycle chaincode checkcommitreadiness --channelID cbdc --name $CC --version $VER --sequence $SEQ --signature-policy "$POLICY" --output json | jq -c .approvals
PEERS=(); for i in 1 2 3; do P="$R/organizations/peerOrganizations/inst$i.cbdc.example"; PEERS+=(--peerAddresses "localhost:$((7051 + 1000*(i-1)))" --tlsRootCertFiles "$P/peers/peer0.inst$i.cbdc.example/tls/ca.crt"); done
echo "== Commit"
retry peer lifecycle chaincode commit -o localhost:7050 --tls --cafile "$ORDERER_CA" --channelID cbdc --name $CC --version $VER \
  --sequence $SEQ --signature-policy "$POLICY" "${PEERS[@]}" | grep -o -E "status \(VALID\) at localhost:[0-9]+|Error.*"
sleep 5
echo -n "== Committed definition: "; peer lifecycle chaincode querycommitted --channelID cbdc --name $CC --output json | jq -c '{sequence, validation_parameter}' | cut -c1-120
echo "== Policy is now OutOf($Q of 5). Wait about 10 s before benchmarking (gateways refresh discovery)."
