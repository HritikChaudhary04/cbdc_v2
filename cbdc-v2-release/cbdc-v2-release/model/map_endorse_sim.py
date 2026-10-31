"""Direct simulation of the endorsement stage (per-peer FCFS M/M/1 servers, default rule) under MMPP arrivals,
for checking the matrix-analytic results. Same Lindley approach as endorsement_check.py."""
import numpy as np
def mmpp_arrivals(lam_rates, r_switch, T, rng):
    """lam_rates = (normal, burst); r_switch = (r_nb, r_bn); returns arrival times on [0, T]."""
    t, ph, out = 0.0, 0, []
    while t < T:
        lam = lam_rates[ph]; r = r_switch[ph]
        dt = rng.exponential(1 / (lam + r)); t += dt
        if rng.random() < lam / (lam + r): out.append(t)
        else: ph = 1 - ph
    return np.array(out)
def endorse_sim(lam_rates, r_switch, mu, c, q, T=3000.0, warm=300.0, seed=0, rule='default'):
    rng = np.random.default_rng(seed); arr = mmpp_arrivals(lam_rates, r_switch, T, rng)
    free = np.zeros(c); te = np.empty(len(arr)); peer_soj = []
    for i, a in enumerate(arr):
        peers = rng.choice(c, q, replace=False) if rule == 'default' else np.arange(c)
        done = np.maximum(free[peers], a) + rng.exponential(1 / mu, len(peers)); free[peers] = done
        if a > warm: peer_soj.extend(done - a)
        te[i] = done.max() if rule == 'default' else np.partition(done, q - 1)[q - 1]
    keep = arr > warm
    return (te - arr)[keep].mean(), np.mean(peer_soj)
