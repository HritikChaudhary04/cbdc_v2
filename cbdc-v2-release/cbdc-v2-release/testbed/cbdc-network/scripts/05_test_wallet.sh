#!/usr/bin/env bash
# Step 5: functional test of the wallet chaincode on the running network (run after step 4).
# Every transaction is endorsed by 3 institutions' peers (Inst1, Inst2, Inst3), as the OutOf(3,...) policy requires.
set -uo pipefail
cd "$(dirname "$0")/.."
R="$PWD"; BIN="${FABRIC_BIN:-$HOME/fabric-samples/bin}"; export PATH="$BIN:$PATH"
export FABRIC_CFG_PATH="$R/config/peercfg" CORE_PEER_TLS_ENABLED=true
ORDERER_CA="$R/organizations/ordererOrganizations/cb.cbdc.example/tlsca/tlsca.cb.cbdc.example-cert.pem"
P1="$R/organizations/peerOrganizations/inst1.cbdc.example"
export CORE_PEER_LOCALMSPID=Inst1MSP CORE_PEER_MSPCONFIGPATH="$P1/users/Admin@inst1.cbdc.example/msp" \
       CORE_PEER_TLS_ROOTCERT_FILE="$P1/peers/peer0.inst1.cbdc.example/tls/ca.crt" CORE_PEER_ADDRESS=localhost:7051
PEERS=()
for i in 1 2 3; do P="$R/organizations/peerOrganizations/inst$i.cbdc.example"; PEERS+=(--peerAddresses "localhost:$((7051 + 1000*(i-1)))" --tlsRootCertFiles "$P/peers/peer0.inst$i.cbdc.example/tls/ca.crt"); done
invoke() { peer chaincode invoke -o localhost:7050 --tls --cafile "$ORDERER_CA" -C cbdc -n wallet "${PEERS[@]}" --waitForEvent -c "$1" 2>&1 | grep -o -E "status:[0-9]+|committed with status \([A-Z_]+\)|Error.*|message:\"[^\"]*\"" | head -2 | tr '\n' ' '; echo; }
query()  { peer chaincode query -C cbdc -n wallet -c "$1" 2>&1 | tail -1; }
echo "== 5a. Admin of Inst1 creates accounts 0..99 with balance 1000 (expect status:200 and VALID)"
echo -n "   "; invoke '{"function":"InitAccounts","Args":["0","100","1000"]}'
echo -n "== 5b. Balance of account 5 (expect 1000): "; query '{"function":"Balance","Args":["5"]}'
echo "== 5c. Transfer 250 from account 1 to account 2 (expect VALID)"
echo -n "   "; invoke '{"function":"Transfer","Args":["1","2","250"]}'
echo -n "   balance 1 (expect 750): "; query '{"function":"Balance","Args":["1"]}'
echo -n "   balance 2 (expect 1250): "; query '{"function":"Balance","Args":["2"]}'
echo "== 5d. Overdraft: transfer 5000 from account 3 (expect an error: insufficient funds; no transaction is ordered)"
echo -n "   "; invoke '{"function":"Transfer","Args":["3","4","5000"]}'
echo -n "   balance 3 unchanged (expect 1000): "; query '{"function":"Balance","Args":["3"]}'
echo "== 5e. Noop (expect VALID; used later to measure the fixed cost of endorsement)"
echo -n "   "; invoke '{"function":"Noop","Args":[]}'
echo "== 5f. Chaincode containers"
docker ps --filter name=_wallet_ccaas --format '   {{.Names}}  {{.Status}}'
echo "== Step 5 complete"
