"""Shared figure style for the CBDC paper. Every load-axis figure marks Nepal's load context so the
reader sees results against the national payment load, not in the abstract.
Load facts (from the manuscript, NRB PSOR FY2023/24): annual mean ~41 TPS; ASSUMED peak range
120-200 TPS (3-5x mean, unsourced: see issue C-5, widen if re-sourced); design target 200 TPS."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
NEPAL_MEAN, PEAK_LO, PEAK_HI, DESIGN = 41, 120, 200, 200
COLORS = {"default": "#0F6E56", "hedged": "#993C1D", "grey": "#5F5E5A",
          "a": "#185FA5", "b": "#0F6E56", "c": "#BA7517", "d": "#993C1D"}
def setup():
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.dpi": 150, "savefig.bbox": "tight", "font.family": "serif"})
def nepal_load_context(ax, ymax_frac=0.97, label=True):
    """Shade the assumed peak band and mark the FY2023/24 mean and the design target."""
    ax.axvspan(PEAK_LO, PEAK_HI, color="#B4B2A9", alpha=0.25, lw=0)
    ax.axvline(NEPAL_MEAN, color=COLORS["grey"], lw=0.8, ls=":")
    ax.axvline(DESIGN, color=COLORS["grey"], lw=0.8, ls="--")
    if label:
        lo, hi = ax.get_ylim(); span = hi - lo
        ax.text(NEPAL_MEAN, lo + ymax_frac * span, " mean\n FY23/24", fontsize=6.5, va="top", ha="left", color=COLORS["grey"])
        ax.text((PEAK_LO+PEAK_HI)/2, lo + (ymax_frac - 0.18) * span, "assumed\npeak", fontsize=6.5, va="top", ha="center", color=COLORS["grey"])
        ax.text(DESIGN, lo + (ymax_frac - 0.36) * span, " design\n 200 TPS", fontsize=6.5, va="top", ha="left", color=COLORS["grey"])
def illustrative_note(fig, text="Service rates illustrative, pending prototype measurement"):
    fig.text(0.5, -0.17, text, fontsize=6.5, ha="center", va="top", style="italic", color="#888780")
def save(fig, name, outdir="../output"):
    import os; os.makedirs(outdir, exist_ok=True)
    fig.savefig(f"{outdir}/{name}.pdf"); fig.savefig(f"{outdir}/{name}.png", dpi=200)
