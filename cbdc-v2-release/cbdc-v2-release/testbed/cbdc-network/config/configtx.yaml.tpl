# configtx.yaml TEMPLATE for the CBDC prototype channel (input to configtxgen).
# __BATCH_TIMEOUT__ and __MAX_MESSAGE_COUNT__ are filled in by scripts/01_generate.sh, so that the block
# size B and timeout tau of the model can be changed for each experiment without editing this file.
# Channel participation API (Fabric 2.3+): no system channel; the genesis block is joined via osnadmin.

Organizations:
  - &CentralBank
    Name: CentralBankMSP
    ID: CentralBankMSP
    MSPDir: ../organizations/ordererOrganizations/cb.cbdc.example/msp
    Policies:
      Readers:
        Type: Signature
        Rule: "OR('CentralBankMSP.member')"
      Writers:
        Type: Signature
        Rule: "OR('CentralBankMSP.member')"
      Admins:
        Type: Signature
        Rule: "OR('CentralBankMSP.admin')"
    OrdererEndpoints:
      - orderer1.cb.cbdc.example:7050
      - orderer2.cb.cbdc.example:8050
      - orderer3.cb.cbdc.example:9050

  - &Inst1
    Name: Inst1MSP
    ID: Inst1MSP
    MSPDir: ../organizations/peerOrganizations/inst1.cbdc.example/msp
    Policies:
      Readers:
        Type: Signature
        Rule: "OR('Inst1MSP.admin', 'Inst1MSP.peer', 'Inst1MSP.client')"
      Writers:
        Type: Signature
        Rule: "OR('Inst1MSP.admin', 'Inst1MSP.client')"
      Admins:
        Type: Signature
        Rule: "OR('Inst1MSP.admin')"
      Endorsement:
        Type: Signature
        Rule: "OR('Inst1MSP.peer')"
    AnchorPeers:
      - Host: peer0.inst1.cbdc.example
        Port: 7051

  - &Inst2
    Name: Inst2MSP
    ID: Inst2MSP
    MSPDir: ../organizations/peerOrganizations/inst2.cbdc.example/msp
    Policies:
      Readers:
        Type: Signature
        Rule: "OR('Inst2MSP.admin', 'Inst2MSP.peer', 'Inst2MSP.client')"
      Writers:
        Type: Signature
        Rule: "OR('Inst2MSP.admin', 'Inst2MSP.client')"
      Admins:
        Type: Signature
        Rule: "OR('Inst2MSP.admin')"
      Endorsement:
        Type: Signature
        Rule: "OR('Inst2MSP.peer')"
    AnchorPeers:
      - Host: peer0.inst2.cbdc.example
        Port: 8051

  - &Inst3
    Name: Inst3MSP
    ID: Inst3MSP
    MSPDir: ../organizations/peerOrganizations/inst3.cbdc.example/msp
    Policies:
      Readers:
        Type: Signature
        Rule: "OR('Inst3MSP.admin', 'Inst3MSP.peer', 'Inst3MSP.client')"
      Writers:
        Type: Signature
        Rule: "OR('Inst3MSP.admin', 'Inst3MSP.client')"
      Admins:
        Type: Signature
        Rule: "OR('Inst3MSP.admin')"
      Endorsement:
        Type: Signature
        Rule: "OR('Inst3MSP.peer')"
    AnchorPeers:
      - Host: peer0.inst3.cbdc.example
        Port: 9051

  - &Inst4
    Name: Inst4MSP
    ID: Inst4MSP
    MSPDir: ../organizations/peerOrganizations/inst4.cbdc.example/msp
    Policies:
      Readers:
        Type: Signature
        Rule: "OR('Inst4MSP.admin', 'Inst4MSP.peer', 'Inst4MSP.client')"
      Writers:
        Type: Signature
        Rule: "OR('Inst4MSP.admin', 'Inst4MSP.client')"
      Admins:
        Type: Signature
        Rule: "OR('Inst4MSP.admin')"
      Endorsement:
        Type: Signature
        Rule: "OR('Inst4MSP.peer')"
    AnchorPeers:
      - Host: peer0.inst4.cbdc.example
        Port: 10051

  - &Inst5
    Name: Inst5MSP
    ID: Inst5MSP
    MSPDir: ../organizations/peerOrganizations/inst5.cbdc.example/msp
    Policies:
      Readers:
        Type: Signature
        Rule: "OR('Inst5MSP.admin', 'Inst5MSP.peer', 'Inst5MSP.client')"
      Writers:
        Type: Signature
        Rule: "OR('Inst5MSP.admin', 'Inst5MSP.client')"
      Admins:
        Type: Signature
        Rule: "OR('Inst5MSP.admin')"
      Endorsement:
        Type: Signature
        Rule: "OR('Inst5MSP.peer')"
    AnchorPeers:
      - Host: peer0.inst5.cbdc.example
        Port: 11051

Capabilities:
  Channel: &ChannelCapabilities
    V2_0: true
  Orderer: &OrdererCapabilities
    V2_0: true
  Application: &ApplicationCapabilities
    V2_5: true

Application: &ApplicationDefaults
  Organizations:
  Policies:
    Readers:
      Type: ImplicitMeta
      Rule: "ANY Readers"
    Writers:
      Type: ImplicitMeta
      Rule: "ANY Writers"
    Admins:
      Type: ImplicitMeta
      Rule: "MAJORITY Admins"
    # Who must approve a chaincode definition before it can be committed: a majority of institutions.
    LifecycleEndorsement:
      Type: ImplicitMeta
      Rule: "MAJORITY Endorsement"
    # Default endorsement policy for chaincodes that do not set their own; ours sets OutOf(3, ...) explicitly.
    Endorsement:
      Type: ImplicitMeta
      Rule: "MAJORITY Endorsement"
  Capabilities:
    <<: *ApplicationCapabilities

Orderer: &OrdererDefaults
  OrdererType: etcdraft
  Addresses:
      - orderer1.cb.cbdc.example:7050
      - orderer2.cb.cbdc.example:8050
      - orderer3.cb.cbdc.example:9050
  EtcdRaft:
    Consenters:
      - Host: orderer1.cb.cbdc.example
        Port: 7050
        ClientTLSCert: ../organizations/ordererOrganizations/cb.cbdc.example/orderers/orderer1.cb.cbdc.example/tls/server.crt
        ServerTLSCert: ../organizations/ordererOrganizations/cb.cbdc.example/orderers/orderer1.cb.cbdc.example/tls/server.crt
      - Host: orderer2.cb.cbdc.example
        Port: 8050
        ClientTLSCert: ../organizations/ordererOrganizations/cb.cbdc.example/orderers/orderer2.cb.cbdc.example/tls/server.crt
        ServerTLSCert: ../organizations/ordererOrganizations/cb.cbdc.example/orderers/orderer2.cb.cbdc.example/tls/server.crt
      - Host: orderer3.cb.cbdc.example
        Port: 9050
        ClientTLSCert: ../organizations/ordererOrganizations/cb.cbdc.example/orderers/orderer3.cb.cbdc.example/tls/server.crt
        ServerTLSCert: ../organizations/ordererOrganizations/cb.cbdc.example/orderers/orderer3.cb.cbdc.example/tls/server.crt
  # Block cutting (model parameters tau and B). A block is cut when MaxMessageCount transactions are
  # pending or BatchTimeout has passed since the FIRST pending transaction, whichever comes first.
  BatchTimeout: __BATCH_TIMEOUT__
  BatchSize:
    MaxMessageCount: __MAX_MESSAGE_COUNT__
    # Byte limits set high on purpose, so blocks are always cut by COUNT or TIME, as the model assumes.
    # With Fabric's default PreferredMaxBytes (512 KB), large blocks would be cut early by size.
    AbsoluteMaxBytes: 99 MB
    PreferredMaxBytes: 64 MB
  Organizations:
  Policies:
    Readers:
      Type: ImplicitMeta
      Rule: "ANY Readers"
    Writers:
      Type: ImplicitMeta
      Rule: "ANY Writers"
    Admins:
      Type: ImplicitMeta
      Rule: "MAJORITY Admins"
    BlockValidation:
      Type: ImplicitMeta
      Rule: "ANY Writers"
  Capabilities:
    <<: *OrdererCapabilities

Channel: &ChannelDefaults
  Policies:
    Readers:
      Type: ImplicitMeta
      Rule: "ANY Readers"
    Writers:
      Type: ImplicitMeta
      Rule: "ANY Writers"
    Admins:
      Type: ImplicitMeta
      Rule: "MAJORITY Admins"
  Capabilities:
    <<: *ChannelCapabilities

Profiles:
  CBDCChannel:
    <<: *ChannelDefaults
    Orderer:
      <<: *OrdererDefaults
      Organizations:
        - *CentralBank
      Capabilities: *OrdererCapabilities
    Application:
      <<: *ApplicationDefaults
      Organizations:
        - *Inst1
        - *Inst2
        - *Inst3
        - *Inst4
        - *Inst5
      Capabilities: *ApplicationCapabilities
