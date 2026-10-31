"""Check endorsement-stage formulas against a fork-join simulation with FCFS M/M/1 peers.
Default rule: each txn sent to a uniformly random q-subset of c peers, done when all q finish.
Hedged rule: each txn sent to all c peers (no cancellation), done at the q-th completion."""
import numpy as np
H=lambda n: sum(1/k for k in range(1,n+1))
def formula(rule,lam,mu,c,q):
    if rule=='default':
        nu=mu-lam*q/c; return H(q)/nu if nu>0 else np.inf
    nu=mu-lam; return (H(c)-H(c-q))/nu if nu>0 else np.inf
def simulate(rule,lam,mu,c,q,n=200_000,warm=20_000,seed=0):
    rng=np.random.default_rng(seed)
    arr=np.cumsum(rng.exponential(1/lam,n))
    free=np.zeros(c)                      # time each peer becomes free (FCFS Lindley)
    T=np.empty(n)
    for i,a in enumerate(arr):
        peers=rng.choice(c,q,replace=False) if rule=='default' else np.arange(c)
        s=rng.exponential(1/mu,len(peers))
        done=np.maximum(free[peers],a)+s
        free[peers]=done
        T[i]=(done.max() if rule=='default' else np.partition(done,q-1)[q-1])-a
    return T[warm:]
if __name__=='__main__':
    mu,c,q=200,5,3
    print("rule     lam  formula_ms  sim_ms(±95%CI over 10 reps)  err%")
    for rule in ['default','hedged']:
        for lam in [50,100,150,180]:
            f=formula(rule,lam,mu,c,q)*1e3
            reps=[simulate(rule,lam,mu,c,q,n=60_000,warm=6_000,seed=s).mean()*1e3 for s in range(10)]
            m=np.mean(reps); ci=1.96*np.std(reps,ddof=1)/np.sqrt(len(reps))
            print(f"{rule:8s} {lam:4d}  {f:9.2f}  {m:8.2f} ± {ci:.2f}            {100*(f-m)/m:+.1f}")
    # crossover
    lo,hi=1,199
    for _ in range(60):
        mid=(lo+hi)/2
        if formula('hedged',mid,mu,c,q)<formula('default',mid,mu,c,q): lo=mid
        else: hi=mid
    print(f"formula crossover lam* = {lo:.1f} TPS")
