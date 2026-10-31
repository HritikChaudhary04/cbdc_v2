"""Resumable runs for notebook 09 (model comparison at equal capacity), same configs and seeds.
30 replications per design; replication i uses seed i for every design (common random numbers)."""
import sys, json, os
sys.path.insert(0, '.')
from cbdc_v2_core import *
from cbdc_v2_params import *
import time; T0=time.time()
out = 'res09_measured.json'; R = json.load(open(out)) if os.path.exists(out) else {}
DESIGNS = {
 'centralised': lambda s: run_queue(QueueConfig(lam=LAM_DESIGN, mu=MU_CENTRAL, c=1, warmup=WARMUP, measure=MEASURE, seed=s)),
 'parallel':    lambda s: run_queue(QueueConfig(lam=LAM_DESIGN, mu=MU_PARALLEL, c=C_PARALLEL, warmup=WARMUP, measure=MEASURE, seed=s)),
 'priority':    lambda s: run_queue(QueueConfig(lam=LAM_DESIGN, mu=MU_PRIORITY, class_probs=PRIORITY_SPLIT, warmup=WARMUP, measure=MEASURE, seed=s)),
 'fabric':      lambda s: run_pipeline(PipelineConfig(lam=LAM_DESIGN, B=B_CHOSEN, warmup=WARMUP, measure=MEASURE, seed=s, **PIPE)),
}
for name, fn in DESIGNS.items():
    R.setdefault(name, {})
    for i in range(N_REPS):
        if str(i) in R[name] or time.time()-T0>230: continue
        r = fn(i)
        R[name][str(i)] = dict(mean=float(r['mean']), p95=float(r['p95']), p99=float(r['p99']), stable=bool(r['stable']))
        json.dump(R, open(out, 'w'), indent=1)
    print(name, 'done', flush=True)
print('ALL DONE', flush=True)
