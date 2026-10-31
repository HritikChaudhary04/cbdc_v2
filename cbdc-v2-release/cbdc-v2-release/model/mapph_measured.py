"""Steps 10-13 with MEASURED mu_e = 436/s: endorsement under PH service (SCV 0.5, 1, 2), Poisson / mild / stress arrivals.
Usage: python3 mapph_measured.py analysis | sim"""
import json, os, sys, time, numpy as np
from cbdc_v2_map import *
mu=436.0; c,q=5,3; RNB,RBN=1/120,1/30
ARR={'poisson':None,'mild':(175,300),'stress':(50,800)}
out='res_mapph_measured.json'; R=json.load(open(out)) if os.path.exists(out) else {}
T0=time.time()
if sys.argv[1]=='analysis':
    for a,lr in ARR.items():
        D0,D1=poisson_map(200.0) if lr is None else mmpp2(*lr,RNB,RBN)
        for scv in [0.5,1.0,2.0]:
            key=f'{a}_{scv}'
            if key in R.get('analysis',{}) or time.time()-T0>200: continue
            Dp0,Dp1=thin(D0,D1,q/c); b,S=ph_service(1/mu,scv); w,lst,peer=map_ph1_sojourn_lst(Dp0,Dp1,b,S)
            e,_,_=endorsement_time_map_ph(D0,D1,mu,scv,c,q)
            R.setdefault('analysis',{})[key]=dict(peer=peer,endorse=e); json.dump(R,open(out,'w'),indent=1); print(key,round(1000*peer,3),round(1000*e,3),flush=True)
else:
    from map_ph_sim import run
    for a,lr in ARR.items():
        for scv in [0.5,1.0,2.0]:
            for s in range(4):
                key=f'{a}_{scv}_{s}'
                if key in R.get('sim',{}) or time.time()-T0>200: continue
                T=20000.0 if a=='stress' else 4000.0
                R.setdefault('sim',{})[key]=run((200,200) if lr is None else lr,scv,T=T,mu=mu,seed=s); json.dump(R,open(out,'w'),indent=1); print(key,flush=True)
