"""Institutions sweep with MEASURED parameters (2026-10-22): c = 3..11, majority q, both dispatch rules at 200 TPS
(hedged capacity is now mu_e = 436 TPS), B = B_CHOSEN = 100, 5 reps x 400 s. Output res03_measured.json."""
import sys, json, math, os, time
from cbdc_v2_core import *; from cbdc_v2_formulas import *; from cbdc_v2_params import *
T0=time.time(); P=PIPE; out='res03_measured.json'; R=json.load(open(out)) if os.path.exists(out) else {}
cfg0=PipelineConfig(lam=LAM_DESIGN,B=B_CHOSEN,warmup=WARMUP,measure=MEASURE,**P)
for rule in ['default','hedged']:
    for c in range(3,12):
        key=f'{rule}_{c}'
        if key in R or time.time()-T0>200: continue
        q=math.ceil((c+1)/2)
        rr=replicate(run_pipeline,replace(cfg0,c=c,q=q,dispatch=rule,measure=400.0),n_reps=5,keys=('endorse','mean'),n_jobs=4)
        R[key]=dict(c=c,q=q,cap=(c*P['mu_e']/q if rule=='default' else P['mu_e']),formula=endorsement_time(rule,LAM_DESIGN,P['mu_e'],c,q),
            endorse=[rr['endorse'][0],rr['endorse'][1]],total=[rr['mean'][0],rr['mean'][1]],stable=rr['stable_all'])
        json.dump(R,open(out,'w'),indent=1); print(key,flush=True)
print('DONE',len(R))
