#!/usr/bin/env bash
# Step 4: build the wallet chaincode ONCE, run one chaincode container per institution (chaincode as a service),
# install the package on all 5 peers, approve it in all 5 institutions with the endorsement policy
# OutOf(Q of 5 peers) (default Q=3), commit it to channel 'cbdc', and check the committed definition.
# Run from ~/cbdc-network after step 3.   Usage: ./scripts/04_chaincode.sh [Q]     (Q = endorsement threshold)
set -euo pipefail
cd "$(dirname "$0")/.."
Q="${1:-3}"; CC=wallet; VER=1.0; SEQ="${CC_SEQUENCE:-1}"
R="$PWD"; BIN="${FABRIC_BIN:-$HOME/fabric-samples/bin}"; export PATH="$BIN:$PATH"
export FABRIC_CFG_PATH="$R/config/peercfg" CORE_PEER_TLS_ENABLED=true
ORDERER_CA="$R/organizations/ordererOrganizations/cb.cbdc.example/tlsca/tlsca.cb.cbdc.example-cert.pem"
POLICY="OutOf($Q,'Inst1MSP.peer','Inst2MSP.peer','Inst3MSP.peer','Inst4MSP.peer','Inst5MSP.peer')"
retry() {  # run a command up to 6 times, 5 s apart (Raft leader election or block delivery may still be in progress)
  local n=0 out
  until out=$("$@" 2>&1); do n=$((n+1)); [ $n -ge 6 ] && { echo "$out"; return 1; }; sleep 5; done
  echo "$out"
}
as_inst() {  # set the environment to act as institution $1's administrator against its own peer
  local i=$1 P="$R/organizations/peerOrganizations/inst$1.cbdc.example"
  export CORE_PEER_LOCALMSPID="Inst${i}MSP" CORE_PEER_MSPCONFIGPATH="$P/users/Admin@inst$i.cbdc.example/msp" \
         CORE_PEER_TLS_ROOTCERT_FILE="$P/peers/peer0.inst$i.cbdc.example/tls/ca.crt" CORE_PEER_ADDRESS="localhost:$((7051 + 1000*(i-1)))"
}
if [ "${SKIP_DOCKER:-0}" != 1 ]; then
  echo "== 4a. Recreating peers whose settings changed (adds CHAINCODE_AS_A_SERVICE_BUILDER_CONFIG; ledgers are kept)"
  python3 scripts/gen_compose.py
  docker compose -f compose/docker-compose.yaml up -d
  sleep 15
  for p in 9446 9447 9448 9449 9450; do curl -s "http://localhost:$p/healthz" | grep -q '"status":"OK"' && echo "   peer ops $p healthy" || { echo "   peer ops $p NOT healthy"; exit 1; }; done
  echo "== 4b. Building the chaincode image once (first time: downloads Go and Alpine images, then compiles)"
  docker build -t cbdc-wallet:$VER chaincode/wallet
fi
echo "== 4c. Creating the chaincode package (type ccaas: it contains only the address of the chaincode service)"
rm -rf build && mkdir -p build/src build/pkg
cat > build/src/connection.json <<CONN
{
  "address": "{{.peername}}_${CC}_ccaas:9999",
  "dial_timeout": "10s",
  "tls_required": false
}
CONN
cat > build/pkg/metadata.json <<META
{ "type": "ccaas", "label": "${CC}_${VER}" }
META
tar -C build/src -czf build/pkg/code.tar.gz .
tar -C build/pkg -czf build/$CC.tar.gz metadata.json code.tar.gz
PACKAGE_ID=$(peer lifecycle chaincode calculatepackageid build/$CC.tar.gz)
echo "   package id: $PACKAGE_ID"
echo "== 4d. Installing the package on all 5 peers (no compilation: the peer only stores the connection details)"
for i in 1 2 3 4 5; do as_inst $i; echo -n "   peer0.inst$i: "; peer lifecycle chaincode install build/$CC.tar.gz 2>&1 | grep -o -E "status:[0-9]+|Error.*" | head -1; done
if [ "${SKIP_DOCKER:-0}" != 1 ]; then
  echo "== 4e. Starting one chaincode container per institution (cores ${SUT_CPUS:-0-5}, on network cbdc_net)"
  for i in 1 2 3 4 5; do
    docker rm -f "peer0inst${i}_${CC}_ccaas" >/dev/null 2>&1 || true
    docker run -d --name "peer0inst${i}_${CC}_ccaas" --network cbdc_net --cpuset-cpus "${SUT_CPUS:-0-5}" \
      -e CHAINCODE_SERVER_ADDRESS=0.0.0.0:9999 -e CHAINCODE_ID="$PACKAGE_ID" -e CORE_CHAINCODE_ID_NAME="$PACKAGE_ID" \
      cbdc-wallet:$VER >/dev/null && echo "   peer0inst${i}_${CC}_ccaas started"
  done
fi
echo "== 4f. Each institution approves the definition with endorsement policy $POLICY"
for i in 1 2 3 4 5; do
  as_inst $i; echo -n "   Inst${i}MSP: "
  retry peer lifecycle chaincode approveformyorg -o localhost:7050 --tls --cafile "$ORDERER_CA" --channelID cbdc --name $CC \
    --version $VER --package-id "$PACKAGE_ID" --sequence $SEQ --signature-policy "$POLICY" | grep -o -E "status \(VALID\)|Error.*" | head -1
done
as_inst 1
echo "== 4g. Commit readiness (all 5 should be true)"
retry peer lifecycle chaincode checkcommitreadiness --channelID cbdc --name $CC --version $VER --sequence $SEQ --signature-policy "$POLICY" --output json | jq -c .approvals
echo "== 4h. Committing the definition (endorsed by peers of Inst1, Inst2, Inst3: a majority, as LifecycleEndorsement requires)"
PEERS=()
for i in 1 2 3; do P="$R/organizations/peerOrganizations/inst$i.cbdc.example"; PEERS+=(--peerAddresses "localhost:$((7051 + 1000*(i-1)))" --tlsRootCertFiles "$P/peers/peer0.inst$i.cbdc.example/tls/ca.crt"); done
retry peer lifecycle chaincode commit -o localhost:7050 --tls --cafile "$ORDERER_CA" --channelID cbdc --name $CC --version $VER \
  --sequence $SEQ --signature-policy "$POLICY" "${PEERS[@]}" | grep -o -E "status \(VALID\) at localhost:[0-9]+|Error.*"
echo "== 4i. Committed definition"
sleep 3
retry peer lifecycle chaincode querycommitted --channelID cbdc --name $CC | tail -1
echo "$PACKAGE_ID" > build/package_id
echo "== Step 4 complete"
