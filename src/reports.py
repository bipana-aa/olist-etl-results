"""SQL reports: run the queries in sql/reports.sql, save each result, and cross-check them against Pandas."""
import re

import pandas as pd

from .config import OUT_DIR, SQL_DIR
from .state import STATS
from .utils import display


def parse_reports(path):
    """Read reports.sql and return a list of (name, question, sql)."""
    text_ = path.read_text(encoding="utf-8")
    parts = re.split(r"^-- name:\s*(\S+)\s*$", text_, flags=re.M)
    queries = []
    for i in range(1, len(parts), 2):
        name, body = parts[i], parts[i + 1]
        question = re.search(r"^-- question:\s*(.+)$", body, flags=re.M)
        sql = "\n".join(line for line in body.splitlines() if not line.startswith("-- question:")).strip().rstrip(";")
        queries.append((name, question.group(1).strip() if question else "", sql))
    return queries


def run_sql_reports(engine):
    """Run every query in sql/reports.sql. Returns {name: (question, sql, result)}."""
    queries = parse_reports(SQL_DIR / "reports.sql")
    sql_results = {}
    for name, question, sql in queries:
        with engine.connect() as con:
            result = pd.read_sql_query(sql, con)
        result.to_csv(OUT_DIR / f"{name}.csv", index=False)
        sql_results[name] = (question, sql, result)
        print(f"\n### {name}\n{question}")
        display(result.head(10))
    print(f"\n{len(queries)} reports ran and were saved in {OUT_DIR}")
    assert len(queries) >= 8, "At least 8 SQL reports are required"
    STATS["sql_report_count"] = len(queries)
    return sql_results


def cross_check(sql_results, analysis):
    """The SQL answers must match the Pandas answers (top category and average order value)."""
    cat_rev, aov = analysis["cat_rev"], analysis["aov"]
    sql_top_category = sql_results["01_revenue_by_category"][2].iloc[0]["category"]
    sql_aov = float(sql_results["05_average_order_value"][2].iloc[0]["avg_order_value"])
    print(f"Top category   - Pandas: {cat_rev.index[0]!r}   SQL: {sql_top_category!r}")
    print(f"Average order  - Pandas: {aov:,.2f}   SQL: {sql_aov:,.2f}")
    assert sql_top_category == cat_rev.index[0], "Pandas and SQL disagree on the top category"
    assert abs(sql_aov - round(aov, 2)) < 0.01, "Pandas and SQL disagree on average order value"
    print("Pandas and SQL agree.")
