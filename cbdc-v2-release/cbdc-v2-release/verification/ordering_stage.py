"""Ordering stage = block formation (size B or timer tau from first txn) followed by a single FCFS
'road' that processes one block at a time, time S = s0 + s1*N for a block of N txns.
Formation is assumed independent of the road (blocks are cut even while the road is busy).
ILLUSTRATIVE s0, s1 until the prototype measures them."""
import numpy as np, math
def simulate(lam,B,tau,s0,s1,n=200_000,warm=20_000,seed=0):
    rng=np.random.default_rng(seed); arr=np.cumsum(rng.exponential(1/lam,n))
    form=np.empty(n); road=np.empty(n); free=0.0; i=0
    while i<n:
        start=arr[i]; j=i
        while j+1<n and j+1-i<B and arr[j+1]<start+tau: j+=1
        N=j-i+1; cut=arr[j] if N==B else start+tau
        begin=max(free,cut); S=s0+s1*N; free=begin+S
        form[i:j+1]=cut-arr[i:j+1]; road[i:j+1]=free-cut
        i=j+1
    return form[warm:].mean(), road[warm:].mean()
def formation_exact(lam,B,tau):
    """Mean formation wait (renewal-reward): int_0^tau [F(m-1;lam t) + lam t F(m-2;lam t)] dt / (1+E[min(K,m)]),
    m=B-1, F = Poisson cdf, K~Poi(lam*tau). Limits: m->inf gives (tau+lam tau^2/2)/(1+lam tau); tau->inf gives (B-1)/(2 lam)."""
    from scipy.stats import poisson
    from scipy.integrate import quad
    m=B-1
    g=lambda t: poisson.cdf(m-1,lam*t)+lam*t*poisson.cdf(m-2,lam*t)
    num=quad(g,0,tau,limit=200)[0]
    mu=lam*tau; EminK=mu*poisson.cdf(m-2,mu)+m*(1-poisson.cdf(m-1,mu))
    return num/(1+EminK)
if __name__=='__main__':
    s0,s1,tau=0.020,0.001,2.0
    print("Check exact formation formula vs simulation:")
    for lam,B in [(1,10),(5,10),(50,100),(200,50)]:
        print(f"  lam={lam} B={B}: exact {formation_exact(lam,B,tau)*1e3:.1f} ms, sim {simulate(lam,B,tau,s0,s1)[0]*1e3:.1f} ms")
    for lam in [200,300]:
        print(f"\nlam={lam} TPS, tau={tau}s, s0={s0*1e3:.0f}ms/block, s1={s1*1e3:.0f}ms/txn")
        print("   B   formation(ms)  road(ms)  total(ms)  road utilisation")
        for B in [5,10,20,30,50,100,200]:
            fo,ro=simulate(lam,B,tau,s0,s1)
            rho=lam*(s1+s0/B)
            print(f" {B:4d}   {fo*1e3:9.1f}  {ro*1e3:9.1f}  {(fo+ro)*1e3:9.1f}    {rho:.2f}")
