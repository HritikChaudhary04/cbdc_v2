"""Fig (Sec 6.5): (a) simulation: mean confirmation time by 20 s arrival window, surges from 200 TPS to 500 and 1000 TPS
for 60 s at t = 500 s (B = 100, measured parameters, 10 reps; res10_surge_measured.json), fluid peak marked.
(b) testbed: committed TPS at inst1 per 10 s for the 100 -> 250 -> 100 TPS surge, mean and range over 5 reps
(raw block logs of block F; path EF_DIR). Generated 2026-10-30."""
import sys, json, glob, csv, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "../../model")
from cbdc_style import *
from cbdc_v2_formulas import surge_fluid
setup()
EF_DIR = sys.argv[1] if len(sys.argv) > 1 else "../../data/raw/EF_results"
R = json.load(open("../../model/res10_surge_measured.json")); edges = np.arange(300, 901, 20)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(3.5, 4.6), gridspec_kw={"hspace": 0.55})
for k, col, lab in [("surge_500", COLORS["b"], "500 TPS (within capacity)"), ("surge_1000", COLORS["d"], "1,000 TPS (above capacity)")]:
    W = np.array([v["win_mean"] for kk, v in R[k].items() if kk != "capacity"])
    m = W.mean(0); lo, hi = W.min(0), W.max(0); x = edges[:-1] + 10
    a1.plot(x, m, color=col, lw=1.1, label=lab); a1.fill_between(x, lo, hi, color=col, alpha=0.2, lw=0)
fl = surge_fluid(200, 1000, 60, R["surge_1000"]["capacity"])
a1.axhline(0.336 + fl["peak_extra_delay"], color=COLORS["d"], lw=0.7, ls=":")
a1.text(612, 0.336 + fl["peak_extra_delay"] * 1.2, "fluid peak", fontsize=6.5, color=COLORS["d"])
a1.axvspan(500, 560, color="#B4B2A9", alpha=0.3, lw=0)
a1.set_yscale("log"); a1.set_ylim(0.1, 200); a1.set_xlim(300, 900)
a1.set_xlabel("Arrival time (s)"); a1.set_ylabel("Confirmation time (s)")
a1.text(0.02, 0.97, "(a) model, surges from 200 TPS for 60 s", transform=a1.transAxes, fontsize=7, va="top")
a1.legend(fontsize=6.5, loc="center right", bbox_to_anchor=(1.0, 0.55), frameon=False)
series = []
for d in sorted(x for x in glob.glob(f"{EF_DIR}/*F-rep*") if not x.endswith(".txt")):
    r = glob.glob(d + "/02-*")[0]
    bo = [float(x["created_utc"]) for x in csv.DictReader(open(r + "/blocks_orderer.csv"))]
    bp = [(float(x["committed_utc"]), int(x["n_tx"])) for x in csv.DictReader(open(r + "/blocks_peer.csv")) if "inst1" in x["peer"]]
    T0 = min(bo); b = np.zeros(30)
    for t, n in bp:
        i = int((t - T0) // 10)
        if 0 <= i < 30: b[i] += n / 10
    series.append(b)
S = np.array(series); x = np.arange(30) * 10 + 5
a2.plot(x, S.mean(0), "o-", ms=3, color=COLORS["b"], lw=1.0, label="committed (mean of 5)")
a2.fill_between(x, S.min(0), S.max(0), color=COLORS["b"], alpha=0.2, lw=0)
a2.step([0, 100, 200, 300], [100, 250, 100, 100], where="post", color="k", lw=0.8, ls="--", label="offered")
a2.set_xlim(0, 300); a2.set_ylim(0, 320)
a2.set_xlabel("Time from start of round (s)"); a2.set_ylabel("Transactions per second")
a2.text(0.02, 0.97, "(b) testbed, B = 100, surge to 250 TPS", transform=a2.transAxes, fontsize=7, va="top")
a2.legend(fontsize=6.5, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False)
save(fig, "fig_surge"); print("saved", S.shape)
