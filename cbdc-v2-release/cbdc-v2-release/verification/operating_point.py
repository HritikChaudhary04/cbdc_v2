"""Capacity-planning procedure (A-3). Given per-peer endorsement rate mu_e, block costs (s0, s1),
commit costs (v0, v1), timer tau, design load lam_d and headroom rho_max:
 1. endorsement: default rule needs lam_d*q/(c*mu_e) <= rho_max (hedged needs lam_d <= rho_max*mu_e)
 2. smallest feasible B: lam_d*(s0/B + s1) <= rho_max and lam_d*(v0/B + v1) <= rho_max
    (needs s1, v1 < rho_max/lam_d: per-transaction costs set hard ceilings)
 3. among feasible B, choose the one minimising E[T] (sum of stage formulas)
 4. report system capacity at that B and what a surge load would require.
E[N] ~ B when lam*tau >> B (checked: exact moments used for rho)."""
import numpy as np, math
from road_queue import moments, road_kingman
from ordering_stage import formation_exact
from commit_stage import commit_qna
from endorsement_check import formula as end_formula
from scipy.optimize import brentq
def stage_rhos(lam,B,mu,c,q,tau,s0,s1,v0,v1,rule='default'):
    EA,EA2,ES,VS,EN=moments(lam,B,tau,s0,s1)
    re=lam*q/(c*mu) if rule=='default' else lam/mu
    return re, lam*(s0/EN+s1), lam*(v0/EN+v1)
def ET(lam,B,mu,c,q,tau,s0,s1,v0,v1,rule='default'):
    return (end_formula(rule,lam,mu,c,q)+formation_exact(lam,B,tau)
            +road_kingman(lam,B,tau,s0,s1)[0]+commit_qna(lam,B,tau,s0,s1,v0,v1)[0])
def plan(lam_d,rho_max,mu,c,q,tau,s0,s1,v0,v1,Bmax=200):
    rows=[]
    for B in range(2,Bmax+1):
        re,ro,rc=stage_rhos(lam_d,B,mu,c,q,tau,s0,s1,v0,v1)
        ok=max(re,ro,rc)<=rho_max
        rows.append((B,re,ro,rc,ok))
    feas=[r for r in rows if r[4]]
    if not feas: return None
    best=min(feas,key=lambda r: ET(lam_d,r[0],mu,c,q,tau,s0,s1,v0,v1))
    return feas[0][0], best
if __name__=='__main__':
    mu,c,q,tau=200,5,3,2.0; s0,s1,v0,v1=0.020,0.001,0.010,0.002
    lam_d,rho_max=200,0.70
    Bmin,best=plan(lam_d,rho_max,mu,c,q,tau,s0,s1,v0,v1)
    B=best[0]
    print(f"Design load {lam_d} TPS, headroom rule rho <= {rho_max}")
    print(f"  smallest feasible block size B_min = {Bmin}; latency-optimal feasible B = {B}")
    print(f"  utilisations at B={B}: endorse {best[1]:.2f}, order {best[2]:.2f}, commit {best[3]:.2f}")
    print(f"  E[T] at design load = {ET(lam_d,B,mu,c,q,tau,s0,s1,v0,v1)*1e3:.1f} ms (formulas, illustrative)")
    for b in [Bmin, Bmin+1, Bmin+2, Bmin+4, Bmin+12]:
        print(f"    B={b:3d}: E[T]={ET(lam_d,b,mu,c,q,tau,s0,s1,v0,v1)*1e3:6.1f} ms  rhos={tuple(round(x,2) for x in stage_rhos(lam_d,b,mu,c,q,tau,s0,s1,v0,v1))}")
    f=lambda l,a0,a1: l*(a0/moments(l,B,tau,s0,s1)[4]+a1)-1
    Lo=brentq(lambda l:f(l,s0,s1),1,1e4); Lc=brentq(lambda l:f(l,v0,v1),1,1e4); Le=c*mu/q
    print(f"  system capacity at B={B}: min(endorse {Le:.0f}, order {Lo:.0f}, commit {Lc:.0f}) = {min(Le,Lo,Lc):.0f} TPS"
          f" -> headroom factor {min(Le,Lo,Lc)/lam_d:.2f}x design load")
    lam_s=500
    print(f"Surge {lam_s} TPS (2.5x design): requirements for stability (rho < 1) at each stage")
    print(f"  endorsement (default): mu_e > {lam_s*q/c:.0f}/s per peer (now {mu})")
    print(f"  ordering: s0/B + s1 < {1/lam_s*1e3:.1f} ms per txn (now at B={B}: {(s0/B+s1)*1e3:.2f} ms)")
    print(f"  commit:   v0/B + v1 < {1/lam_s*1e3:.1f} ms per txn (now at B={B}: {(v0/B+v1)*1e3:.2f} ms); needs v1 < {1/lam_s*1e3:.1f} ms in any case")
