"""Resumable runs for notebook 04 (block size), same configs and seeds.
Grid: B in {2,4,9,20,50,100} x load in {41,120,200,300} TPS; configs with any stage utilisation >= 0.95 skipped.
3 replications x 300 s measured per config. Compares simulated stage times with the closed forms."""
import sys, json, os
sys.path.insert(0, '.')
from cbdc_v2_core import *
from cbdc_v2_formulas import *
from cbdc_v2_params import *
import time; T0=time.time(); P = PIPE; out = 'res04_measured.json'; R = json.load(open(out)) if os.path.exists(out) else {}
for lam in [41.0, 120.0, 200.0, 300.0]:
    for B in [2, 4, 10, 20, 50, 100, 500]:
        key = f'{int(lam)}_{B}'
        if key in R: continue
        if time.time()-T0>200: break
        rhos = stage_rhos(lam, B, **P)
        if max(rhos) >= 0.95:
            R[key] = dict(skipped=True, rhos=[float(x) for x in rhos]); json.dump(R, open(out, 'w'), indent=1); continue
        cfg = PipelineConfig(lam=lam, B=B, warmup=WARMUP, measure=300.0, **P)
        rr = replicate(run_pipeline, cfg, n_reps=3, keys=('mean', 'endorse', 'order', 'commit'), n_jobs=4)
        f_form = formation_exact(lam, B, P['tau']); f_road = road_kingman(lam, B, P['tau'], P['s0'], P['s1'])[0]
        f_road_ex = road_exact(lam, B, P['tau'], P['s0'], P['s1'])[0] if B <= 20 and lam*0+1 else None
        f_com = commit_qna(lam, B, P['tau'], P['s0'], P['s1'], P['v0'], P['v1'])[0]
        R[key] = dict(skipped=False, rhos=[float(x) for x in rhos],
                      sim={k: [float(rr[k][0]), float(rr[k][1])] for k in ('mean', 'endorse', 'order', 'commit')},
                      formula=dict(total=float(end_to_end(lam, B, **P)), formation=float(f_form), road=float(f_road),
                                   road_exact=None if f_road_ex is None else float(f_road_ex), commit=float(f_com)))
        json.dump(R, open(out, 'w'), indent=1); print(key, flush=True)
print('ALL DONE', flush=True)
