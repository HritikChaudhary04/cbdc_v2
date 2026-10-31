"""Delay 2 (ordering 'road'): block cut epochs form a renewal process.
Interblock time A = E + C, E~Exp(lam) (gap to next block's first txn), C = min(tau, Gamma_{B-1}) (open duration).
Service S = s0 + s1*N, N = 1 + min(K_C, B-1). S_n depends only on block n, A_{n+1} only on later arrivals,
so (S_n, A_{n+1}) are independent: the road is a GI/G/1 queue. Kingman/Allen-Cunneen approximation:
Wq ~ rho/(1-rho) * (ca2 + cs2)/2 * E[S]."""
import numpy as np
from scipy.stats import poisson
from scipy.integrate import quad
from ordering_stage import simulate
def moments(lam,B,tau,s0,s1):
    """Exact moments. C = min(tau, G), G ~ Gamma(m, lam) = time of the (B-1)th later arrival."""
    from scipy.stats import gamma
    m=B-1
    if m==0: EC=EC2=0.0
    else:
        G=lambda k: gamma.cdf(tau,a=k,scale=1/lam)          # P(Gamma(k,lam) <= tau)
        EC = m/lam*G(m+1) + tau*(1-G(m))
        EC2= m*(m+1)/lam**2*G(m+2) + tau**2*(1-G(m))
    EA=1/lam+EC; EA2=2/lam**2+2*EC/lam+EC2
    mu=lam*tau; k=np.arange(0,m+int(mu)+400); p=poisson.pmf(k,mu); Nk=1+np.minimum(k,m)
    EN=np.sum(p*Nk); EN2=np.sum(p*Nk**2)
    ES=s0+s1*EN; VS=s1**2*(EN2-EN**2)
    return EA,EA2,ES,VS,EN
def road_kingman(lam,B,tau,s0,s1):
    EA,EA2,ES,VS,EN=moments(lam,B,tau,s0,s1)
    rho=ES/EA
    if rho>=1: return np.inf,rho
    ca2=(EA2-EA**2)/EA**2; cs2=VS/ES**2
    Wq=rho/(1-rho)*(ca2+cs2)/2*ES
    return Wq+ES, rho
if __name__=='__main__':
    s0,s1,tau=0.020,0.001,2.0
    print(" lam   B   rho   ca2    Kingman_road(ms)  sim_road(ms)  err%")
    for lam,B in [(200,10),(200,20),(200,50),(300,10),(300,20),(41,2),(120,4)]:
        EA,EA2,ES,VS,EN=moments(lam,B,tau,s0,s1)
        k,rho=road_kingman(lam,B,tau,s0,s1)
        reps=[simulate(lam,B,tau,s0,s1,n=100_000,warm=10_000,seed=s)[1] for s in range(5)]
        sm=np.mean(reps)
        print(f"{lam:4d} {B:3d}  {rho:.2f}  {(EA2-EA**2)/EA**2:.3f}   {k*1e3:10.1f}       {sm*1e3:9.1f}   {100*(k-sm)/sm:+.1f}")
