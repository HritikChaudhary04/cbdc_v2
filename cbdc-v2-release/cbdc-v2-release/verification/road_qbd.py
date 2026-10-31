"""Exact check of the ordering 'road' queue by matrix-analytic methods.
Interblock time A and block service S are represented by phase-type (PH) distributions matched to
their first two moments (exact when blocks fill by size: A is then Erlang(B, lam)). The road is a
PH/PH/1 queue solved as a QBD: level = blocks at the road, phase = (arrival phase, service phase).
G by logarithmic reduction (Latouche-Ramaswami), R = A0 (-A1 - A0 G)^{-1}."""
import numpy as np
from road_queue import moments, road_kingman
from ordering_stage import simulate

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

def ph_phase_mean(alpha, T): return -alpha @ np.linalg.solve(T, np.ones(len(alpha)))

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

if __name__ == '__main__':
    s0, s1, tau = 0.020, 0.001, 2.0
    print(" lam   B   phases(A x S)   exact QBD   Kingman   simulation   [road time, ms]")
    for lam, B in [(41,2),(120,4),(200,10),(200,20),(300,10),(300,20)]:
        Wex, ca2, cs2, kA, kS = road_exact(lam, B, tau, s0, s1)
        Wk, rho = road_kingman(lam, B, tau, s0, s1)
        sims = [simulate(lam, B, tau, s0, s1, n=100_000, warm=10_000, seed=s)[1] for s in range(5)]
        sm = np.mean(sims); ci = 1.96*np.std(sims, ddof=1)/np.sqrt(5)
        print(f"{lam:4d} {B:3d}   {kA:3d} x {kS:3d}      {Wex*1e3:8.2f}   {Wk*1e3:7.2f}   {sm*1e3:7.2f} ± {ci*1e3:.2f}")
