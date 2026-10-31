# CBDC prototype network (v2)

Hyperledger Fabric 2.5.14 network for the CBDC confirmation-time paper: 5 institution organisations
(one peer each, endorse + commit) and a central-bank ordering organisation with 3 Raft orderers.

Work only inside the Linux home folder (~/cbdc-network), never under /mnt/c.

## Step 1: identities and channel configuration
    ./scripts/01_generate.sh            # B = 9, tau = 2s (the operating point of the paper)
    ./scripts/01_generate.sh 50 1s      # example: another block size and timeout for the B sweep
Creates organizations/ (all certificates, via cryptogen) and channel-artifacts/cbdc.block (the genesis block
of channel 'cbdc', via configtxgen) and prints a check of what the block contains.

## Step 2: start the nodes
    ./scripts/02_up.sh      # generates compose/docker-compose.yaml from scripts/nodes.py, starts 8 containers, checks health
## Step 3: create the channel
    ./scripts/03_channel.sh # orderers join (osnadmin), Raft elects a leader, peers join, ledger and gossip checked
## Step 4: deploy the wallet chaincode (chaincode as a service)
    ./scripts/04_chaincode.sh [Q]   # Q = endorsement threshold (default 3 of 5). Builds the image once, runs one
                                    # chaincode container per institution, installs, approves, commits.
## Step 5: functional test of the wallet
    ./scripts/05_test_wallet.sh     # creates accounts, transfers, rejects an overdraft, Noop
## Step 6: benchmark set-up and smoke benchmark (Caliper 0.7.1, Fabric gateway connector)
    ./scripts/06_init_accounts.sh [N] [BAL]          # N accounts (default 10000) with balance BAL (default 1e9)
    ./scripts/07_benchmark.sh benchmarks/smoke.yaml   # first run installs Caliper; runs on cores 6-7;
                                                      # flags any round whose send rate is >2% below target
## Step 7: measurement collection (runs inside 07_benchmark.sh, one Caliper launch per round)
For every round, caliper/results/<timestamp>-<label>/<NN-round>/ holds:
- report.html, caliper.log, round.yaml               Caliper's own output and the exact round run
- metrics_before/, metrics_after/                    /metrics of all 8 nodes just before and after the round (A)
- logs/*.log.gz                                      container logs for exactly the round window
- blocks_orderer.csv                                 per block: leader, cut time, Raft-written times (times = UTC epoch seconds)
- blocks_peer.csv                                    per block and peer: size, validated/committed times, sub-times (C)
- gateway_calls.csv                                  per gateway call: peer, method, code, end time, duration (C)
- docker_stats.csv                                   CPU % (per core) and memory of every container, about every 2 s (D)
- summary.json                                       per-round means, distributions (mean, sd, SCV, p50/p95/p99), conflicts,
                                                     endorsement share per peer, steady-window throughput, leader
The results folder also holds env.txt (versions, host, leader) and summary.txt (all rounds, send-rate check).
## Stop
    ./scripts/down.sh       # removes containers and ledger volumes (also remove chaincode containers:
                            #   docker rm -f $(docker ps -aq --filter name=_wallet_ccaas))

Files:
- config/crypto-config.yaml : which organisations and nodes exist (input to cryptogen)
- config/configtx.yaml.tpl  : channel rules: members, policies, Raft, block cutting (input to configtxgen)
- scripts/01_generate.sh    : fills in B and tau, runs cryptogen and configtxgen, checks the block
- scripts/nodes.py         : ONE specification of all 8 nodes (ports, settings); compose file is generated from it
- scripts/gen_compose.py   : writes compose/docker-compose.yaml (images pinned to 2.5.14; Fabric containers on cores 0-5)
- config/peercfg/core.yaml : Fabric 2.5.14's stock peer config with ONE change: vm.endpoint "" (no Docker builder)
- chaincode/wallet/          : Go wallet chaincode (wallet.go: functions; main.go: service start-up; Dockerfile)
- scripts/dev/native_check.py : development check used to validate configs without Docker (not needed on the laptop)
- caliper/networks/cbdc-network.yaml : Caliper network config: 5 institutions, User1 identity each, own peer as gateway
- caliper/workload/transfer.js       : Transfer workload (clients rotate over 5 institutions; uniform or Zipf accounts)
- caliper/workload/noop.js           : Noop workload (fixed cost of a transaction)
- caliper/benchmarks/smoke.yaml      : short fixed-rate rounds to check the pipeline and the send-rate check
- scripts/collect.py                 : snapshots, log parsing, per-round summary and report (step 7)
- scripts/stats_sampler.sh           : docker stats sampler (step 7)
