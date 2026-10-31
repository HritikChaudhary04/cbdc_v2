#!/usr/bin/env bash
# Step 1: generate identities and the channel genesis block.
# Usage: ./scripts/01_generate.sh [MAX_MESSAGE_COUNT] [BATCH_TIMEOUT]      (defaults: 9 and 2s)
# Run from ~/cbdc-network. Uses the Fabric 2.5.14 binaries in ~/fabric-samples/bin.
set -euo pipefail
B="${1:-9}"; TAU="${2:-2s}"
BIN="${FABRIC_BIN:-$HOME/fabric-samples/bin}"
cd "$(dirname "$0")/.."
echo "== Fabric tools: $("$BIN/configtxgen" -version | grep -m1 Version)"
echo "== Removing any previous identities and artifacts"
rm -rf organizations channel-artifacts config/configtx.yaml
mkdir -p channel-artifacts
echo "== 1a. Generating identities with cryptogen"
"$BIN/cryptogen" generate --config=config/crypto-config.yaml --output=organizations
echo "== 1b. Writing config/configtx.yaml with MaxMessageCount=$B, BatchTimeout=$TAU"
sed -e "s/__MAX_MESSAGE_COUNT__/$B/" -e "s/__BATCH_TIMEOUT__/$TAU/" config/configtx.yaml.tpl > config/configtx.yaml
echo "== 1c. Creating the genesis block of channel 'cbdc'"
FABRIC_CFG_PATH="$PWD/config" "$BIN/configtxgen" -profile CBDCChannel -outputBlock channel-artifacts/cbdc.block -channelID cbdc
echo "== 1d. Checking the block"
"$BIN/configtxlator" proto_decode --input channel-artifacts/cbdc.block --type common.Block --output channel-artifacts/cbdc.json
C='.data.data[0].payload.data.config.channel_group'
jq -r "\"institution orgs: \" + ([$C.groups.Application.groups | keys[]] | join(\", \"))" channel-artifacts/cbdc.json
jq -r "\"ordering org: \" + ([$C.groups.Orderer.groups | keys[]] | join(\", \"))" channel-artifacts/cbdc.json
jq -r "$C.groups.Orderer.values.BatchSize.value | \"block size: MaxMessageCount=\(.max_message_count), PreferredMaxBytes=\(.preferred_max_bytes)\"" channel-artifacts/cbdc.json
jq -r "$C.groups.Orderer.values.BatchTimeout.value | \"block timeout: \(.timeout)\"" channel-artifacts/cbdc.json
jq -r "\"raft consenters: \" + ([$C.groups.Orderer.values.ConsensusType.value.metadata.consenters[] | \"\(.host):\(.port)\"] | join(\", \"))" channel-artifacts/cbdc.json
jq -r "\"anchor peers: \" + ([$C.groups.Application.groups[].values.AnchorPeers.value.anchor_peers[]? | \"\(.host):\(.port)\"] | join(\", \"))" channel-artifacts/cbdc.json
echo "== Step 1 complete"
