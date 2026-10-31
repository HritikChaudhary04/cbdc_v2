import pickle,numpy as np,statistics as st
from ext import cfg,s0,s1,v0,v1,wq,H,formation_exact,road_kingman,commit_qna
rows=pickle.load(open('rows.pkl','rb'))
C,ae,ac,e0=7.8,1.0,0.5,0.00247   # stage laws fitted separately (endorse C=8.05 a=1.09; commit C=7.40 a=0.49)
def pred(r,U,d0=0):
    B,tau,q=cfg[r['b']]; x=1-U/C
    if x<=0.02: return np.inf
    k=x**(-ac); Te=H(q)*e0*x**(-ae)
    return 1000*(Te+formation_exact(r['lam'],B,tau)+road_kingman(r['lam'],B,tau,s0,s1)[0]+commit_qna(r['lam'],B,tau,s0,s1,v0*k,v1*k)[0])+d0
# fixed overhead: mean residual at 50 TPS (low load, all configs)
lo=[r for r in rows if r['lam']==50]; d0=st.mean(r['lat']-pred(r,r['U']) for r in lo); print('fixed overhead d0 from 50 TPS rows: %.0f ms'%d0)
# CPU growth: per-tx CPU vs U?  fit w = w0(q) * (1 + g*U)
import numpy as np
g=np.mean([ (r['U']/r['lam'])/(wq[1]+wq[0]*cfg[r['b']][2]) for r in rows if r['lam']>=150 and r['n']==5])
print('per-tx CPU at >=150 TPS is %.2f x the 50 TPS value'%g)
print('block lam | meas | base | ext (measured U) | ext (predicted U, low-load w) | errors')
E={'mU':[],'pU':[],'base':[]}
for r in sorted(rows,key=lambda r:(r['b'],r['lam'])):
    if r['n']<5: continue   # skip groups with <5 healthy reps (single-rep points)
    B,tau,q=cfg[r['b']]
    base=1000*(H(q)*e0+formation_exact(r['lam'],B,tau)+road_kingman(r['lam'],B,tau,s0,s1)[0]+commit_qna(r['lam'],B,tau,s0,s1,v0,v1)[0])+d0
    a=pred(r,r['U'],d0); Up=r['lam']*(wq[1]+wq[0]*q); b=pred(r,Up,d0)
    for k,v in [('base',base),('mU',a),('pU',b)]: E[k].append(100*(v-r['lat'])/r['lat'])
    print(f"{r['b']:5} {r['lam']:4} | {r['lat']:5.0f} | {base:5.0f} {E['base'][-1]:+4.0f}% | {a:5.0f} {E['mU'][-1]:+4.0f}% | {b:5.0f} {E['pU'][-1]:+4.0f}%  (U meas {r['U']:.1f}, pred {Up:.1f})")
for k,v in E.items(): print(k,'mean |err| %.1f%%  max |err| %.1f%%  mean signed %+.1f%%'%(st.mean(map(abs,v)),max(map(abs,v)),st.mean(v)))
