"""Fig (Sec 4.2): mean endorsement time vs load for default and hedged dispatch, closed form (lines)
and fork-join simulation (markers, 95% CI), with Nepal load context and stability limits.
MEASURED mu_e = 436/s (testbed, Sec. 5.3), c = 5, q = 3 (regenerated 2026-10-30)."""
import sys, numpy as np; sys.path.insert(0, "../../verification"); sys.path.insert(0, ".")
from cbdc_style import *
from endorsement_check import formula, simulate
setup(); mu, c, q = 436, 5, 3
lam = np.linspace(5, 700, 500)
fig, ax = plt.subplots(figsize=(3.5, 2.6))
for rule, lab in [("default", "Default: send to q, wait for all"), ("hedged", "Hedged: send to all c, first q")]:
    y = np.array([formula(rule, l, mu, c, q) for l in lam]) * 1e3
    ax.plot(lam, y, color=COLORS[rule], lw=1.3, label=lab)
    pts = [50, 100, 200, 300, 380] if rule == "hedged" else [50, 100, 200, 300, 400, 500, 600]
    for l in pts:
        reps = [simulate(rule, l, mu, c, q, n=40_000, warm=4_000, seed=s).mean()*1e3 for s in range(5)]
        m = np.mean(reps); ci = 1.96*np.std(reps, ddof=1)/np.sqrt(len(reps))
        ax.errorbar(l, m, yerr=ci, fmt="o", ms=3, color=COLORS[rule], capsize=2, lw=0.8)
ax.set_ylim(0, 30); ax.set_xlim(0, 760)
ax.axvline(mu, color=COLORS["hedged"], lw=0.6, ls="-.")
ax.axvline(c*mu/q, color=COLORS["default"], lw=0.6, ls="-.")
ax.text(mu+6, 25, "hedged\nlimit µe", fontsize=6.5, color=COLORS["hedged"])
ax.text(c*mu/q-60, 25, "default\nlimit\ncµe/q", fontsize=6.5, color=COLORS["default"])
nepal_load_context(ax)
ax.set_xlabel("Offered load λ (transactions per second)")
ax.set_ylabel("Mean endorsement time (ms)")
ax.legend(fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1, frameon=False)
save(fig, "fig_endorsement_dispatch")
print("saved")
