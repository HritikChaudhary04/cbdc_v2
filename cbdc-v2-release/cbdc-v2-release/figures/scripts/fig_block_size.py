"""Fig (Sec 6.2): confirmation time against block size B at 50 and 200 TPS (q = 3 of 5, tau = 2 s, measured parameters).
Lines: formula (cbdc_v2_formulas.end_to_end) where every stage < 100% busy. Markers: testbed repetitions
(campaign_rounds.csv: B10 / B10H, A = B50, B100, B500); open = congested (steady throughput < 97% of offered).
Regenerated 2026-10-30 (previous version: illustrative costs, ordering stage only)."""
import sys, csv, re, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "../../model")
from cbdc_style import *
from cbdc_v2_formulas import end_to_end, stage_rhos
from cbdc_v2_params import PIPE
setup()
R = list(csv.DictReader(open("../../results/campaign_rounds.csv")))
BLK = {10: ["B10", "B10H"], 50: ["A"], 100: ["B100"], 500: ["B500"]}
fig, ax = plt.subplots(figsize=(3.5, 2.7))
for l, col in [(50, COLORS["a"]), (200, COLORS["d"])]:
    Bs = np.unique(np.round(np.logspace(np.log10(2), np.log10(500), 120)).astype(int))
    y = [1e3 * end_to_end(l, B, **PIPE) if max(stage_rhos(l, B, **PIPE)) < 1 else np.nan for B in Bs]
    ax.plot(Bs, y, color=col, lw=1.1, label=f"{l} TPS: model")
    for B, blks in BLK.items():
        for r in R:
            if r["block"] in blks and r["round"] == f"uniform-{l}tps":
                ok = float(r["steady_tps"]) >= 0.97 * l
                ax.plot(B * np.exp(np.random.uniform(-0.06, 0.06)), 1e3 * float(r["avg_lat_s"]), "o", ms=3.2,
                        mfc=col if ok else "none", mec=col, mew=0.8)
    ax.plot([], [], "o", ms=3.2, color=col, label=f"{l} TPS: testbed (open: congested)")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(1.7, 650); ax.set_ylim(30, 12000)
ax.set_xticks([2, 5, 10, 20, 50, 100, 200, 500]); ax.set_xticklabels(["2", "5", "10", "20", "50", "100", "200", "500"])
ax.set_xlabel("Block size B (transactions)"); ax.set_ylabel("Mean confirmation time (ms)")
ax.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False)
save(fig, "fig_block_size"); print("saved")
