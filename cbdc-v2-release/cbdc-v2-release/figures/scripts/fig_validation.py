"""Fig (Sec 5.3): measured confirmation time on the testbed against the model, B = 10, 50, 100 (q = 3, tau = 2 s).
Markers: per-repetition measured means (open = round congested: steady throughput < 97% of offered).
Lines: model with low-load parameters (cbdc_v2_formulas.end_to_end, measured PIPE).
Squares: model with stage times measured in the same round (references/results/model_vs_measured.txt).
Data: references/results/campaign_rounds.csv. Generated 2026-10-30."""
import sys, csv, re, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "../../model")
from cbdc_style import *
from cbdc_v2_formulas import end_to_end
from cbdc_v2_params import PIPE
setup()
R = list(csv.DictReader(open("../../results/campaign_rounds.csv")))
PL = {}
for line in open("../../results/model_vs_measured.txt"):
    m = re.match(r"(\S+)\s+(\d+) \|\s+(\d+) \|\s+(\d+) ", line)
    if m: PL[(m.group(1), int(m.group(2)))] = float(m.group(4))
cfg = [("B10", "B10H", 10, COLORS["a"]), ("A", None, 50, COLORS["c"]), ("B100", None, 100, COLORS["b"])]
fig, ax = plt.subplots(figsize=(3.5, 2.8))
for blk, extra, B, col in cfg:
    lam = np.linspace(20, 310, 300)
    y = []
    for l in lam:
        try: y.append(1e3 * end_to_end(l, B, **PIPE))
        except Exception: y.append(np.nan)
    ax.plot(lam, y, color=col, lw=1.1, label=f"B = {B}: model, low-load parameters")
    for b in [blk] + ([extra] if extra else []):
        for r in R:
            if r["block"] != b or not r["round"].startswith("uniform"): continue
            l = int(re.search(r"(\d+)tps", r["round"]).group(1)); v = 1e3 * float(r["avg_lat_s"])
            ok = float(r["steady_tps"]) >= 0.97 * l
            ax.plot(l + np.random.uniform(-3, 3), v, "o", ms=3, mfc=col if ok else "none", mec=col, mew=0.8, alpha=0.85)
    for (b, l), v in PL.items():
        if b == blk: ax.plot(l, v, "s", ms=4, mfc="white", mec=col, mew=1.0)
ax.set_yscale("log"); ax.set_ylim(60, 12000); ax.set_xlim(0, 320)
nepal_load_context(ax)
ax.set_xlabel("Offered load λ (transactions per second)")
ax.set_ylabel("Mean confirmation time (ms)")
from matplotlib.lines import Line2D
h = [Line2D([], [], color=c, lw=1.1, label=f"B = {B}") for _, _, B, c in cfg]
h += [Line2D([], [], color="k", lw=1.1, label="model, low-load parameters"),
      Line2D([], [], ls="", marker="s", mfc="white", mec="k", label="model, stage times at that load"),
      Line2D([], [], ls="", marker="o", mfc="k", mec="k", ms=3, label="testbed repetition"),
      Line2D([], [], ls="", marker="o", mfc="none", mec="k", ms=3, label="testbed repetition, congested")]
ax.legend(handles=h, fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False)
save(fig, "fig_validation"); print("saved")
