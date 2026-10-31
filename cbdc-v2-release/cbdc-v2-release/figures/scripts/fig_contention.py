"""Fig (Sec 6.7): share of transactions invalidated against load for four account-access workloads (testbed, B = 100,
q = 3, 5 reps; campaign_rounds.csv blocks B100 and D), with the same-block prediction (dashes) and the valid
throughput at 200 TPS offered (right panel). Generated 2026-10-30."""
import sys, csv, numpy as np
sys.path.insert(0, ".")
from cbdc_style import *
setup()
R = list(csv.DictReader(open("../../results/campaign_rounds.csv")))
W = [("uniform", "B100", "Uniform, 10,000", 1.93, COLORS["b"]), ("zipf0.8", "D", "Zipf 0.8", 10.32, COLORS["a"]),
     ("zipf1.2", "D", "Zipf 1.2", 47.38, COLORS["c"]), ("n100", "D", "Uniform, 100", 66.61, COLORS["d"])]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(3.5, 2.4), gridspec_kw={"width_ratios": [1.6, 1], "wspace": 0.45})
loads = [50, 150, 200]; valid = []
for case, blk, lab, pred, col in W:
    F = [[100 * float(r["fail_frac"]) for r in R if r["block"] == blk and r["round"] == f"{case}-{l}tps"] for l in loads]
    a1.errorbar(loads, [np.mean(f) for f in F], yerr=[2.776 * np.std(f, ddof=1) / np.sqrt(len(f)) for f in F],
                fmt="o-", ms=3, color=col, lw=1.0, capsize=1.5, label=lab)
    a1.plot([28, 42], [pred, pred], color=col, lw=2.5, solid_capstyle="butt")
    rr = [r for r in R if r["block"] == blk and r["round"] == f"{case}-200tps"]
    valid.append(np.mean([float(r["steady_tps"]) * (1 - float(r["fail_frac"])) for r in rr]))
a1.set_xlim(25, 215); a1.set_ylim(0, 80); a1.set_xticks(loads)
a1.set_xlabel("Offered load (TPS)"); a1.set_ylabel("Invalidated (%)")
a1.text(31, 77, "bars at left:\nsame-block prediction", fontsize=6, va="top", color=COLORS["grey"])
a1.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.75, -0.25), ncol=2, frameon=False)
a2.bar(range(4), valid, color=[w[4] for w in W])
a2.axhline(200, color="k", lw=0.7, ls="--"); a2.text(3.4, 203, "offered", fontsize=6, ha="right", va="bottom")
a2.set_xticks(range(4)); a2.set_xticklabels(["Unif.\n10k", "Zipf\n0.8", "Zipf\n1.2", "Unif.\n100"], fontsize=6)
a2.set_ylabel("Valid TPS at 200 offered"); a2.set_ylim(0, 230)
save(fig, "fig_contention"); print("saved", [round(v) for v in valid])
