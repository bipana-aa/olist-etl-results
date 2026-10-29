"""Write the project files: the combined .sql file, every query with its result, and the written report."""
import pandas as pd

from .config import ROOT, SQL_DIR
from .state import CLEAN_LOG, STATS
from .utils import md_table


def write_project_files(sql_results):
    """Write sql/olist_ecommerce.sql, docs/sql_report_results.md and docs/Project_Report.md."""
    schema_sql = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")

    # 1) One combined .sql file: table creation + reporting queries
    reports_sql = (SQL_DIR / "reports.sql").read_text(encoding="utf-8")
    (SQL_DIR / "olist_ecommerce.sql").write_text(
        "-- ===== PART 1: DATABASE AND TABLE CREATION =====\n" + schema_sql
        + "\n\n-- ===== PART 2: SQL REPORTING QUERIES =====\n" + reports_sql, encoding="utf-8")

    # 2) Every query with its result
    parts = ["# SQL Reports: queries and results\n",
             f"Database: `database/olist.db` (SQLite). {len(sql_results)} reporting queries.\n"]
    for name, (question, sql, result) in sql_results.items():
        parts += [f"\n## {name}\n", f"**Question:** {question}\n", "```sql\n" + sql + ";\n```\n",
                  "**Result:**\n", md_table(result), ""]
    (ROOT / "docs" / "sql_report_results.md").write_text("\n".join(parts), encoding="utf-8")
    print("Wrote sql/olist_ecommerce.sql and docs/sql_report_results.md")

    # 3) The written project report, filled with this run's numbers
    shapes = STATS["raw_shapes"]
    total_rows = sum(r for r, _ in shapes.values())
    clean = STATS["clean_shapes"]
    n_orders = shapes["orders"][0]
    first_ts = STATS["first_purchase_date"]
    last_ts = STATS["last_purchase_date"]

    # Pieces of the report are built first, so the big text below stays simple
    extract_table = md_table(pd.DataFrame({"file": list(shapes.keys()),
                                           "rows": [v[0] for v in shapes.values()],
                                           "columns": [v[1] for v in shapes.values()]}), 20)
    nulls_table = md_table(STATS["null_report"].head(8), 8)
    log_df = pd.DataFrame(CLEAN_LOG, columns=["Table", "What was done", "Rows affected", "Why"])
    cleaning_table = md_table(log_df[log_df["Rows affected"] > 0], 60)

    uc, kd, inv = STATS["unique_counts"], STATS["key_dups"], STATS["invalid"]
    peak_month, peak_orders = STATS["eda_peak_orders_month"]
    loaded_line = ", ".join(f"{k} {v:,}" for k, v in STATS["loaded_rows"].items())
    insight_lines = "\n".join(f"{i}. {t}" for i, t in enumerate(STATS["insights"], 1))
    sql_lines = "\n".join(f"{i}. **{n}**: {q}" for i, (n, (q, _s, _r)) in enumerate(sql_results.items(), 1))
    n_not_defined = inv["payments: payment_type = 'not_defined'"]
    n_zero_installments = inv["payments: payment_installments = 0"]
    n_zero_weight = inv["products: weight_g = 0"]
    n_dup_reviews = kd["reviews: repeated (review_id, order_id)"]
    n_dup_review_ids = kd["reviews: repeated review_id"]
    n_geo_dups = STATS["full_row_dups"]["geolocation"]
    satisfaction_note = "most customers are satisfied" if STATS["eda_five_star_pct"] >= 50 else "many customers are not fully satisfied"

    report = f"""# Project Report: End-to-End ETL & Data Analysis Pipeline

**Student:** Bipana Khadka
**Dataset:** Brazilian E-Commerce Public Dataset by Olist (Kaggle)
**Tools:** Python, Pandas, Matplotlib, SQLAlchemy, SQLite, SQL

## 1. Dataset and Source
The data comes from the public Kaggle dataset *Brazilian E-Commerce Public Dataset by Olist*
(https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). It describes orders placed on a Brazilian online
marketplace between {first_ts} and {last_ts}. It has **{len(shapes)} CSV files, {STATS["total_columns"]} columns and {total_rows:,} rows** in total,
including **{n_orders:,} orders**. The files cover orders, order items, customers, products, sellers, payments, reviews,
geolocation and a category translation table. Money is in Brazilian reais (R$).

## 2. Objective
Build a complete and repeatable ETL pipeline: extract the raw files, explore and clean them with Python and Pandas,
transform them into related tables, load them into a relational SQLite database, and use SQL and Pandas to find business
insights about sales, customers, payments and delivery.

## 3. Extraction
All {len(shapes)} CSV files are read with `pandas.read_csv` into DataFrames. The original files in `data/raw/` are never edited;
all cleaning is done on copies.

{extract_table}

## 4. EDA Findings
- The busiest month in the raw data was **{peak_month}** with {peak_orders:,} orders (see `docs/figures/01_orders_per_month.png`).
- {STATS["eda_five_star_pct"]}% of all reviews give 5 stars, so {satisfaction_note}.
- The median item price is R$ {STATS["eda_price_median"]}, with a long tail of expensive items.
- `customer_id` is created for every order, while `customer_unique_id` identifies the real person: there are {uc["customers.customer_id"]:,} customer ids but only {uc["customers.customer_unique_id"]:,} real customers.
- Customers come from {uc["customers.customer_state"]} states, and {uc["products.product_category_name"]} product categories exist.

## 5. Data Quality Issues Found
**Missing values (largest):**

{nulls_table}

**Other issues:**
- {STATS["wrong_types"]} date columns were stored as plain text.
- Duplicates: the reviews file has {n_dup_reviews:,} repeated (review_id, order_id) pairs, and the geolocation file has {n_geo_dups:,} fully duplicated rows.
- Invalid values: {n_not_defined} payments with type not_defined, {n_zero_installments} payments with 0 installments, {n_zero_weight} products with weight 0 g.
- {len(STATS["untranslated"])} product categories had no English translation.
- City names had accents, extra spaces and mixed capital letters.
- Outliers: very expensive items exist, but they are real purchases, so they were kept.

## 6. Cleaning and Transformation
Every step is based on a problem found during EDA:

{cleaning_table}

New analysis tables: `sales` (one row per sold item), `order_totals` (one row per order) and `customer_orders` (one row per real customer with a segment).
{STATS["quality_checks"]} automatic quality checks must pass before anything is loaded.

## 7. Database Design
The database has **9 related tables**: customers, sellers, geolocation, product_categories, products, orders, order_items, order_payments, order_reviews.
Each table has a primary key, and foreign keys link them (customer, then orders, then items / payments / reviews; products and sellers, then items;
category, then products). CHECK constraints protect the data (for example price at least 0, review score 1 to 5, valid order status and payment type).
The ERD is in `docs/ERD.png` and the SQL is in `sql/schema.sql`.

![ERD](ERD.png)

## 8. ETL Process
1. **Extract:** read the 9 CSV files with Pandas.
2. **Transform:** explore, check quality, clean and build new columns with Pandas.
3. **Load:** delete the old database, create the tables from `schema.sql`, and load the DataFrames with SQLAlchemy (`to_sql`) in parent-before-child order.
4. **Verify:** row counts, foreign key check and integrity check.
5. **Report:** run the SQL queries and save the results.

Loaded rows: {loaded_line}.
The whole process is repeatable with `python run_pipeline.py` (or by running the notebook).

## 9. Data Analysis
Seven questions were answered with Pandas: top categories by revenue, the best month, customers by state, payment methods,
average order value, delivery time versus reviews, and repeat customers.

![Top categories](figures/04_top_categories_revenue.png)
![Monthly revenue](figures/05_monthly_revenue.png)
![Delivery vs review](figures/08_delivery_vs_review.png)

## 10. Key Insights
{insight_lines}

## 11. SQL Reports
{len(sql_results)} queries (see `sql/reports.sql`; results in `docs/sql_report_results.md` and `outputs/sql_reports/`):

{sql_lines}

## 12. Challenges Encountered
- **Repeated review ids:** {n_dup_review_ids:,} review_id values appear more than once, so `review_id` alone cannot be a primary key. A composite key (review_id, order_id) was used.
- **Customer identity:** `customer_id` changes with every order, so customer analysis uses `customer_unique_id`.
- **Huge geolocation file:** it has {shapes["geolocation"][0]:,} rows with many repeated zip codes. It was reduced to {clean["geolocation"]:,} rows (one per zip prefix). A foreign key from customers to it was not used because some customer zip codes are not in the file.
- **Missing translations and categories:** some products had no category and some categories had no English name; these were handled with an 'unknown' category and a readable fallback name.
- **Dates as text:** all date columns had to be converted before delivery time and monthly trends could be calculated.
- **Keeping the load repeatable:** the database is deleted and rebuilt on each run, with foreign keys switched on so mistakes are caught immediately.

## 13. Conclusion
The project turns {total_rows:,} rows of raw marketplace data across {len(shapes)} files into a clean, validated, relational database and a set of
reports. It shows the complete path: Raw Data, Extract, Explore, Clean, Transform, Analyze, Load, SQL Reports. The business findings
(see Key Insights) show where revenue comes from, how customers pay, and how delivery speed affects satisfaction.
Possible next steps: scheduling the pipeline (for example with Airflow), loading into PostgreSQL, and building a dashboard.
"""
    (ROOT / "docs" / "Project_Report.md").write_text(report, encoding="utf-8")
    print("Wrote docs/Project_Report.md")
