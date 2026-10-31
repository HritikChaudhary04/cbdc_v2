"""Block formation delay under Fabric's rule: a block opens at its first transaction and is cut
when B transactions are in it or tau seconds after it opened, whichever is first.
Returns mean time a transaction waits from its arrival until its block is cut (formation only)."""
import numpy as np
def formation_wait(lam,B,tau,n=200_000,seed=0):
    rng=np.random.default_rng(seed); arr=np.cumsum(rng.exponential(1/lam,n))
    waits=[]; i=0
    while i<n:
        start=arr[i]; j=i
        while j+1<n and j+1-i<B and arr[j+1]<start+tau: j+=1
        cut = arr[j] if j-i+1==B else start+tau
        waits.extend(cut-arr[i:j+1]); i=j+1
    return np.mean(waits)
if __name__=='__main__':
    for B,tau in [(10,2.0),(100,2.0)]:
        print(f"B={B}, tau={tau}s")
        for lam in [1,5,10,50,100,200]:
            w=formation_wait(lam,B,tau)
            print(f"  lam={lam:4d}  wait={w*1e3:8.1f} ms   size-rule (B-1)/(2lam)={(B-1)/(2*lam)*1e3:8.1f} ms")
