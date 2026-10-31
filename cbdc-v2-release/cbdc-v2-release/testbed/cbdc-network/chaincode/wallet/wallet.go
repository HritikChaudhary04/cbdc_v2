/*
CBDC wallet chaincode for the confirmation-time prototype (Hyperledger Fabric 2.5, Go, chaincode as a service).

State: one key per account, "acct_<id>", whose value is the balance as a decimal integer (smallest unit).

Functions
  Transfer(from, to, amount)          move funds; fails if from has insufficient balance  (measured workload)
  Balance(id)                         read a balance                                       (query)
  Noop()                              does nothing; isolates the fixed cost of endorsement (calibration)
  Mint(id, amount)                    create funds in an account          (set-up only; institution admins)
  InitAccounts(start, count, amount)  create accounts start..start+count-1 (set-up only; institution admins)

How double spending is prevented: Transfer READS the sender's balance during endorsement and records the key and
its version in the transaction's read set. At commit, every peer checks that the version is unchanged (Fabric's
MVCC check). If another committed transaction changed the balance in between, this transaction is marked invalid
(MVCC_READ_CONFLICT) and has no effect. Two transfers that spend the same balance can therefore never both
commit. Transfers touching popular ("hot") accounts conflict more often, which is the contention effect measured
in the prototype.

Prototype simplifications (stated in the paper): accounts are not bound to individual client identities (any
client of an institution may submit a transfer); issuance (Mint, InitAccounts) is limited to institution
administrators, because in this network the central bank operates only the ordering service. Issuance is a
set-up step and is not part of any measured workload.
*/
package main

import (
	"fmt"
	"strconv"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// Wallet is the chaincode; contractapi exposes each exported method as a transaction function.
type Wallet struct {
	contractapi.Contract
}

func accountKey(id string) string { return "acct_" + id }

// readBalance returns the balance of an account and whether it exists. Reading puts the key in the read set.
func readBalance(ctx contractapi.TransactionContextInterface, id string) (int64, bool, error) {
	b, err := ctx.GetStub().GetState(accountKey(id))
	if err != nil {
		return 0, false, fmt.Errorf("failed to read account %s: %v", id, err)
	}
	if b == nil {
		return 0, false, nil
	}
	v, err := strconv.ParseInt(string(b), 10, 64)
	if err != nil {
		return 0, false, fmt.Errorf("corrupt balance for account %s: %v", id, err)
	}
	return v, true, nil
}

func writeBalance(ctx contractapi.TransactionContextInterface, id string, v int64) error {
	return ctx.GetStub().PutState(accountKey(id), []byte(strconv.FormatInt(v, 10)))
}

// requireAdmin allows only institution administrators (certificate OU "admin", from cryptogen's NodeOUs).
func requireAdmin(ctx contractapi.TransactionContextInterface) error {
	cert, err := ctx.GetClientIdentity().GetX509Certificate()
	if err != nil {
		return fmt.Errorf("cannot read client certificate: %v", err)
	}
	for _, ou := range cert.Subject.OrganizationalUnit {
		if ou == "admin" {
			return nil
		}
	}
	return fmt.Errorf("only institution administrators may issue funds")
}

// Transfer moves amount from one account to another, rejecting overdrafts.
func (w *Wallet) Transfer(ctx contractapi.TransactionContextInterface, from string, to string, amount int64) error {
	if amount <= 0 {
		return fmt.Errorf("amount must be positive")
	}
	if from == to {
		return fmt.Errorf("sender and receiver must differ")
	}
	fb, ok, err := readBalance(ctx, from)
	if err != nil {
		return err
	}
	if !ok {
		return fmt.Errorf("account %s does not exist", from)
	}
	if fb < amount {
		return fmt.Errorf("insufficient funds in %s", from)
	}
	tb, ok, err := readBalance(ctx, to)
	if err != nil {
		return err
	}
	if !ok {
		return fmt.Errorf("account %s does not exist", to)
	}
	if err := writeBalance(ctx, from, fb-amount); err != nil {
		return err
	}
	return writeBalance(ctx, to, tb+amount)
}

// Balance returns the balance of an account.
func (w *Wallet) Balance(ctx contractapi.TransactionContextInterface, id string) (int64, error) {
	v, ok, err := readBalance(ctx, id)
	if err != nil {
		return 0, err
	}
	if !ok {
		return 0, fmt.Errorf("account %s does not exist", id)
	}
	return v, nil
}

// Noop does nothing. Endorsing it measures the fixed cost of endorsement (signature checks, gRPC, chaincode
// call) without any state access; comparing Noop with Transfer separates fixed cost from business logic.
func (w *Wallet) Noop(ctx contractapi.TransactionContextInterface) error {
	return nil
}

// Mint adds amount to an account, creating it if necessary (administrators only).
func (w *Wallet) Mint(ctx contractapi.TransactionContextInterface, id string, amount int64) error {
	if err := requireAdmin(ctx); err != nil {
		return err
	}
	if amount <= 0 {
		return fmt.Errorf("amount must be positive")
	}
	v, _, err := readBalance(ctx, id)
	if err != nil {
		return err
	}
	return writeBalance(ctx, id, v+amount)
}

// InitAccounts creates accounts "<start>" .. "<start+count-1>" with the given balance (administrators only).
// Accounts are created in chunks (for example 1000 per call) to keep each transaction small.
func (w *Wallet) InitAccounts(ctx contractapi.TransactionContextInterface, start int, count int, amount int64) error {
	if err := requireAdmin(ctx); err != nil {
		return err
	}
	if count <= 0 || count > 5000 {
		return fmt.Errorf("count must be between 1 and 5000")
	}
	for i := start; i < start+count; i++ {
		if err := writeBalance(ctx, strconv.Itoa(i), amount); err != nil {
			return err
		}
	}
	return nil
}
