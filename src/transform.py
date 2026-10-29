"""Transform: build the analysis tables (sales, order_totals, customer_orders) and save the clean tables."""
import numpy as np
import pandas as pd

from .config import PROCESSED_DIR
from .utils import display


def build_analysis_tables(tables):
    """Build `sales`, `order_totals` and `customer_orders` from the clean tables."""
    items, orders, products, categories, customers = (tables["items"], tables["orders"], tables["products"],
                                                      tables["categories"], tables["customers"])

    sales = (items
             .merge(orders[["order_id", "customer_id", "order_status", "purchase_ts"]], on="order_id")
             .merge(products[["product_id", "category_name"]], on="product_id")
             .merge(categories, on="category_name", how="left")
             .merge(customers[["customer_id", "customer_unique_id", "state"]], on="customer_id"))
    sales = sales[~sales["order_status"].isin(["canceled", "unavailable"])].copy()
    sales["year_month"] = sales["purchase_ts"].dt.to_period("M").astype(str)
    sales["price_band"] = pd.cut(sales["price"], [0, 50, 100, 200, np.inf],
                                 labels=["under 50", "50 to 100", "100 to 200", "over 200"], right=False)

    order_totals = (sales.groupby("order_id")
                    .agg(order_total=("total_price", "sum"), items=("order_item_id", "count"),
                         customer_unique_id=("customer_unique_id", "first"), state=("state", "first"))
                    .reset_index())

    customer_orders = (order_totals.groupby("customer_unique_id")
                       .agg(orders=("order_id", "nunique"), total_spent=("order_total", "sum")).reset_index())
    customer_orders["segment"] = pd.cut(customer_orders["orders"], [0, 1, 2, np.inf],
                                        labels=["One-time", "Two orders", "3+ orders"])

    print(f"sales: {len(sales):,} rows | order_totals: {len(order_totals):,} rows | customer_orders: {len(customer_orders):,} rows")
    display(sales.head(3))
    return sales, order_totals, customer_orders


def save_processed(tables):
    """Write the clean tables to data/processed/ as CSV files."""
    orders, customers, sellers, products = tables["orders"], tables["customers"], tables["sellers"], tables["products"]
    categories, items, payments = tables["categories"], tables["items"], tables["payments"]
    reviews, geolocation = tables["reviews"], tables["geolocation"]

    # Save the cleaned tables (processed layer)
    for name, frame in {"orders": orders, "customers": customers, "sellers": sellers, "products": products,
                        "product_categories": categories, "order_items": items, "order_payments": payments,
                        "order_reviews": reviews, "geolocation": geolocation}.items():
        frame.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)
    print("Cleaned tables saved in", PROCESSED_DIR)
