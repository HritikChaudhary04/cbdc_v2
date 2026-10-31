"""Section 4.7 with MEASURED parameters (decision 2026-10-30): Poisson, mild (175/300), strong (150/400), stress (50/800),
bursts 20% of time, mean length 30 s; mu_e=436, c=5, q=3, B=100; ordering and commit service Erlang-5 in the analysis
(k=30 replication phases in the simulation). Usage: python3 map_measured.py analysis | sim"""
import json, os, sys, time, numpy as np
from cbdc_v2_map import *
from cbdc_v2_params import PIPE
P = PIPE; mu = P['mu_e']; c, q, B = 5, 3, 100; RNB, RBN = 1/120, 1/30
CASES = {'poisson': None, 'mild': (175, 300), 'strong': (150, 400), 'stress': (50, 800)}
def maps(case):
    return poisson_map(200.0) if CASES[case] is None else mmpp2(*CASES[case], RNB, RBN)
out = 'res_map_measured.json'; R = json.load(open(out)) if os.path.exists(out) else {}
mode = sys.argv[1]
if mode == 'analysis':
    for case in CASES:
        if case in R.get('analysis', {}): continue
        D0, D1 = maps(case); t = time.time()
        Dp0, Dp1 = thin(D0, D1, q / c); w, F, peer = map_m1_sojourn(Dp0, Dp1, mu)
        endo, _, _ = endorsement_time_map(D0, D1, mu, c, q)
        form = formation_wait_map(D0, D1, B)
        C0, C1 = block_map(D0, D1, B)
        b, S = erlang_ph(P['s0'] + P['s1'] * B, 5); Lr, Wr = road_map_ph1(C0, C1, b, S)
        b2, S2 = erlang_ph(P['v0'] + P['v1'] * B, 5); Lc, Wc = road_map_ph1(C0, C1, b2, S2)
        fl = burst_fluid_mean_delay(*CASES[case], RNB, RBN, 727.0) if CASES[case] else 0.0
        R.setdefault('analysis', {})[case] = dict(peer=peer, endorse=endo, formation=form, road=Wr, commit=Wc, fluid=fl, secs=time.time() - t)
        json.dump(R, open(out, 'w'), indent=1)
        print(case, {k: round(1000 * v, 2) for k, v in R['analysis'][case].items() if k != 'secs'}, round(time.time() - t, 1), 's', flush=True)
else:
    from map_chain_sim import chain_mmpp
    T0 = time.time(); plan = {'poisson': (4, 4000.0), 'mild': (4, 4000.0), 'strong': (4, 4000.0), 'stress': (8, 20000.0)}
    for case, (nrep, T) in plan.items():
        for i in range(nrep):
            key = f'{case}_{i}'
            if key in R.get('sim', {}) or time.time() - T0 > 200: continue
            rates = (200.0, 200.0) if CASES[case] is None else CASES[case]
            r = chain_mmpp(rates, (RNB, RBN), T, 300.0, mu=mu, c=c, q=q, B=B, tau=P['tau'], s0=P['s0'], s1=P['s1'],
                           v0=P['v0'], v1=P['v1'], k=30, seed=i)
            R.setdefault('sim', {})[key] = r; json.dump(R, open(out, 'w'), indent=1)
            print(key, {k: round(1000 * v, 1) for k, v in r.items()}, flush=True)
