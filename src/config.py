"""Folder paths and the fixed lists the pipeline needs (file names, date columns)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent      # the project folder
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
FIG_DIR = ROOT / "docs" / "figures"
OUT_DIR = ROOT / "outputs" / "sql_reports"
DB_PATH = ROOT / "database" / "olist.db"
SQL_DIR = ROOT / "sql"
DOCS_DIR = ROOT / "docs"

# The 9 raw CSV files
FILES = {
    "orders":               "olist_orders_dataset.csv",
    "customers":            "olist_customers_dataset.csv",
    "order_items":          "olist_order_items_dataset.csv",
    "payments":             "olist_order_payments_dataset.csv",
    "reviews":              "olist_order_reviews_dataset.csv",
    "products":             "olist_products_dataset.csv",
    "sellers":              "olist_sellers_dataset.csv",
    "geolocation":          "olist_geolocation_dataset.csv",
    "category_translation":  "product_category_name_translation.csv",
}

# Date columns that are stored as text in the raw data
DATE_COLS = {
    "orders": ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
               "order_delivered_customer_date", "order_estimated_delivery_date"],
    "order_items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}

# Date columns of the orders table -> clearer names
DATE_RENAME = {
    "order_purchase_timestamp":       "purchase_ts",
    "order_approved_at":              "approved_ts",
    "order_delivered_carrier_date":   "delivered_carrier_ts",
    "order_delivered_customer_date":  "delivered_customer_ts",
    "order_estimated_delivery_date":  "estimated_delivery_date",
}


def ensure_dirs():
    """Create the output folders if they do not exist yet."""
    for folder in (PROCESSED_DIR, FIG_DIR, OUT_DIR, DB_PATH.parent):
        folder.mkdir(parents=True, exist_ok=True)
