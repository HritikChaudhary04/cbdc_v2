"""Fast full-chain simulation (endorse -> formation -> road -> commit) with MMPP arrivals, for checking the
matrix-analytic results of Section 4.7. Same structure as full_chain.py; arrivals from map_endorse_sim.mmpp_arrivals.
Replication time Erlang-30 with mean s0 + s1*N (as in the MAP/PH/1 model); commit time v0 + v1*N."""
import numpy as np, json, os, sys
from map_endorse_sim import mmpp_arrivals
def chain_mmpp(lam_rates, r_switch, T, warm, mu=200.0, c=5, q=3, B=9, tau=2.0, s0=.02, s1=.001, v0=.01, v1=.002, k=30, seed=0):
    rng = np.random.default_rng(seed); arr = mmpp_arrivals(lam_rates, r_switch, T, rng); n = len(arr)
    free = np.zeros(c); te = np.empty(n)
    for i, a in enumerate(arr):
        peers = rng.choice(c, q, replace=False)
        done = np.maximum(free[peers], a) + rng.exponential(1 / mu, q); free[peers] = done; te[i] = done.max()
    order = np.argsort(te); tin = te[order]; road = peer = 0.0
    form = np.empty(n); rd = np.empty(n); cm = np.empty(n); i = 0
    while i < n:
        start = tin[i]; j = i
        while j + 1 < n and j + 1 - i < B and tin[j + 1] < start + tau: j += 1
        N = j - i + 1; cut = tin[j] if N == B else start + tau
        S = rng.gamma(k, (s0 + s1 * N) / k)
        road = max(road, cut) + S; peer = max(peer, road) + v0 + v1 * N
        idx = order[i:j + 1]; form[idx] = cut - te[idx]; rd[idx] = road - cut; cm[idx] = peer - road; i = j + 1
    keep = (arr > warm) & (arr < T - 200)
    return dict(endorse=float((te - arr)[keep].mean()), formation=float(form[keep].mean()), road=float(rd[keep].mean()),
                commit=float(cm[keep].mean()), total=float((te - arr + form + rd + cm)[keep].mean()))
if __name__ == '__main__':
    out = 'res_mapchain.json'; R = json.load(open(out)) if os.path.exists(out) else {}
    for name, lr, T, reps in [('poisson', (200, 200), 4000.0, 4), ('mild', (175, 300), 4000.0, 4), ('strong', (150, 400), 20000.0, 8)]:
        R.setdefault(name, {})
        for s in range(reps):
            if str(s) in R[name]: continue
            R[name][str(s)] = chain_mmpp(lr, (1/120, 1/30), T, 300.0, seed=s)
            json.dump(R, open(out, 'w'), indent=1); print(name, s, flush=True)
    print('ALL DONE', flush=True)
