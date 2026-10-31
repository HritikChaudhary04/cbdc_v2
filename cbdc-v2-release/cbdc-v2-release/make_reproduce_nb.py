"""Builds cbdc-v2-release/reproduce_paper.ipynb: loads the saved results and rebuilds the paper's main tables and
figures (no long simulations). Run from the release root."""
import nbformat as nbf
nb = nbf.v4.new_notebook(); C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s)); code = lambda s: C.append(nbf.v4.new_code_cell(s))

md("""# Reproducing the paper's tables and figures
*Confirmation time in a permissioned retail CBDC: a queueing model validated on a Hyperledger Fabric testbed*

This notebook reads the saved results in `model/` and `results/` and rebuilds the main tables and all figures in about a
minute. It does not rerun the long simulations or the testbed; the runners that produced the saved files are listed in
`README.md`. All service parameters are those measured on the testbed.""")
code("""import sys, json, csv, re, subprocess, numpy as np, pandas as pd
from IPython.display import Image, display
sys.path.insert(0, 'model')
from cbdc_v2_params import PIPE, B_CHOSEN, LAM_DESIGN
from cbdc_v2_formulas import end_to_end, stage_rhos, capacities
pd.set_option('display.precision', 2); pd.set_option('display.width', 160)
J = lambda f: json.load(open('model/' + f))
stats = pd.read_csv('results/campaign_stats.csv'); rounds = pd.read_csv('results/campaign_rounds.csv')
print('Measured parameters:', PIPE); print('Chosen block size:', B_CHOSEN, '| design load:', LAM_DESIGN, 'TPS')""")

md("## Section 4.6: capacity and the model's operating point at 200 TPS")
code("""rows = []
for B in [4, 5, 10, 20, 50, 100]:
    r = stage_rhos(200, B, **PIPE); cap = capacities(B, **PIPE)
    rows.append(dict(B=B, rho_endorse=float(r[0]), rho_order=float(r[1]), rho_commit=float(r[2]),
                     model_ms=1000 * end_to_end(200, B, **PIPE), system_capacity=cap['system']))
pd.DataFrame(rows)""")
md("The model alone picks the smallest feasible block size (B = 5, about 45 ms); the testbed rejected small blocks near the design load, and B = 100 is the confirmed choice (Sections 4.6 and 6.2).")

md("## Section 5.3: model against measurement (testbed)")
code("""print(open('results/stage_parameters.txt').read())
print(open('results/model_vs_measured.txt').read())""")

md("## Section 6.1: equal-capacity comparison (30 replications)")
code("""R = J('res09_measured.json'); out = []
for d in ['centralised', 'parallel', 'priority', 'fabric']:
    v = R[d]; n = len(v)
    a = {k: 1000 * np.array([v[str(i)][k] for i in range(n)]) for k in ['mean', 'p95', 'p99']}
    out.append({'design': d, **{k: f"{x.mean():.2f} ± {2.045 * x.std(ddof=1) / np.sqrt(n):.2f}" for k, x in a.items()}})
pd.DataFrame(out)""")

md("## Section 6.2: block size, formula against simulation")
code("""R = J('res04_measured.json'); out = []
for k, v in R.items():
    lam, B = map(int, k.split('_'))
    if v['skipped']: out.append(dict(lam=lam, B=B, note='saturated')); continue
    f, s = v['formula'], v['sim']
    out.append(dict(lam=lam, B=B, total_formula_ms=1000 * f['total'], total_sim_ms=1000 * s['mean'][0],
                    error_pct=100 * (f['total'] - s['mean'][0]) / s['mean'][0]))
pd.DataFrame(out)""")
md("Testbed, mean confirmation time (s) by block size and load (5 repetitions each):")
code("""sel = stats[stats['block'].isin(['B10', 'B10H', 'A', 'B100', 'B500', 'T025', 'T1']) & stats['round'].str.startswith('uniform')]
sel[['block', 'round', 'lat_mean', 'lat_ci', 'lat_min', 'lat_max', 'tps_mean', 'fail_pct']]""")

md("## Section 6.3: number of endorsing institutions (model) and threshold (testbed)")
code("""R = J('res03_measured.json'); out = []
for c in range(3, 12):
    a, h = R[f'default_{c}'], R[f'hedged_{c}']
    out.append(dict(c=c, q=a['q'], tolerated=c - a['q'], capacity=a['cap'], default_formula_ms=1000 * a['formula'],
                    default_sim_ms=1000 * a['endorse'][0], hedged_formula_ms=1000 * h['formula'], hedged_sim_ms=1000 * h['endorse'][0]))
display(pd.DataFrame(out))
q = stats[stats['block'].isin(['Q1', 'Q2', 'B100', 'Q4', 'Q5']) & stats['round'].isin(['uniform-150tps', 'uniform-200tps'])]
q[['block', 'round', 'lat_mean', 'lat_ci', 'endorse_ms', 'fail_pct']]""")

md("## Section 6.4: two of five peers fail at t = 500 s (10 replications)")
code("""R = J('res10_failure_measured.json'); wins = ['300-500', '500-560', '560-650', '650-800', '800-900']; out = []
for k, v in R.items():
    W = 1000 * np.array([r['windows'] for r in v.values()])
    out.append({'case': k, **{w: f"{m:.1f}" for w, m in zip(wins, W.mean(0))}})
pd.DataFrame(out)""")

md("## Section 6.5: surges (10 replications) and the fluid approximation")
code("""from cbdc_v2_formulas import surge_fluid
R = J('res10_surge_measured.json'); edges = np.arange(300, 901, 20); out = []
for k in ['surge_500', 'surge_1000']:
    reps = [v for kk, v in R[k].items() if kk != 'capacity']
    wm = np.array([r['win_mean'] for r in reps]); wx = np.array([r['win_max'] for r in reps])
    sel = (edges[:-1] >= 500) & (edges[:-1] < 700)
    out.append(dict(case=k, before_ms=1000 * wm[:, :10].mean(), largest_window_s=wm[:, sel].max(1).mean(),
                    largest_single_s=wx[:, sel].max(1).mean()))
display(pd.DataFrame(out))
print('fluid, 1000 TPS for 60 s:', surge_fluid(200, 1000, 60, R['surge_1000']['capacity']))""")

md("## Section 6.6: confirmation time across loads")
code("""R = J('res10_sweep_measured.json')
pd.DataFrame([dict(case=k, B=v['B'], max_util=max(v['rhos']), formula_ms=1000 * v['formula'], sim_ms=1000 * v['sim']['mean'][0])
              for k, v in R.items()])""")

md("## Section 4.7: bursty arrivals (matrix-analytic analysis against simulation)")
code("""R = J('res_map_measured.json'); A = R['analysis']; S = R['sim']; out = []
for case in ['poisson', 'mild', 'strong', 'stress']:
    reps = [v for k, v in S.items() if k.startswith(case + '_')]; a = A[case]
    lo = a['peer'] + a['formation'] + a['road'] + a['commit']; hi = a['endorse'] + a['formation'] + a['road'] + a['commit']
    out.append(dict(case=case, bracket_ms=f"[{1000*lo:.1f}, {1000*hi:.1f}]", sim_total_ms=1000 * np.mean([r['total'] for r in reps]),
                    formation_exact_ms=1000 * a['formation']))
pd.DataFrame(out)""")

md("## Section 6.7: contention for accounts")
code("""c = stats[(stats['block'] == 'D') | ((stats['block'] == 'B100') & stats['round'].str.startswith('uniform'))]
c[['block', 'round', 'fail_pct', 'fail_ci', 'tps_mean', 'lat_mean']]""")

md("## Figures\nEach figure is regenerated by its script in `figures/scripts/` and shown from `figures/output/`. Panel (b) of the surge figure needs the raw failure and surge rounds (`EF_results.tar.gz`); without them the saved figure is shown.")
code("""figs = ['fig_endorsement_dispatch', 'fig_validation', 'fig_block_size', 'fig_institutions', 'fig_surge', 'fig_loadcurve', 'fig_contention']
for f in figs:
    if f == 'fig_endorsement_dispatch':
        status = 'saved (regenerating simulates; run the script to redo)'
    else:
        r = subprocess.run([sys.executable, f + '.py'], cwd='figures/scripts', capture_output=True, text=True)
        status = 'regenerated' if r.returncode == 0 else 'saved (raw data not present)'
    print(f, '->', status); display(Image(filename=f'figures/output/{f}.png', width=420))""")
nb['cells'] = C
nb['metadata']['kernelspec'] = {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}
nbf.write(nb, 'cbdc-v2-release/reproduce_paper.ipynb'); print('written')
