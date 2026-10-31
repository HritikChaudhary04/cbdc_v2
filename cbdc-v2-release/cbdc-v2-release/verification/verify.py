"""Analytical calculator for the CBDC paper. Run: python verify.py [--lam 200 --mv 150 --c 5 --mc 200 --ml 300 --q 3]
Prints the v1 Eq.(3) value, the corrected tandem value (consensus as M/G/1 with
hypoexponential service, commit as M/M/1), the validator-count curve, and checks
against numbers quoted by reviewers. Extend, do not replace, as the model changes."""
import math, argparse

def mmc(lam, mu, c):
    """M/M/c: returns (Wq, W, Lq) in seconds; inf if unstable."""
    a = lam / mu; r = a / c
    if r >= 1: return math.inf, math.inf, math.inf
    p0 = 1 / (sum(a**n / math.factorial(n) for n in range(c)) + a**c / math.factorial(c) / (1 - r))
    Lq = a**c * r * p0 / (math.factorial(c) * (1 - r)**2)
    return Lq / lam, Lq / lam + 1 / mu, Lq

def quorum_mean(c, q, mc):
    """Theorem 1 / Renyi: E[q-th order statistic of c iid Exp(mc)]."""
    return sum(1 / ((c - i) * mc) for i in range(q))

def quorum_var(c, q, mc):
    return sum(1 / ((c - i) * mc)**2 for i in range(q))

def mg1_W(lam, ES, ES2):
    rho = lam * ES
    if rho >= 1: return math.inf, math.inf, rho
    Wq = lam * ES2 / (2 * (1 - rho)); return Wq, Wq + ES, rho

def majority(c): return math.ceil((c + 1) / 2)

def report(lam, mv, c, mc, ml, q):
    ms = 1e3
    Wq1, W1, _ = mmc(lam, mv, c)
    ES, V = quorum_mean(c, q, mc), quorum_var(c, q, mc)
    Wq2, W2, rho2 = mg1_W(lam, ES, V + ES**2)
    W3 = 1 / (ml - lam) if lam < ml else math.inf
    v1 = W1 + ES + 1 / ml
    tot = W1 + W2 + W3
    print(f"Params lam={lam} mv={mv} c={c} mc={mc} ml={ml} q={q}")
    print(f"v1 Eq.(3) total            : {v1*ms:.3f} ms")
    print(f"Stage1 M/M/{c} W           : {W1*ms:.3f} ms (Wq {Wq1*ms:.4f})")
    print(f"Consensus M/G/1 rho, Wq, W : {rho2:.3f}, {Wq2*ms:.2f}, {W2*ms:.2f} ms  (capacity {1/ES:.1f} TPS)")
    print(f"Commit M/M/1 W             : {W3*ms:.2f} ms")
    if math.isfinite(tot):
        q_share = (Wq1 + Wq2 + (W3 - 1/ml)) / tot
        print(f"Corrected tandem total     : {tot*ms:.2f} ms, queueing share {q_share*100:.1f}%")
    else:
        print("Corrected tandem total     : UNSTABLE")
    print("\nValidator curve (majority quorum), consensus mean and v1 total:")
    for cc in range(3, 12):
        qq = majority(cc)
        print(f"  c={cc:2d} q={qq}: {quorum_mean(cc,qq,mc)*ms:.3f} ms, v1 total {(mmc(lam,mv,cc)[1]+quorum_mean(cc,qq,mc)+1/ml)*ms:.3f}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for k, v in dict(lam=200, mv=150, c=5, mc=200, ml=300, q=3).items():
        p.add_argument(f"--{k}", type=float if k in ("lam","mv","mc","ml") else int, default=v)
    a = p.parse_args(); report(a.lam, a.mv, a.c, a.mc, a.ml, a.q)
    print("\nReviewer cross-checks:")
    print(f"  failure c=3,q=3 v1: {(mmc(a.lam,a.mv,3)[1]+quorum_mean(3,3,a.mc)+1/a.ml)*1e3:.3f} ms")
    print(f"  failure c=3,q=2 v1: {(mmc(a.lam,a.mv,3)[1]+quorum_mean(3,2,a.mc)+1/a.ml)*1e3:.3f} ms (paper reported 14.88)")
    print(f"  parallel M/M/5 @600: {mmc(600,150,5)[1]*1e3:.2f} ms (paper 8.46)")
