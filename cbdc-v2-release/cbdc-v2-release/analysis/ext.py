import pickle,numpy as np,statistics as st
from scipy.optimize import least_squares
from cbdc_v2_formulas import formation_exact,road_kingman,commit_qna
H=lambda n: sum(1/k for k in range(1,n+1))
rows=pickle.load(open('rows.pkl','rb'))
cfg={'A':(50,2.0,3),'B10':(10,2.0,3),'B100':(100,2.0,3),'B500':(500,2.0,3),'T025':(50,0.25,3),'T1':(50,1.0,3),'Q1':(100,2.0,1),'Q2':(100,2.0,2),'Q4':(100,2.0,4),'Q5':(100,2.0,5)}
s0,s1,v0,v1=0.01488,0.0000494,0.00868,0.0005447
# CPU work per tx at low load vs q (50 TPS rows)
lo=[r for r in rows if r['lam']==50]; q=np.array([cfg[r['b']][2] for r in lo]); w=np.array([r['U']/r['lam'] for r in lo])
wq=np.polyfit(q,w,1); print('w(q) = %.2f + %.2f q  ms CPU per tx (50 TPS)'%(1000*wq[1],1000*wq[0]))
def predict(b,lam,C,ac,e0,d0,U=None):
    B,tau,qq=cfg[b]
    if U is None: U=lam*(wq[1]+wq[0]*qq)
    x=1-U/C
    if x<=0.02: return np.inf
    e=e0/x; Te=H(qq)*e
    k=x**(-ac)
    Wf=formation_exact(lam,B,tau); Wo=road_kingman(lam,B,tau,s0,s1)[0]; Wc=commit_qna(lam,B,tau,s0,s1,v0*k,v1*k)[0]
    return 1000*(Te+Wf+Wo+Wc)+d0
train=[r for r in rows if r['b'] in ('B100','Q1','Q2','Q4','Q5')]
test=[r for r in rows if r['b'] not in ('B100','Q1','Q2','Q4','Q5')]
def res(p): return [(predict(r['b'],r['lam'],*p)-r['lat'])/r['lat'] for r in train]
p=least_squares(res,[8,0.5,0.0024,20],bounds=([4,0,0.001,0],[20,3,0.006,200])).x
print('fitted on B100+Q1..Q5 (%d points): C_eff=%.2f cores, alpha_commit=%.2f, e0=%.2f ms, fixed overhead d0=%.0f ms'%(len(train),p[0],p[1],1000*p[2],p[3]))
print('\nblock lam | measured | base model (fixed rates) | EXTENDED (predicted CPU) | error base / extended')
errs={'train':[],'test':[]}
for r in sorted(rows,key=lambda r:(r['b'],r['lam'])):
    B,tau,qq=cfg[r['b']]
    base=1000*(H(qq)*0.00246+formation_exact(r['lam'],B,tau)+road_kingman(r['lam'],B,tau,s0,s1)[0]+commit_qna(r['lam'],B,tau,s0,s1,v0,v1)[0])
    ext=predict(r['b'],r['lam'],*p)
    tag='train' if r in train else 'test'; e1=100*(ext-r['lat'])/r['lat']; errs[tag].append(abs(e1))
    print(f"{r['b']:5} {r['lam']:4} | {r['lat']:6.0f} ({r['n']}/5) | {base:6.0f} | {ext:6.0f} | {100*(base-r['lat'])/r['lat']:+4.0f}% / {e1:+4.0f}%  [{tag}]")
for k,v in errs.items(): print(k,'mean |error| %.1f%%, max %.1f%%'%(st.mean(v),max(v)))
B,tau=100,2.0
for qq,b in [(3,'B100'),(3,'A')]:
    lamx=next(l for l in range(50,1000,5) if not np.isfinite(predict(b,l,*p)))
    print(b,'predicted CPU limit (U -> C_eff) ~',lamx,'TPS')
