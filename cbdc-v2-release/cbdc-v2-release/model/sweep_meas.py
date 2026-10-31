import json
from cbdc_v2_core import *; from cbdc_v2_formulas import *; from cbdc_v2_params import *
import os,sys
P=PIPE; R=json.load(open('res10_sweep_measured.json')) if os.path.exists('res10_sweep_measured.json') else {}
NMAX=int(sys.argv[1]) if len(sys.argv)>1 else 99; done=0
def best_B(lam):
    best=None
    for B in range(2,301):
        if max(stage_rhos(lam,B,**P))<0.95:
            e=end_to_end(lam,B,**P)
            if best is None or e<best[1]: best=(B,e)
    return best[0]
for mode in ['fixed','rechosen']:
    for lam in [25.0,50.0,100.0,150.0,200.0,250.0,300.0]:
        if f'{mode}_{int(lam)}' in R: continue
        if done>=NMAX: break
        done+=1
        B=B_CHOSEN if mode=='fixed' else best_B(lam)
        rr=replicate(run_pipeline,PipelineConfig(lam=lam,B=B,warmup=WARMUP,measure=MEASURE,**P),n_reps=3,keys=('mean','p95','p99'),n_jobs=4)
        R[f'{mode}_{int(lam)}']=dict(B=B,rhos=[float(x) for x in stage_rhos(lam,B,**P)],formula=float(end_to_end(lam,B,**P)),
            sim={k:[float(rr[k][0]),float(rr[k][1])] for k in ('mean','p95','p99')},stable=bool(rr['stable_all']))
        json.dump(R,open('res10_sweep_measured.json','w'),indent=1); print(mode,lam,B,flush=True)
print('ALL DONE')
