import pickle,statistics as st
from ext2 import pred,cfg,wq,rows,e0,s0,s1,v0,v1,H,formation_exact,road_kingman,commit_qna
train=('B100','Q1','Q2','Q4','Q5')
for d0 in (0,25):
  for setname,sel in [('train',lambda r:r['b'] in train),('test (held out)',lambda r:r['b'] not in train)]:
    S=[r for r in rows if r['n']==5 and sel(r)]
    out={}
    for k in ('base','pU'):
        e=[]
        for r in S:
            B,tau,q=cfg[r['b']]
            v=(1000*(H(q)*e0+formation_exact(r['lam'],B,tau)+road_kingman(r['lam'],B,tau,s0,s1)[0]+commit_qna(r['lam'],B,tau,s0,s1,v0,v1)[0])+d0) if k=='base' else pred(r,r['lam']*(wq[1]+wq[0]*q),d0)
            e.append(100*(v-r['lat'])/r['lat'])
        out[k]=e
    hi=[i for i,r in enumerate(S) if r['lam']>=150]
    print(f"d0={d0:2} {setname:16} n={len(S):2} | base mean|err| {st.mean(map(abs,out['base'])):4.1f}% | extended {st.mean(map(abs,out['pU'])):4.1f}% | at >=150 TPS: base {st.mean(abs(out['base'][i]) for i in hi):4.1f}% -> ext {st.mean(abs(out['pU'][i]) for i in hi):4.1f}%")
