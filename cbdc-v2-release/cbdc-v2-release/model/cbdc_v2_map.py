"""
cbdc_v2_map.py : matrix-analytic analysis of bursty (MAP) traffic for the v2 CBDC model.
Every step mirrors the derivation in the paper (Section 4.7, bursty traffic).

Notation: a MAP is (D0, D1); theta is the stationary vector of D = D0 + D1; lam = theta D1 1.
"""
import numpy as np
from scipy.stats import gamma as gamma_dist
from scipy.integrate import quad


# ---------------------------------------------------------------- MAP basics
def mmpp2(lam_n, lam_b, r_nb, r_bn):
    """Two-phase MMPP: phase 0 = normal, phase 1 = burst."""
    D1 = np.diag([lam_n, lam_b])
    D0 = np.array([[-(lam_n + r_nb), r_nb], [r_bn, -(lam_b + r_bn)]])
    return D0, D1

def poisson_map(lam):
    return np.array([[-lam]]), np.array([[lam]])

def stationary(Q):
    """theta Q = 0, theta 1 = 1 for an irreducible generator Q."""
    n = Q.shape[0]; A = np.vstack([Q.T, np.ones(n)]); b = np.zeros(n + 1); b[-1] = 1
    return np.linalg.lstsq(A, b, rcond=None)[0]

def map_rate(D0, D1):
    th = stationary(D0 + D1); return float(th @ D1 @ np.ones(len(th)))

def thin(D0, D1, p):
    """Step 1: each arrival kept with probability p -> MAP (D0 + (1-p) D1, p D1)."""
    return D0 + (1 - p) * D1, p * D1

def map_scv_idc(D0, D1, horizon=None):
    """Interarrival SCV and asymptotic index of dispersion of counts (burstiness measures)."""
    n = len(D0); one = np.ones(n); th = stationary(D0 + D1); lam = th @ D1 @ one
    pi_a = th @ D1 / lam                                  # phase just after an arrival
    M = np.linalg.inv(-D0)
    m1 = pi_a @ M @ one; m2 = 2 * pi_a @ M @ M @ one
    scv = m2 / m1**2 - 1
    D = D0 + D1; Pi = np.outer(one, th)
    Z = np.linalg.inv(Pi - D)                             # deviation matrix + Pi
    idc = 1 + 2 * (th @ D1 @ (Z - Pi) @ D1 @ one) / lam  # asymptotic IDC
    return float(scv), float(idc)


# ---------------------------------------------------------------- QBD solver
def log_reduction_G(A0, A1, A2, tol=1e-14, itmax=80):
    """Latouche-Ramaswami logarithmic reduction for G (A2 + A1 G + A0 G^2 = 0); A0 up, A2 down."""
    n = A1.shape[0]; I = np.eye(n)
    H = np.linalg.solve(-A1, A0); L = np.linalg.solve(-A1, A2); G = L.copy(); T = H.copy()
    for _ in range(itmax):
        U = H @ L + L @ H; Hn = np.linalg.solve(I - U, H @ H); Ln = np.linalg.solve(I - U, L @ L)
        G = G + T @ Ln; T = T @ Hn; H, L = Hn, Ln
        if np.max(np.abs(1 - G.sum(1))) < tol: break
        # guard (2026-10-30): with large, lightly loaded QBDs the residual can stall near 1e-13 while H, L
        # underflow and T overflows; stop once the remaining correction is negligible
        if not np.isfinite(T).all() or np.max(np.abs(T @ np.ones(n))) < 1e-16: break
    return G

def solve_qbd(B00, B01, B10, A0, A1, A2):
    """Step 3: R = A0(-A1 - A0 G)^-1; boundary (pi0, pi1); returns pi0, pi1, R.
    Level 0 has its own phase space (size of B00); levels >= 1 use A0, A1, A2."""
    G = log_reduction_G(A0, A1, A2)
    R = A0 @ np.linalg.inv(-A1 - A0 @ G)
    n0, n = B00.shape[0], A1.shape[0]
    M = np.block([[B00, B01], [B10, A1 + R @ A2]])
    IR = np.linalg.inv(np.eye(n) - R)
    norm = np.concatenate([np.ones(n0), IR @ np.ones(n)])
    Mf = np.hstack([M, norm[:, None]]); rhs = np.zeros(M.shape[1] + 1); rhs[-1] = 1
    x = np.linalg.lstsq(Mf.T, rhs, rcond=None)[0]
    return x[:n0], x[n0:], R


# ---------------------------------------------------------------- MAP/M/1 peer
def map_m1(D0, D1, mu):
    """Step 2: MAP/M/1 as a QBD. Level n = proposals at the peer, phase = MAP phase.
    A0 = D1 (arrival), A1 = D0 - mu I (phase change), A2 = mu I (service); B00 = D0, B01 = D1, B10 = mu I."""
    m = len(D0); I = np.eye(m)
    return solve_qbd(D0, D1, mu * I, D1, D0 - mu * I, mu * I)

def map_m1_sojourn(D0, D1, mu):
    """Step 4 (exact, no truncation): FCFS sojourn-time distribution in MAP/M/1 by arrival phase.
    With pi_n = pi_1 R^(n-1) and Sum_n R^n P(Erl(n+1,mu) > t) = expm(-mu (I-R) t) (I-R)^-1,
      P(S > t, phase j) = (1/lam)[ (pi0 D1)_j e^{-mu t} + (pi1 M(t) D1)_j ],
      M(t) = expm(-mu(I-R)t)(I-R)^-1 + e^{-mu t} Int_0^{mu t} expm(R x) dx   (Van Loan block form).
    Returns (w, F, mean): w_j = P(arrival in phase j); F(t) = vector of P(S <= t | phase j); exact mean."""
    from scipy.linalg import expm
    pi0, pi1, R = map_m1(D0, D1, mu)
    m = len(D0); I = np.eye(m); one = np.ones(m); lam = map_rate(D0, D1)
    IR = np.linalg.inv(I - R)
    w = (pi0 @ D1 + pi1 @ IR @ D1) / lam
    # e^{-y} Int_0^y e^{R x} dx = R^-1 (e^{-(I-R) y} - e^{-y} I), y = mu t (R invertible because D1 is;
    # every eigenvalue of R lies in (0, 1), so both terms decay and nothing overflows).
    Rinv = np.linalg.inv(R)
    def surv(t):
        E = expm(-mu * (I - R) * t)
        M = E @ IR + Rinv @ (E - np.exp(-mu * t) * I)
        return ((pi0 @ D1) * np.exp(-mu * t) + pi1 @ M @ D1) / lam
    def F(t):
        return 1 - surv(t) / w
    # exact mean: E[S] = (1/lam)[pi0 D1 1 / mu + pi1 Sum_{n>=1} R^(n-1) (n+1)/mu D1 1]
    #           Sum_{n>=1} R^(n-1)(n+1) = (I-R)^-2 + (I-R)^-1
    mean = float((pi0 @ D1 @ one / mu + pi1 @ (IR @ IR + IR) @ D1 @ one / mu) / lam)
    return w, F, mean

def endorsement_time_map(D0, D1, mu_e, c, q, rule="default", tmax=None):
    """Step 5: phase-conditioned approximation of the endorsement time.
    default: each peer sees MAP thinned with p = q/c; slowest of q.  hedged: p = 1; q-th of c."""
    p = q / c if rule == "default" else 1.0
    Dp0, Dp1 = thin(D0, D1, p)
    w, F, mean_peer = map_m1_sojourn(Dp0, Dp1, mu_e)
    tmax = tmax or 200 * mean_peer
    from math import comb
    def surv(t):
        Fj = F(t)
        if rule == "default":
            return 1 - Fj ** q                               # max of q i.i.d. given phase
        # q-th smallest of c: P(T > t) = P(fewer than q of c done by t)
        return sum(comb(c, i) * Fj**i * (1 - Fj)**(c - i) for i in range(q))
    # integrate survival per phase
    ts = np.concatenate([np.linspace(0, 10 * mean_peer, 4000), np.linspace(10 * mean_peer, tmax, 4000)[1:]])
    S = np.array([surv(t) for t in ts])                     # shape (len(ts), m), conditional on phase
    Ej = np.trapezoid(S, ts, axis=0)
    return float(w @ Ej), mean_peer, w


# ---------------------------------------------------------------- Part 2: blocks and the ordering road
def block_map(D0, D1, B):
    """Step 6: block arrivals under the size rule as a MAP on phases (k, j), k = txns already in the open block.
    C0 = I_B (x) D0 + S_B (x) D1 ; C1 = (e_{B-1} e_0^T) (x) D1."""
    IB = np.eye(B); SB = np.eye(B, k=1); E = np.zeros((B, B)); E[B - 1, 0] = 1.0
    return np.kron(IB, D0) + np.kron(SB, D1), np.kron(E, D1)

def formation_wait_map(D0, D1, B):
    """Step 7: exact mean formation wait under the size rule.
    M = (-D0)^-1, P = M D1, pi_a = theta D1 / lam; E[W_f] = (1/B) Sum_{i=1}^B pi_a Sum_{s=0}^{B-i-1} P^s M 1."""
    m = len(D0); one = np.ones(m); th = stationary(D0 + D1); lam = th @ D1 @ one
    pi_a = th @ D1 / lam; M = np.linalg.inv(-D0); P = M @ D1; Mone = M @ one
    terms = []; v = pi_a.copy()                         # v = pi_a P^s
    for s in range(B - 1):
        terms.append(v @ Mone); v = v @ P
    cum = np.cumsum(terms)                              # cum[r-1] = expected time for r more arrivals
    return float(sum(cum[B - i - 1] for i in range(1, B)) / B)

def erlang_ph(mean, k):
    beta = np.zeros(k); beta[0] = 1.0; r = k / mean
    S = np.diag(-r * np.ones(k)) + np.diag(r * np.ones(k - 1), 1)
    return beta, S

def road_map_ph1(C0, C1, beta, S):
    """Step 8: MAP/PH/1 road. Level = blocks at the road; phase = (block-MAP phase, service phase).
    A0 = C1 (x) I, A1 = C0 (x) I + I (x) S, A2 = I (x) (s beta); B00 = C0, B01 = C1 (x) beta, B10 = I (x) s.
    Returns mean number of blocks L and mean block sojourn W = L / lam_b."""
    na, k = len(C0), len(beta); Ia, Ik = np.eye(na), np.eye(k); s = -S @ np.ones(k)
    A0 = np.kron(C1, Ik); A1 = np.kron(C0, Ik) + np.kron(Ia, S); A2 = np.kron(Ia, np.outer(s, beta))
    B00 = C0; B01 = np.kron(C1, beta[None, :]); B10 = np.kron(Ia, s[:, None])
    pi0, pi1, R = solve_qbd(B00, B01, B10, A0, A1, A2)
    IR = np.linalg.inv(np.eye(len(A1)) - R)
    L = float(pi1 @ IR @ IR @ np.ones(len(A1)))
    lam_b = map_rate(C0, C1)
    return L, L / lam_b


def burst_fluid_mean_delay(lam_n, lam_b, r_nb, r_bn, cap):
    """Bottleneck fluid approximation for an MMPP(2) whose burst rate exceeds the system capacity:
    backlog grows at (lam_b - cap) during a burst of length D ~ Exp(r_bn), then drains at (cap - lam_n),
    assumed complete before the next burst. Area of backlog per burst = (a/2) D^2 (1 + a/d), a = lam_b - cap,
    d = cap - lam_n; E[D^2] = 2 / r_bn^2. Mean extra delay = mean backlog / mean rate (Little)."""
    a, d = lam_b - cap, cap - lam_n
    if a <= 0: return 0.0
    area = 0.5 * a * (2 / r_bn**2) * (1 + a / d)
    cycle = 1 / r_bn + 1 / r_nb
    lam = (lam_n / r_nb + lam_b / r_bn) / cycle
    return area / cycle / lam


# ---------------------------------------------------------------- Part 3: phase-type service (MAP/PH/1 peer)
def ph_service(mean, scv):
    """Step 10: service PH(beta, S) with given mean and SCV: exponential (1), Erlang-2 (0.5), balanced H2 (>1)."""
    if abs(scv - 1) < 1e-12:
        return np.array([1.0]), np.array([[-1 / mean]])
    if abs(scv - 0.5) < 1e-12:
        r = 2 / mean; return np.array([1.0, 0.0]), np.array([[-r, r], [0, -r]])
    p = 0.5 * (1 + np.sqrt((scv - 1) / (scv + 1))); r1, r2 = 2 * p / mean, 2 * (1 - p) / mean
    return np.array([p, 1 - p]), np.diag([-r1, -r2])

def map_ph1(D0, D1, beta, S):
    """Step 11: MAP/PH/1 peer as a QBD; phase = (arrival phase, service phase)."""
    m, k = len(D0), len(beta); Im, Ik = np.eye(m), np.eye(k); s = -S @ np.ones(k)
    A0 = np.kron(D1, Ik); A1 = np.kron(D0, Ik) + np.kron(Im, S); A2 = np.kron(Im, np.outer(s, beta))
    return solve_qbd(D0, np.kron(D1, beta[None, :]), np.kron(Im, s[:, None]), A0, A1, A2)

def map_ph1_sojourn_lst(D0, D1, beta, S):
    """Step 12: exact sojourn LST by arrival phase, closed form via Sum_{n>=1} R^(n-1) phi^n = phi (I - phi R)^-1.
    Returns (w, lst) with lst(theta) -> vector over arrival phases j of E[e^{-theta S}; J=j] / w_j, and exact mean."""
    pi0, pi1, R = map_ph1(D0, D1, beta, S)
    m, k = len(D0), len(beta); s = -S @ np.ones(k); lam = map_rate(D0, D1)
    D1k = np.kron(D1, np.eye(k)); IR = np.linalg.inv(np.eye(m * k) - R)
    a0 = pi0 @ D1 / lam                                        # arrivals finding an empty peer, by phase j
    w = a0 + (pi1 @ IR @ D1k / lam).reshape(m, k).sum(1)
    def lst(theta):
        Rs = np.linalg.solve(theta * np.eye(k) - S, s)          # residual LSTs r_u(theta)
        phi = beta @ Rs                                         # full service LST
        X = pi1 @ (phi * np.linalg.inv(np.eye(m * k) - phi * R)) @ D1k / lam
        return (a0 * phi + X.reshape(m, k) @ Rs) / w
    # exact mean sojourn: E[residual_u] + n E[X] summed with the geometric weights
    EX = -beta @ np.linalg.solve(S, np.ones(k)); Eres = -np.linalg.solve(S, np.ones(k))
    Y1 = (pi1 @ IR @ D1k / lam).reshape(m, k); Y2 = (pi1 @ IR @ IR @ D1k / lam).reshape(m, k)
    mean = float(a0.sum() * EX + (Y1 @ Eres).sum() + EX * Y2.sum())   # level n>=1: residual + n services
    return w, lst, mean

def euler_cdf(lst, t, A=18.4, n=15, mterms=11):
    """Step 13: Abate-Whitt Euler inversion of F(t) from the LST (transform of F is lst(s)/s); error ~ e^-A.
    lst returns a vector (one entry per arrival phase)."""
    from math import comb, pi as PI
    X = A / (2 * t); H = PI / t
    f = lambda z: lst(z) / z
    terms = [0.5 * np.real(f(X))] + [(-1) ** k * np.real(f(X + 1j * k * H)) for k in range(1, n + mterms + 1)]
    partial = np.cumsum(terms, axis=0) * np.exp(A / 2) / t
    return sum(comb(mterms, j) * partial[n + j] for j in range(mterms + 1)) / 2 ** mterms

def endorsement_time_map_ph(D0, D1, mu_e, scv, c, q, rule="default", npts=1500):
    """Endorsement bracket with PH service: lower bound E[S]; phase-conditioned value via inverted CDF."""
    p = q / c if rule == "default" else 1.0
    beta, S = ph_service(1 / mu_e, scv)
    w, lst, mean = map_ph1_sojourn_lst(*thin(D0, D1, p), beta, S)
    ts = np.concatenate([np.linspace(1e-6, 8 * mean, npts), np.linspace(8 * mean, 60 * mean, npts)[1:]])
    F = np.clip(np.array([euler_cdf(lst, t) for t in ts]), 0, 1)
    if rule == "default":
        surv = 1 - F ** q
    else:
        from math import comb
        surv = sum(comb(c, i) * F**i * (1 - F)**(c - i) for i in range(q))
    Ej = np.trapezoid(np.vstack([np.ones(len(w)), surv]), np.concatenate([[0], ts]), axis=0)
    return float(w @ Ej), mean, w
