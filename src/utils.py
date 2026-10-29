"""Small helpers used by every step: logging, text cleaning, markdown tables, display."""
import unicodedata
import warnings

import pandas as pd

from .state import CLEAN_LOG

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 40)
pd.set_option("display.width", 200)

# In Jupyter `display` shows nice tables; in a plain script it is just print.
try:
    get_ipython()
    from IPython.display import display
except NameError:
    display = print


def log(table, action, n, why):
    """Record one cleaning step so it can be explained in the report."""
    CLEAN_LOG.append((table, action, int(n), why))
    print(f"[{table}] {action}: {int(n):,}")


def strip_accents(text):
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")


def clean_text(series):
    """trim spaces, lower-case, remove accents, then Title Case (e.g. ' São PAULO ' -> 'Sao Paulo')."""
    s = series.astype("string").str.strip().str.lower()
    mapping = {u: strip_accents(u) for u in s.dropna().unique()}   # map unique values only: fast
    return s.map(mapping).str.title()


def md_table(frame, max_rows=15):
    shown = frame.head(max_rows)
    cols = [str(c) for c in shown.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in shown.iterrows():
        cells = []
        for v in row:
            cells.append(f"{v:,.2f}" if isinstance(v, float) else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    if len(frame) > max_rows:
        lines.append(f"\n*(first {max_rows} of {len(frame)} rows)*")
    return "\n".join(lines)
