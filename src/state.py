"""Numbers and messages collected while the pipeline runs (used by the final report)."""

STATS = {}        # numbers for the report
CLEAN_LOG = []    # (table, what we did, rows affected, why)
INSIGHTS = []     # business insights written from the analysis


def reset_state():
    """Empty the shared containers (in place, so every module sees the change)."""
    STATS.clear()
    CLEAN_LOG.clear()
    INSIGHTS.clear()
