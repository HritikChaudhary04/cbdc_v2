'use strict';
/* Noop workload: endorses and commits a transaction with no state access. Isolates the fixed per-transaction cost of
   endorsement, ordering and commit (signatures, gRPC, chaincode call, block handling) from business logic. */
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');
class NoopWorkload extends WorkloadModuleBase {
    async initializeWorkloadModule(...args) { await super.initializeWorkloadModule(...args); this.tx = 0;
        this.orgs = ['Inst1MSP', 'Inst2MSP', 'Inst3MSP', 'Inst4MSP', 'Inst5MSP']; }
    async submitTransaction() {
        const org = this.orgs[(this.tx++ + this.workerIndex) % this.orgs.length];
        await this.sutAdapter.sendRequests({ contractId: 'wallet', contractFunction: 'Noop', contractArguments: [],
            invokerMspId: org, invokerIdentity: 'User1', readOnly: false });
    }
}
module.exports.createWorkloadModule = () => new NoopWorkload();
