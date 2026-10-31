"""End-to-end check: endorsement (per-peer FCFS M/M/1, default or hedged) -> ordering (formation B/tau
+ road) -> commit at the client's gateway peer. Transactions enter ordering in endorsement-completion
order. Compares the full-chain simulation with the sum of the stage formulas.
ILLUSTRATIVE: mu_e=200/s, c=5, q=3; road s0=20 ms + s1=1 ms/txn; commit v0=10 ms + v1=2 ms/txn; tau=2 s."""
import numpy as np
from endorsement_check import formula as end_formula
from ordering_stage import formation_exact
from road_queue import road_kingman
from commit_stage import commit_qna
def chain(lam,rule,B,tau,mu,c,q,s0,s1,v0,v1,n=120_000,warm=12_000,seed=0):
    rng=np.random.default_rng(seed); arr=np.cumsum(rng.exponential(1/lam,n))
    free=np.zeros(c); te=np.empty(n)
    for i,a in enumerate(arr):
        peers=rng.choice(c,q,replace=False) if rule=='default' else np.arange(c)
        done=np.maximum(free[peers],a)+rng.exponential(1/mu,len(peers)); free[peers]=done
        te[i]=done.max() if rule=='default' else np.partition(done,q-1)[q-1]
    order=np.argsort(te); t_in=te[order]                 # arrival order at the orderer
    total=np.empty(n); stage=np.zeros((n,3)); i=0; road=0.0; peer=0.0
    while i<n:
        start=t_in[i]; j=i
        while j+1<n and j+1-i<B and t_in[j+1]<start+tau: j+=1
        N=j-i+1; cut=t_in[j] if N==B else start+tau
        road=max(road,cut)+s0+s1*N; peer=max(peer,road)+v0+v1*N
        idx=order[i:j+1]; total[idx]=peer-arr[idx]
        stage[idx,0]=te[idx]-arr[idx]; stage[idx,1]=road-te[idx]; stage[idx,2]=peer-road
        i=j+1
    keep=slice(warm,n-warm)
    return total[keep].mean(), stage[keep].mean(0)
if __name__=='__main__':
    mu,c,q,tau=200,5,3,2.0; s0,s1,v0,v1=0.020,0.001,0.010,0.002
    print("rule     lam  B | formulas: endorse order commit = total | sim: endorse order commit = total | err%")
    for rule,lam,B in [('default',41,2),('default',100,4),('default',150,8),('default',200,10),('hedged',41,2),('hedged',100,4)]:
        fe=end_formula(rule,lam,mu,c,q); fo=formation_exact(lam,B,tau)+road_kingman(lam,B,tau,s0,s1)[0]
        fc=commit_qna(lam,B,tau,s0,s1,v0,v1)[0]; ft=fe+fo+fc
        res=[chain(lam,rule,B,tau,mu,c,q,s0,s1,v0,v1,seed=s) for s in range(4)]
        st=np.mean([r[1] for r in res],0); tt=np.mean([r[0] for r in res])
        print(f"{rule:8s} {lam:3d} {B:2d} | {fe*1e3:6.1f} {fo*1e3:6.1f} {fc*1e3:6.1f} = {ft*1e3:6.1f} | {st[0]*1e3:6.1f} {st[1]*1e3:6.1f} {st[2]*1e3:6.1f} = {tt*1e3:6.1f} | {100*(ft-tt)/tt:+.1f}")
