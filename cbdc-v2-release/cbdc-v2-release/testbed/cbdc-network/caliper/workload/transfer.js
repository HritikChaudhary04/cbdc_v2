'use strict';
/*
Transfer workload. Each transaction moves 1 unit between two different accounts.
- Clients rotate across the 5 institutions (round robin by transaction index and worker), so load is spread over all
  5 gateway peers, as for payments originating at 5 banks.
- Account choice: 'uniform' (every account equally likely: few conflicts) or 'zipf' with exponent s (a few hot
  accounts receive most of the traffic: many MVCC conflicts). The sender is drawn from the distribution; the receiver
  uniformly, so contention is driven by senders, whose balances are read and written.
Arguments (from the benchmark file): accounts, distribution ('uniform' | 'zipf'), zipfS, orgs (list of gateway MSP ids).
*/
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');

class TransferWorkload extends WorkloadModuleBase {
    async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
        await super.initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext);
        this.n = Number(roundArguments.accounts || 10000);
        this.dist = roundArguments.distribution || 'uniform';
        // gateways used by the clients (default all 5); the failure test (8g) uses only the institutions that stay up
        this.orgs = roundArguments.orgs || ['Inst1MSP', 'Inst2MSP', 'Inst3MSP', 'Inst4MSP', 'Inst5MSP'];
        this.tx = 0;
        if (this.dist === 'zipf') {                     // cumulative Zipf weights for ranks 1..n
            const s = Number(roundArguments.zipfS || 1.0);
            let c = 0; this.cdf = new Float64Array(this.n);
            for (let k = 1; k <= this.n; k++) { c += 1 / Math.pow(k, s); this.cdf[k - 1] = c; }
            for (let k = 0; k < this.n; k++) { this.cdf[k] /= c; }
        }
    }
    pick() {
        if (this.dist !== 'zipf') { return Math.floor(Math.random() * this.n); }
        const u = Math.random(); let lo = 0, hi = this.n - 1;   // binary search in the CDF
        while (lo < hi) { const mid = (lo + hi) >> 1; if (this.cdf[mid] < u) { lo = mid + 1; } else { hi = mid; } }
        return lo;
    }
    async submitTransaction() {
        const from = this.pick();
        let to = Math.floor(Math.random() * this.n);
        if (to === from) { to = (to + 1) % this.n; }
        const org = this.orgs[(this.tx + this.workerIndex) % this.orgs.length];
        this.tx++;
        await this.sutAdapter.sendRequests({
            contractId: 'wallet', contractFunction: 'Transfer',
            contractArguments: [String(from), String(to), '1'],
            invokerMspId: org, invokerIdentity: 'User1', readOnly: false
        });
    }
}
function createWorkloadModule() { return new TransferWorkload(); }
module.exports.createWorkloadModule = createWorkloadModule;
