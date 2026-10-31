#!/usr/bin/env bash
# Step 3: join the 3 orderers and 5 peers to channel 'cbdc' and check Raft and gossip.
# Run from ~/cbdc-network after step 2.
set -euo pipefail
cd "$(dirname "$0")/.."
R="$PWD"; BIN="${FABRIC_BIN:-$HOME/fabric-samples/bin}"; export PATH="$BIN:$PATH"
O="$R/organizations/ordererOrganizations/cb.cbdc.example"
echo "== 3a. Orderers join the channel (channel participation API, via osnadmin and the central bank admin's TLS identity)"
for k in 1 2 3; do
  a=$((7053 + 1000*(k-1)))
  echo -n "   orderer$k: "
  osnadmin channel join --channelID cbdc --config-block "$R/channel-artifacts/cbdc.block" -o "localhost:$a" \
    --ca-file "$O/tlsca/tlsca.cb.cbdc.example-cert.pem" \
    --client-cert "$O/users/Admin@cb.cbdc.example/tls/client.crt" --client-key "$O/users/Admin@cb.cbdc.example/tls/client.key" \
    2>&1 | grep -E "Status|Error" | head -1
done
echo "== 3b. Waiting for Raft to elect a leader (up to 60 s)"
leader=""
for t in $(seq 1 30); do
  for k in 1 2 3; do l=$(docker logs "orderer$k.cb.cbdc.example" 2>&1 | grep -m1 -E "became leader at term" || true); [ -n "$l" ] && leader="$l"; done
  [ -n "$leader" ] && break; sleep 2
done
[ -n "$leader" ] && echo "$leader" | sed 's/.*-> /   /' || { echo "   no Raft leader after 60 s; check: docker logs orderer1.cb.cbdc.example"; exit 1; }
echo "== 3c. Each institution's admin joins its peer to the channel"
export FABRIC_CFG_PATH="$R/config/peercfg" CORE_PEER_TLS_ENABLED=true
for i in 1 2 3 4 5; do
  P="$R/organizations/peerOrganizations/inst$i.cbdc.example"
  echo -n "   peer0.inst$i: "
  CORE_PEER_LOCALMSPID="Inst${i}MSP" CORE_PEER_MSPCONFIGPATH="$P/users/Admin@inst$i.cbdc.example/msp" \
  CORE_PEER_TLS_ROOTCERT_FILE="$P/peers/peer0.inst$i.cbdc.example/tls/ca.crt" CORE_PEER_ADDRESS="localhost:$((7051 + 1000*(i-1)))" \
    peer channel join -b "$R/channel-artifacts/cbdc.block" 2>&1 | grep -E "Successfully|Error" | sed 's/.*-> //'
done
echo "== 3d. Waiting 15 s, then checking a ledger and gossip membership"
sleep 15
# gossip can take >15 s (new laptop 2026-10-20): wait up to 90 s more until inst1 sees all 4 other peers
for _ in $(seq 1 18); do n=$(docker logs peer0.inst1.cbdc.example 2>&1 | grep "Membership view has changed" | tail -1 | grep -o "cbdc.example" | wc -l); [ "$n" -ge 4 ] && break; sleep 5; done
P="$R/organizations/peerOrganizations/inst3.cbdc.example"
echo -n "   inst3 ledger: "
CORE_PEER_LOCALMSPID=Inst3MSP CORE_PEER_MSPCONFIGPATH="$P/users/Admin@inst3.cbdc.example/msp" \
CORE_PEER_TLS_ROOTCERT_FILE="$P/peers/peer0.inst3.cbdc.example/tls/ca.crt" CORE_PEER_ADDRESS=localhost:9051 \
  peer channel getinfo -c cbdc 2>&1 | tail -1
echo -n "   inst1 sees: "
docker logs peer0.inst1.cbdc.example 2>&1 | grep "Membership view has changed" | tail -1 | grep -o "current view.*" || echo "(no gossip view yet; rerun the last check in a few seconds)"
echo "== Step 3 complete"
