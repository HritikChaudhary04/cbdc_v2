import csv,glob,json,statistics as st,re,numpy as np
from params import blocks
from scipy.optimize import least_squares
R=list(csv.DictReader(open('campaign_rounds.csv')))
def cores(f):
    c=json.load(open(f))['cpu_percent_mean']; return sum(v for k,v in c.items() if 'peer0' in k or 'orderer' in k)/100
rows=[]
for b in ['A','B10','B100','B500','T025','T1','Q1','Q2','Q4','Q5']:
    for lab in sorted({x['round'] for x in R if x['block']==b and x['round'].startswith('uniform')}):
        lam=int(re.search(r'(\d+)tps',lab).group(1))
        H=[x for x in R if x['block']==b and x['round']==lab and float(x['fail_frac'])<0.06 and float(x['steady_tps'])>0.97*lam]
        if not H: continue
        cs=[];pts=[]
        for x in H:
            rd=glob.glob(f"*-{b}-rep{x['rep']}/[0-9][0-9]-{lab}")[0]; cs.append(cores(rd+'/summary.json')); pts+=blocks(rd)
        N=st.mean(p[0] for p in pts)
        rows.append(dict(b=b,lam=lam,U=st.mean(cs),e=st.mean(float(x['endorse_ms']) for x in H),
            o=st.mean(p[1] for p in pts),c=st.mean(p[2] for p in pts),N=N,lat=1000*st.mean(float(x['avg_lat_s']) for x in H),n=len(H)))
# baselines (low-load service): endorse 2.3 ms sojourn-free? use fitted e0; order s0+s1N; commit v0+v1N
s0,s1,v0,v1=14.88,0.0494,8.68,0.5447
for r in rows: r['ro']=r['o']/(s0+s1*r['N']); r['rc']=r['c']/(v0+v1*r['N'])
train=[r for r in rows if r['b'] in ('B100','Q1','Q2','Q4','Q5')]
def fit(key,f0=True):
    def res(p):
        C,a,e0=p; return [ (np.log(r[key] if key=='e' else r[key]) - np.log((e0 if key=='e' else 1)* (1-min(r['U']/C,0.99))**(-a))) for r in train]
    p=least_squares(res,[8,1,2.3],bounds=([5,0.05,0.5],[20,5,5])).x; return p
for k in ['e','ro','rc']:
    C,a,e0=fit(k); print(f"{k}: C_eff={C:.2f} cores, alpha={a:.2f}, base={e0 if k=='e' else 1:.2f}")
for r in rows: print(f"{r['b']:5} {r['lam']:4} U={r['U']:.2f} cores  e={r['e']:.1f}ms  order x{r['ro']:.2f}  commit x{r['rc']:.2f}  lat {r['lat']:.0f} ({r['n']} healthy)")
import pickle; pickle.dump(rows,open('rows.pkl','wb'))
