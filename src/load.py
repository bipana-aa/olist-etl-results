"""Load: create the SQLite database from sql/schema.sql and load the clean tables (parents before children)."""
import sqlite3

import pandas as pd
from sqlalchemy import create_engine, event, text

from .config import DB_PATH, SQL_DIR
from .state import STATS
from .utils import display


def db_ready(frame, ts_cols=(), int_cols=()):
    """Turn a DataFrame into plain Python values SQLite accepts: text timestamps, None for missing."""
    out = frame.copy()
    for col in ts_cols:
        out[col] = out[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    for col in int_cols:
        out[col] = out[col].astype("Int64")
    out = out.astype(object)
    return out.where(out.notna(), None)


def build_load_plan(tables):
    """List (table name, DataFrame ready for SQLite), parent tables first."""
    orders, customers, sellers, products = tables["orders"], tables["customers"], tables["sellers"], tables["products"]
    categories, items, payments = tables["categories"], tables["items"], tables["payments"]
    reviews, geolocation = tables["reviews"], tables["geolocation"]

    load_plan = [   # parent tables first, child tables after
        ("geolocation",        db_ready(geolocation[["zip_code_prefix", "latitude", "longitude", "city", "state"]])),
        ("customers",          db_ready(customers[["customer_id", "customer_unique_id", "zip_code_prefix", "city", "state"]])),
        ("sellers",            db_ready(sellers[["seller_id", "zip_code_prefix", "city", "state"]])),
        ("product_categories", db_ready(categories[["category_name", "category_name_en"]])),
        ("products",           db_ready(products[["product_id", "category_name", "name_length", "description_length",
                                                  "photos_qty", "weight_g", "length_cm", "height_cm", "width_cm"]])),
        ("orders",             db_ready(orders[["order_id", "customer_id", "order_status", "purchase_ts", "approved_ts",
                                                "delivered_carrier_ts", "delivered_customer_ts", "estimated_delivery_date",
                                                "purchase_year", "purchase_month", "delivery_days", "delay_days", "is_late"]],
                                        ts_cols=["purchase_ts", "approved_ts", "delivered_carrier_ts",
                                                 "delivered_customer_ts", "estimated_delivery_date"],
                                        int_cols=["is_late"])),
        ("order_items",        db_ready(items[["order_id", "order_item_id", "product_id", "seller_id",
                                               "shipping_limit_ts", "price", "freight_value", "total_price"]],
                                        ts_cols=["shipping_limit_ts"])),
        ("order_payments",     db_ready(payments[["order_id", "payment_sequential", "payment_type",
                                                 "payment_installments", "payment_value"]])),
        ("order_reviews",      db_ready(reviews[["review_id", "order_id", "review_score", "comment_title", "comment_message",
                                                 "creation_date", "answer_ts"]],
                                        ts_cols=["creation_date", "answer_ts"])),
    ]
    print("Prepared", len(load_plan), "tables for loading.")
    return load_plan


def create_database(db_path=DB_PATH):
    """Delete the old database and create all tables from sql/schema.sql. Returns the SQLAlchemy engine."""
    # Database connection (SQLAlchemy) with foreign keys switched on for every connection
    db_path.unlink(missing_ok=True)                                 # start fresh: the load is repeatable
    engine = create_engine(f"sqlite:///{db_path}")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys = ON")

    # Create the tables from the SQL file
    schema_sql = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as con:
        con.executescript(schema_sql)
    print("Tables created from sql/schema.sql")
    return engine


def load_tables(engine, load_plan):
    """Write every DataFrame into its table. Returns {table: rows loaded}."""
    # Load: DataFrame -> table
    loaded = {}
    for table, frame in load_plan:
        frame.to_sql(table, engine, if_exists="append", index=False, chunksize=5000)
        loaded[table] = len(frame)
        print(f"  loaded {table:20} {len(frame):>9,} rows")
    STATS["loaded_rows"] = loaded
    return loaded


def verify_load(engine, load_plan, loaded, db_path=DB_PATH):
    """Check row counts, foreign keys and database integrity. Raises AssertionError on any problem."""
    # Verify the load: row counts, foreign keys, database integrity
    with engine.connect() as con:
        in_db = {t: con.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() for t, _ in load_plan}
        fk_problems = con.execute(text("PRAGMA foreign_key_check")).fetchall()
        integrity = con.execute(text("PRAGMA integrity_check")).scalar()

    verify = pd.DataFrame({"dataframe_rows": loaded, "database_rows": in_db})
    verify["match"] = verify["dataframe_rows"] == verify["database_rows"]
    display(verify)
    assert verify["match"].all(), "Row counts do not match after loading"
    assert not fk_problems, f"Foreign key problems: {fk_problems[:5]}"
    assert integrity == "ok", integrity
    print(f"Load verified: all row counts match, 0 foreign key problems, integrity check = '{integrity}'.")
    STATS["db_size_mb"] = round(db_path.stat().st_size / 1e6, 1)
