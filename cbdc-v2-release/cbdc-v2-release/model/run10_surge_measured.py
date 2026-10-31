"""Resumable runs for the surge and ramp scenarios (notebook 10), same configs and seeds.
surge_B9: 200 TPS, 2.5x surge (500 TPS) for 60 s at t=500, illustrative ledger (capacity ~310).
surge_provisioned: same surge, all service rates 1.8x faster (capacity ~560).
ramp: load rises linearly 100 -> 600 TPS over t = 300..900 (v1's ramp), reported by arrival window."""
import sys, json, os, numpy as np
sys.path.insert(0, '.')
from cbdc_v2_core import *
from cbdc_v2_formulas import capacities, surge_fluid
from cbdc_v2_params import *
import time; T0=time.time()
out = 'res10_surge_measured.json'; R = json.load(open(out)) if os.path.exists(out) else {}
edges = np.arange(300, 901, 20)
def scaled(k):
    P = dict(PIPE); P['mu_e'] *= k
    for s in ('s0', 's1', 'v0', 'v1'): P[s] /= k
    return P
CASES = {
 'surge_500':  (scaled(1.0), dict(lam=200.0, load_profile=SurgeProfile(500, 60, 2.5), load_max_mult=2.5), 10),
 'surge_1000': (scaled(1.0), dict(lam=200.0, load_profile=SurgeProfile(500, 60, 5.0), load_max_mult=5.0), 10),
 'ramp':       (scaled(1.0), dict(lam=200.0, load_profile=RampProfile(300, 600, 0.5, 5.0), load_max_mult=5.0), 5)}
for name, (P, kw, nrep) in CASES.items():
    R.setdefault(name, {'capacity': capacities(B_CHOSEN, **P)['system']})
    for i in range(nrep):
        if str(i) in R[name] or time.time()-T0>200: continue
        cfg = PipelineConfig(B=B_CHOSEN, warmup=300.0, measure=600.0, drain_limit=1200.0, seed=i, **kw, **P)
        r = run_pipeline(cfg); t, T = r['times']
        wm = [float(T[(t >= a) & (t < b)].mean()) for a, b in zip(edges[:-1], edges[1:])]
        wx = [float(T[(t >= a) & (t < b)].max()) for a, b in zip(edges[:-1], edges[1:])]
        R[name][str(i)] = dict(win_mean=wm, win_max=wx, confirmed=int(r['n_confirmed']), n=int(r['n']))
        json.dump(R, open(out, 'w'), indent=1); print(name, i, flush=True)
print('ALL DONE', flush=True)
