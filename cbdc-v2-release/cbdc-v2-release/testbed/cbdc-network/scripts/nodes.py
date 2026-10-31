"""
nodes.py : ONE specification of the 8 nodes of the CBDC prototype (3 orderers, 5 peers).
Both the Docker Compose file (compose/docker-compose.yaml) and the native start-up test are generated from
this file, so they cannot drift apart. Ports:
  orderer k (k=1..3): listen 7050/8050/9050, admin 7053/8053/9053, operations (metrics/health) 9443/9444/9445
  peer of Inst i (i=1..5): listen 7051/8051/9051/10051/11051, chaincode 7052/.../11052, operations 9446..9450
"""
IMG_TAG = "2.5.14"
ORG_DOMAIN = "cbdc.example"

def orderers():
    out = []
    for k in range(1, 4):
        host = f"orderer{k}.cb.{ORG_DOMAIN}"
        port, admin, ops = 7050 + 1000 * (k - 1), 7053 + 1000 * (k - 1), 9442 + k
        base = f"organizations/ordererOrganizations/cb.{ORG_DOMAIN}/orderers/{host}"
        env = {
            "FABRIC_LOGGING_SPEC": "INFO",
            "ORDERER_GENERAL_LISTENADDRESS": "0.0.0.0",
            "ORDERER_GENERAL_LISTENPORT": str(port),
            "ORDERER_GENERAL_LOCALMSPID": "CentralBankMSP",
            "ORDERER_GENERAL_LOCALMSPDIR": "{MSP}",
            "ORDERER_GENERAL_TLS_ENABLED": "true",
            "ORDERER_GENERAL_TLS_PRIVATEKEY": "{TLS}/server.key",
            "ORDERER_GENERAL_TLS_CERTIFICATE": "{TLS}/server.crt",
            "ORDERER_GENERAL_TLS_ROOTCAS": "[{TLS}/ca.crt]",
            "ORDERER_GENERAL_CLUSTER_CLIENTCERTIFICATE": "{TLS}/server.crt",
            "ORDERER_GENERAL_CLUSTER_CLIENTPRIVATEKEY": "{TLS}/server.key",
            "ORDERER_GENERAL_CLUSTER_ROOTCAS": "[{TLS}/ca.crt]",
            "ORDERER_GENERAL_BOOTSTRAPMETHOD": "none",
            "ORDERER_CHANNELPARTICIPATION_ENABLED": "true",
            "ORDERER_ADMIN_TLS_ENABLED": "true",
            "ORDERER_ADMIN_TLS_CERTIFICATE": "{TLS}/server.crt",
            "ORDERER_ADMIN_TLS_PRIVATEKEY": "{TLS}/server.key",
            "ORDERER_ADMIN_TLS_ROOTCAS": "[{TLS}/ca.crt]",
            "ORDERER_ADMIN_TLS_CLIENTROOTCAS": "[{TLS}/ca.crt]",
            "ORDERER_ADMIN_LISTENADDRESS": f"0.0.0.0:{admin}",
            "ORDERER_OPERATIONS_LISTENADDRESS": f"0.0.0.0:{ops}",
            "ORDERER_METRICS_PROVIDER": "prometheus",
            "ORDERER_FILELEDGER_LOCATION": "{DATA}",
            "ORDERER_CONSENSUS_WALDIR": "{DATA}/etcdraft/wal",
            "ORDERER_CONSENSUS_SNAPDIR": "{DATA}/etcdraft/snapshot",
        }
        out.append(dict(kind="orderer", host=host, ports=[port, admin, ops], msp=f"{base}/msp", tls=f"{base}/tls",
                        env=env, data="/var/hyperledger/production/orderer", ops=ops))
    return out

def peers():
    out = []
    for i in range(1, 6):
        host = f"peer0.inst{i}.{ORG_DOMAIN}"
        port, cc, ops = 7051 + 1000 * (i - 1), 7052 + 1000 * (i - 1), 9445 + i
        base = f"organizations/peerOrganizations/inst{i}.{ORG_DOMAIN}/peers/{host}"
        env = {
            "FABRIC_LOGGING_SPEC": "INFO",
            "FABRIC_CFG_PATH": "{CFG}",
            "CORE_PEER_ID": host,
            "CORE_PEER_ADDRESS": f"{host}:{port}",
            "CORE_PEER_LISTENADDRESS": f"0.0.0.0:{port}",
            "CORE_PEER_CHAINCODEADDRESS": f"{host}:{cc}",
            "CORE_PEER_CHAINCODELISTENADDRESS": f"0.0.0.0:{cc}",
            "CORE_PEER_GOSSIP_BOOTSTRAP": f"{host}:{port}",
            "CORE_PEER_GOSSIP_EXTERNALENDPOINT": f"{host}:{port}",
            "CORE_PEER_LOCALMSPID": f"Inst{i}MSP",
            "CORE_PEER_MSPCONFIGPATH": "{MSP}",
            "CORE_PEER_TLS_ENABLED": "true",
            "CORE_PEER_TLS_CERT_FILE": "{TLS}/server.crt",
            "CORE_PEER_TLS_KEY_FILE": "{TLS}/server.key",
            "CORE_PEER_TLS_ROOTCERT_FILE": "{TLS}/ca.crt",
            "CORE_PEER_FILESYSTEMPATH": "{DATA}",
            "CORE_LEDGER_STATE_STATEDATABASE": "goleveldb",
            "CORE_OPERATIONS_LISTENADDRESS": f"0.0.0.0:{ops}",
            "CORE_METRICS_PROVIDER": "prometheus",
            "CORE_PEER_PROFILE_ENABLED": "false",
            "CORE_CHAINCODE_EXECUTETIMEOUT": "300s",
            # Name used by the ccaas_builder to fill {{.peername}} in the chaincode package's connection.json, so each
            # peer connects to its own institution's chaincode container (peer0inst<i>_wallet_ccaas:9999).
            # core.yaml passes this variable to the builder (propagateEnvironment). Without it the build fails.
            "CHAINCODE_AS_A_SERVICE_BUILDER_CONFIG": '{"peername":"peer0inst%d"}' % i,
            # NOTE: the peer's Docker chaincode builder is switched off in config/peercfg/core.yaml
            # (vm.endpoint: ""). An empty environment variable would be ignored by Fabric.
        }
        out.append(dict(kind="peer", host=host, ports=[port, ops], msp=f"{base}/msp", tls=f"{base}/tls",
                        env=env, data="/var/hyperledger/production", ops=ops, org=i))
    return out

def all_nodes():
    return orderers() + peers()

def fill(value, paths):
    """Replace only the path placeholders {MSP}, {TLS}, {DATA}, {CFG}; leave every other brace (e.g. JSON) alone."""
    for k, v in paths.items():
        value = value.replace("{" + k + "}", v)
    return value
