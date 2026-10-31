/*
Entry point: runs the wallet as a chaincode SERVICE (chaincode as a service). Instead of the peer building and
launching the chaincode, this program listens on CHAINCODE_SERVER_ADDRESS (0.0.0.0:9999) and the peer connects
to it, as described by connection.json in the chaincode package. Structure follows Fabric's official sample
fabric-samples/asset-transfer-basic/chaincode-external. TLS between peer and chaincode is disabled inside the
private Docker network (CHAINCODE_TLS_DISABLED defaults to true), as in that sample.
*/
package main

import (
	"log"
	"os"
	"strconv"

	"github.com/hyperledger/fabric-chaincode-go/v2/shim"
	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

func main() {
	chaincode, err := contractapi.NewChaincode(&Wallet{})
	if err != nil {
		log.Panicf("error creating wallet chaincode: %s", err)
	}
	server := &shim.ChaincodeServer{
		CCID:     os.Getenv("CHAINCODE_ID"),
		Address:  os.Getenv("CHAINCODE_SERVER_ADDRESS"),
		CC:       chaincode,
		TLSProps: shim.TLSProperties{Disabled: tlsDisabled()},
	}
	if err := server.Start(); err != nil {
		log.Panicf("error starting wallet chaincode server: %s", err)
	}
}

func tlsDisabled() bool {
	v, ok := os.LookupEnv("CHAINCODE_TLS_DISABLED")
	if !ok {
		return true
	}
	b, err := strconv.ParseBool(v)
	if err != nil {
		return true
	}
	return b
}
