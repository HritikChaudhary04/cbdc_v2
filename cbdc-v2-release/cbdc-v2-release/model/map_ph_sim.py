"""Simulation check for Step 10-13: endorsement stage with MMPP (or Poisson) arrivals and PH service
(Erlang-2, exponential, balanced H2), default dispatch c=5, q=3."""
import numpy as np, json, os
from map_endorse_sim import mmpp_arrivals
def draw_service(rng, mean, scv, size):
    if abs(scv - 1) < 1e-12: return rng.exponential(mean, size)
    if abs(scv - 0.5) < 1e-12: return rng.gamma(2, mean / 2, size)
    p = 0.5 * (1 + np.sqrt((scv - 1) / (scv + 1))); u = rng.random(size)
    return np.where(u < p, rng.exponential(mean / (2 * p), size), rng.exponential(mean / (2 * (1 - p)), size))
def run(lr, scv, T=4000.0, warm=300.0, mu=200.0, c=5, q=3, seed=0):
    rng = np.random.default_rng(seed); arr = mmpp_arrivals(lr, (1/120, 1/30), T, rng)
    free = np.zeros(c); te = np.empty(len(arr)); soj = []
    for i, a in enumerate(arr):
        peers = rng.choice(c, q, replace=False)
        done = np.maximum(free[peers], a) + draw_service(rng, 1 / mu, scv, q); free[peers] = done
        te[i] = done.max()
        if a > warm: soj.extend(done - a)
    k = arr > warm
    return float((te - arr)[k].mean()), float(np.mean(soj))
if __name__ == '__main__':
    out = 'res_mapph.json'; R = json.load(open(out)) if os.path.exists(out) else {}
    for name, lr in [('poisson', (200, 200)), ('mild', (175, 300))]:
        for scv in [0.5, 1.0, 2.0]:
            key = f'{name}_{scv}'; R.setdefault(key, {})
            for s in range(4):
                if str(s) in R[key]: continue
                R[key][str(s)] = run(lr, scv, seed=s); json.dump(R, open(out, 'w'), indent=1); print(key, s, flush=True)
    print('ALL DONE', flush=True)
