"""Resumable runs for the validator-failure scenario (notebook 10, section 'failure'), same configs and seeds.
Two of five peers fail at t = 500 s (200 s into the measured window), load 200 TPS, B = 9."""
import sys, json, os, time, numpy as np
T0=time.time()
sys.path.insert(0, '.')
from cbdc_v2_core import *
from cbdc_v2_params import *
out = 'res10_failure_measured.json'; R = json.load(open(out)) if os.path.exists(out) else {}
WIN = [(300, 500), (500, 560), (560, 650), (650, 800), (800, 900)]
CASES = {'held_q3': dict(new_q=None, mu_e=PIPE['mu_e']),
         'lowered_q2': dict(new_q=2, mu_e=PIPE['mu_e']),
         'held_q3_mu200': dict(new_q=None, mu_e=200.0)}
for name, cs in CASES.items():
    R.setdefault(name, {})
    for i in range(10):
        if str(i) in R[name] or time.time()-T0>230: continue
        P = dict(PIPE); P['mu_e'] = cs['mu_e']
        cfg = PipelineConfig(lam=LAM_DESIGN, B=B_CHOSEN, warmup=WARMUP, measure=MEASURE, drain_limit=300.0,
                             seed=i, failures=[(500.0, [3, 4], cs['new_q'])], **P)
        r = run_pipeline(cfg); t, T = r['times']
        R[name][str(i)] = dict(windows=[float(T[(t >= a) & (t < b)].mean()) for a, b in WIN],
                               growth=float(r['growth']), stable=bool(r['stable']), unendorsable=int(r['n_unendorsable']))
        json.dump(R, open(out, 'w'), indent=1); print(name, i, flush=True)
print('ALL DONE', flush=True)
