"""
Olist E-Commerce ETL pipeline.

Run from the project root:   python run_pipeline.py

Extract the 9 CSV files in data/raw/, clean and transform them, load them into database/olist.db (SQLite),
run the SQL reports and write the charts and the report. Each step lives in its own module in src/.
"""
from src.analyze import run_analysis
from src.clean import clean_all
from src.config import DB_PATH, ROOT, ensure_dirs
from src.eda import run_eda
from src.extract import extract
from src.load import build_load_plan, create_database, load_tables, verify_load
from src.quality import run_quality_checks
from src.report_writer import write_project_files
from src.reports import cross_check, run_sql_reports
from src.state import reset_state
from src.transform import build_analysis_tables, save_processed


def main():
    reset_state()
    ensure_dirs()
    print("Project folder:", ROOT)

    raw = extract()                                   # 1. Extract
    run_eda(raw)                                      # 2. EDA (on the raw data)
    tables = clean_all(raw)                           # 3. Clean
    run_quality_checks(tables)                        #    stop here if the clean data is bad
    sales, order_totals, customer_orders = build_analysis_tables(tables)   # 4. Transform
    save_processed(tables)
    analysis = run_analysis(tables, sales, order_totals, customer_orders)  # 5. Analyze

    load_plan = build_load_plan(tables)               # 6. Load
    engine = create_database()
    loaded = load_tables(engine, load_plan)
    verify_load(engine, load_plan, loaded)

    sql_results = run_sql_reports(engine)             # 7. SQL reports
    cross_check(sql_results, analysis)                #    SQL must agree with Pandas
    write_project_files(sql_results)                  # 8. Combined .sql file, results and report

    print("\nPIPELINE COMPLETE: raw data extracted, cleaned, loaded into", DB_PATH.name, "and reported.")


if __name__ == "__main__":
    main()
