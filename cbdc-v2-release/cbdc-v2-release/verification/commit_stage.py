"""Commit stage: blocks leaving the ordering road are delivered to every peer; the client waits for
its own gateway peer, a single FCFS server processing whole blocks, V = v0 + v1*N.
Arrivals to the peer = departures of the road (not renewal). QNA linking equation (Whitt 1983):
cd2 = rho_o^2 * cs2 + (1 - rho_o^2) * ca2, then Kingman at the peer with arrival scv cd2.
ILLUSTRATIVE costs: road s0=20 ms/block + s1=1 ms/txn; commit v0=10 ms/block + v1=2 ms/txn."""
import numpy as np
from road_queue import moments
def simulate_chain(lam,B,tau,s0,s1,v0,v1,n=150_000,warm=15_000,seed=0):
    rng=np.random.default_rng(seed); arr=np.cumsum(rng.exponential(1/lam,n))
    i=0; road_free=0.0; peer_free=0.0; commit=np.empty(n)
    while i<n:
        start=arr[i]; j=i
        while j+1<n and j+1-i<B and arr[j+1]<start+tau: j+=1
        N=j-i+1; cut=arr[j] if N==B else start+tau
        road_free=max(road_free,cut)+s0+s1*N           # leaves ordering road
        peer_free=max(peer_free,road_free)+v0+v1*N     # committed at gateway peer
        commit[i:j+1]=peer_free-road_free; i=j+1
    return commit[warm:].mean()
def commit_qna(lam,B,tau,s0,s1,v0,v1):
    EA,EA2,ES,VS,EN=moments(lam,B,tau,s0,s1)
    ca2=(EA2-EA**2)/EA**2; cs2=VS/ES**2; rho_o=ES/EA
    cd2=rho_o**2*cs2+(1-rho_o**2)*ca2                 # departure scv from the road
    EV=v0+v1*EN; VV=v1**2*(VS/s1**2) if s1>0 else 0  # Var(N) = VS/s1^2
    cv2=VV/EV**2; rho_c=EV/EA
    if rho_c>=1: return np.inf,rho_c,cd2,ca2
    Wq=rho_c/(1-rho_c)*(cd2+cv2)/2*EV
    # naive (ignores smoothing by the road): use ca2 instead of cd2
    return Wq+EV, rho_c, cd2, ca2
if __name__=='__main__':
    s0,s1,v0,v1,tau=0.020,0.001,0.010,0.002,2.0
    print(" lam   B  rho_road rho_commit  ca2_in  cd2_QNA   QNA(ms)   sim(ms)    err%")
    for lam,B in [(41,2),(120,4),(200,10),(200,20),(250,10),(300,20)]:
        q,rc,cd2,ca2=commit_qna(lam,B,tau,s0,s1,v0,v1)
        EA,_,ES,_,_=moments(lam,B,tau,s0,s1)
        sims=[simulate_chain(lam,B,tau,s0,s1,v0,v1,seed=s) for s in range(5)]
        sm=np.mean(sims)
        print(f"{lam:4d} {B:3d}   {ES/EA:.2f}     {rc:.2f}     {ca2:.3f}   {cd2:.3f}   {q*1e3:7.2f}  {sm*1e3:7.2f}   {100*(q-sm)/sm:+.1f}")
