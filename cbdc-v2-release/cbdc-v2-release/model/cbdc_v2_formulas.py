"""
cbdc_v2_formulas.py : closed-form and matrix-analytic expressions of the v2 model (paper Section 4).
Companion to cbdc_v2_core.py (simulation). Every number in the paper's analytical columns comes from here.
  endorsement_time(rule, lam, mu_e, c, q)  Prop. endtime  (default: upper bound; hedged: approximation)
  formation_exact(lam, B, tau)              Prop. formation (exact)
  moments(...), road_kingman(...)           Lemma renewal + Kingman (approximation)
  road_exact(...)                           PH/PH/1 QBD by logarithmic reduction (exact up to PH fit)
  commit_qna(...)                           QNA linking equation + Kingman (approximation)
  end_to_end(...)                           Eq. endtoend (sum of stages)
  stage_rhos(...), capacities(...)          Eq. rhos and stability
"""
import math
import numpy as np
from scipy.stats import poisson
from scipy.optimize import brentq

H = lambda n: sum(1 / k for k in range(1, n + 1))

def endorsement_time(rule,lam,mu,c,q):
    if rule=='default':
        nu=mu-lam*q/c; return H(q)/nu if nu>0 else np.inf
    nu=mu-lam; return (H(c)-H(c-q))/nu if nu>0 else np.inf

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

def ph_fit(mean, scv, kmax=60):
    """Two-moment PH fit (Tijms): scv<1 mixture of Erlang(k-1),Erlang(k) with common rate; scv>=1 balanced H2."""
    if scv >= 1:
        p = 0.5*(1+np.sqrt((scv-1)/(scv+1))); r1, r2 = 2*p/mean, 2*(1-p)/mean
        return np.array([p, 1-p]), np.diag([-r1, -r2])
    k = int(min(max(np.ceil(1/max(scv,1e-9)), 2), kmax))
    if 1/scv > kmax:                                   # cap: use pure Erlang(kmax), slightly more variable
        p = 0.0
    else:
        p = (k*scv - np.sqrt(k*(1+scv) - k*k*scv)) / (1+scv)
    mu = (k - p)/mean
    T = np.diag(-mu*np.ones(k)) + np.diag(mu*np.ones(k-1), 1)
    alpha = np.zeros(k); alpha[0] = 1.0
    # with prob p exit after k-1 phases: route phase k-2 -> exit with prob p
    T[k-2, k-1] = mu*(1-p)
    return alpha, T

def qbd_ph_ph_1(aA, TA, aS, TS, tol=1e-13, itmax=60):
    nA, nS = len(aA), len(aS); IA, IS = np.eye(nA), np.eye(nS)
    tA = -TA @ np.ones(nA); tS = -TS @ np.ones(nS)
    A0 = np.kron(np.outer(tA, aA), IS)                 # arrival: level up, restart arrival PH
    A1 = np.kron(TA, IS) + np.kron(IA, TS)             # local
    A2 = np.kron(IA, np.outer(tS, aS))                 # service completion: level down, restart service PH
    n = nA*nS; I = np.eye(n)
    H = np.linalg.solve(-A1, A0); L = np.linalg.solve(-A1, A2); G = L.copy(); Tm = H.copy()
    for _ in range(itmax):
        U = H@L + L@H; M = H@H; H = np.linalg.solve(I-U, M); M = L@L; L = np.linalg.solve(I-U, M)
        G = G + Tm@L; Tm = Tm@H
        if np.max(np.abs(1 - G.sum(1))) < tol: break
    R = A0 @ np.linalg.inv(-A1 - A0@G)
    # boundary: level 0 phases = arrival phase only
    B00 = TA; B01 = np.kron(np.outer(tA, aA), aS[None, :])   # arrival into empty: start service
    B10 = np.kron(IA, tS[:, None])                            # last block leaves: to level 0
    # solve [pi0, pi1] [[B00, B01],[B10, A1 + R A2]] = 0 with normalisation
    M = np.block([[B00, B01], [B10, A1 + R@A2]])
    IR = np.linalg.inv(np.eye(n) - R)
    norm = np.concatenate([np.ones(nA), IR@np.ones(n)])
    Mfull = np.hstack([M, norm[:, None]])
    rhs = np.zeros(M.shape[1] + 1); rhs[-1] = 1
    x = np.linalg.lstsq(Mfull.T, rhs, rcond=None)[0]
    pi0, pi1 = x[:nA], x[nA:]
    Lq_blocks = pi1 @ IR @ IR @ np.ones(n)             # mean number of blocks at the road
    return Lq_blocks

def road_exact(lam, B, tau, s0, s1):
    EA, EA2, ES, VS, EN = moments(lam, B, tau, s0, s1)
    ca2 = (EA2-EA**2)/EA**2; cs2 = VS/ES**2
    aA, TA = ph_fit(EA, ca2); aS, TS = ph_fit(ES, cs2)
    Lb = qbd_ph_ph_1(aA, TA, aS, TS)
    return Lb*EA, ca2, cs2, len(aA), len(aS)            # Little: W = L / (1/EA)

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

def end_to_end(lam, B, tau, mu_e, c, q, s0, s1, v0, v1, rule="default"):
    """Eq. (endtoend): E[T] = E[T_e] + E[W_f] + E[W_o] + E[W_c] (seconds)."""
    return (endorsement_time(rule, lam, mu_e, c, q) + formation_exact(lam, B, tau)
            + road_kingman(lam, B, tau, s0, s1)[0] + commit_qna(lam, B, tau, s0, s1, v0, v1)[0])


def stage_rhos(lam, B, tau, mu_e, c, q, s0, s1, v0, v1, rule="default"):
    EN = moments(lam, B, tau, s0, s1)[4]
    re = lam * q / (c * mu_e) if rule == "default" else lam / mu_e
    return re, lam * (s0 / EN + s1), lam * (v0 / EN + v1)


def capacities(B, tau, mu_e, c, q, s0, s1, v0, v1, rule="default"):
    Le = c * mu_e / q if rule == "default" else mu_e
    f = lambda l, a0, a1: l * (a0 / moments(l, B, tau, s0, s1)[4] + a1) - 1
    Lo = brentq(lambda l: f(l, s0, s1), 1e-3, 1e5); Lc = brentq(lambda l: f(l, v0, v1), 1e-3, 1e5)
    return dict(endorse=Le, order=Lo, commit=Lc, system=min(Le, Lo, Lc))


def surge_fluid(lam_d, lam_s, dur, cap):
    """Fluid (bathtub) approximation of a surge above capacity: backlog Q = (lam_s - cap) * dur
    at the end of the surge, extra delay of the last surge arrival ~ Q / cap, and recovery time
    R = Q / (cap - lam_d) after the surge. Valid when lam_s > cap > lam_d."""
    if lam_s <= cap:
        return dict(backlog=0.0, peak_extra_delay=0.0, recovery=0.0)
    Q = (lam_s - cap) * dur
    return dict(backlog=Q, peak_extra_delay=Q / cap, recovery=Q / (cap - lam_d) if cap > lam_d else float('inf'))
