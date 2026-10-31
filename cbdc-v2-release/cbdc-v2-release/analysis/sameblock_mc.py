import numpy as np
rng=np.random.default_rng(1)
def sim(N,dist,s=1.0,B=50,blocks=4000):
    if dist=='zipf':
        p=1/np.arange(1,N+1)**s; p/=p.sum()
    inval=0;tot=0
    for _ in range(blocks):
        fr = rng.choice(N,B,p=p) if dist=='zipf' else rng.integers(0,N,B)
        to = rng.integers(0,N,B); to=np.where(to==fr,(to+1)%N,to)
        written=set()
        for a,b in zip(fr,to):
            tot+=1
            if a in written or b in written: inval+=1
            else: written.add(a); written.add(b)
    return inval/tot
for N in (10000,1000,100): print('uniform',N, round(100*sim(N,'u'),2))
for s in (0.8,1.0,1.2): print('zipf',s, round(100*sim(10000,'zipf',s),2))
