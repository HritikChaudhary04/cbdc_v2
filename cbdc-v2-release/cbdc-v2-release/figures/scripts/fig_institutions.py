"""Fig (Sec 6.3): (a) model: endorsement time against the number of endorsing institutions c = 3..11 with majority q,
default and hedged dispatch, closed form (lines) and simulation (markers, 95% CI; res03_measured.json), 200 TPS, B = 100;
even c marked open. (b) testbed, c = 5: confirmation time (left axis) and endorsement mismatches per round (right axis)
against the threshold q at 200 TPS (campaign_rounds.csv). Generated 2026-10-30."""
import sys, json, csv, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "../../model")
from cbdc_style import *
setup()
D = json.load(open("../../model/res03_measured.json"))
R = list(csv.DictReader(open("../../results/campaign_rounds.csv")))
fig, (a1, a2) = plt.subplots(2, 1, figsize=(3.5, 4.6), gridspec_kw={"hspace": 0.55})
cs = np.arange(3, 12)
for rule in ["default", "hedged"]:
    col = COLORS[rule]
    a1.plot(cs, [1e3 * D[f"{rule}_{c}"]["formula"] for c in cs], color=col, lw=1.1, label=f"{rule.capitalize()} dispatch")
    for c in cs:
        m, h = [1e3 * x for x in D[f"{rule}_{c}"]["endorse"]]
        a1.errorbar(c, m, yerr=h, fmt="o", ms=3.5, mfc=col if c % 2 else "white", mec=col, ecolor=col, capsize=1.5, lw=0.8)
a1.set_xlabel("Endorsing institutions c (majority q)"); a1.set_ylabel("Endorsement time (ms)")
a1.set_xticks(cs); a1.set_ylim(0, 9)
a1.text(0.02, 0.97, "(a) model, 200 TPS; open: even c", transform=a1.transAxes, fontsize=7, va="top")
a1.legend(fontsize=6.5, loc="lower right", frameon=False)
blk = {1: "Q1", 2: "Q2", 3: "B100", 4: "Q4", 5: "Q5"}
qs = np.arange(1, 6)
lat = [[1e3 * float(r["avg_lat_s"]) for r in R if r["block"] == blk[q] and r["round"] == "uniform-200tps"] for q in qs]
mis = [[float(r["mism"]) for r in R if r["block"] == blk[q] and r["round"] == "uniform-200tps"] for q in qs]
a2.errorbar(qs, [np.mean(v) for v in lat], yerr=[[np.mean(v) - min(v) for v in lat], [max(v) - np.mean(v) for v in lat]],
            fmt="o-", ms=4, color=COLORS["b"], capsize=2, lw=1.0, label="confirmation time")
a2.set_xlabel("Endorsement threshold q (of c = 5)"); a2.set_ylabel("Confirmation time (ms)", color=COLORS["b"])
a2.set_xticks(qs); a2.set_ylim(300, 600)
b2 = a2.twinx(); b2.spines["right"].set_visible(True)
b2.plot(qs, [np.mean(v) for v in mis], "s--", ms=3.5, color=COLORS["d"], lw=0.9, label="mismatches per round")
b2.set_ylabel("Mismatches per 300 s round", color=COLORS["d"]); b2.set_ylim(0, 420)
a2.text(0.02, 0.97, "(b) testbed, 200 TPS, B = 100", transform=a2.transAxes, fontsize=7, va="top")
h1, l1 = a2.get_legend_handles_labels(); h2, l2 = b2.get_legend_handles_labels()
a2.legend(h1 + h2, l1 + l2, fontsize=6.5, loc="lower right", frameon=False)
save(fig, "fig_institutions"); print("saved")
