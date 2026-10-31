"""Fig (Sec 6.6): confirmation time against load, measured parameters, q = 3 of 5, tau = 2 s.
B = 100: formula (line), simulation (markers, 95% CI; res10_sweep_measured.json), testbed (squares, mean and range).
Model-only re-chosen B (2-6): dashed, labelled as not stable on the testbed. Generated 2026-10-30."""
import sys, json, csv, re, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "../../model")
from cbdc_style import *
from cbdc_v2_formulas import end_to_end
from cbdc_v2_params import PIPE
setup()
S = json.load(open("../../model/res10_sweep_measured.json"))
R = list(csv.DictReader(open("../../results/campaign_rounds.csv")))
fig, ax = plt.subplots(figsize=(3.5, 2.7))
lam = np.linspace(20, 320, 300)
ax.plot(lam, [1e3 * end_to_end(l, 100, **PIPE) for l in lam], color=COLORS["b"], lw=1.2, label="B = 100, formula")
for k, v in S.items():
    l = int(k.split("_")[1]); m, h = 1e3 * v["sim"]["mean"][0], 1e3 * v["sim"]["mean"][1]
    if k.startswith("fixed"): ax.errorbar(l, m, yerr=h, fmt="o", ms=3, color=COLORS["b"], capsize=2, lw=0.8)
ls = sorted(int(k.split("_")[1]) for k in S if k.startswith("rechosen"))
ax.plot(ls, [1e3 * S[f"rechosen_{l}"]["formula"] for l in ls], color=COLORS["d"], lw=1.0, ls="--",
        label="model-only best B (2 to 6), not stable on testbed")
for l in (50, 150, 200):
    v = [1e3 * float(r["avg_lat_s"]) for r in R if r["block"] == "B100" and r["round"] == f"uniform-{l}tps"]
    ax.errorbar(l + 6, np.mean(v), yerr=[[np.mean(v) - min(v)], [max(v) - np.mean(v)]], fmt="s", ms=4,
                mfc="white", mec="k", ecolor="k", capsize=2, lw=0.8)
ax.plot([], [], "s", mfc="white", mec="k", label="B = 100, testbed (mean, range of 5)")
ax.plot([], [], "o", ms=3, color=COLORS["b"], label="B = 100, simulation (95% CI)")
ax.set_ylim(0, 1250); ax.set_xlim(0, 320)
nepal_load_context(ax)
ax.set_xlabel("Offered load λ (transactions per second)"); ax.set_ylabel("Mean confirmation time (ms)")
ax.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1, frameon=False)
save(fig, "fig_loadcurve"); print("saved")
