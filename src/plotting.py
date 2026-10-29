"""Chart style and the helper that saves every chart to docs/figures/."""
import matplotlib

# In a notebook charts are shown; in a plain script they are only saved to files.
try:
    get_ipython()
except NameError:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from .config import FIG_DIR

BLUE, INK, MUTED, GRID = "#2a78d6", "#0b0b0b", "#52514e", "#e3e2de"
THOUSANDS = FuncFormatter(lambda v, _: f"{v:,.0f}")     # 80000 -> 80,000
plt.rcParams.update({
    "figure.figsize": (9, 4.5), "figure.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "font.size": 10,
})


def save_fig(name):
    plt.tight_layout()
    plt.savefig(FIG_DIR / name, dpi=130)
    plt.show()
    plt.close()
