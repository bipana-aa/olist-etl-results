"""Quality checks on the clean data: the pipeline stops here if any check fails."""
import pandas as pd

from .state import STATS
from .utils import display


def run_quality_checks(tables):
    """Run the automatic checks on the clean tables. Raises AssertionError if one fails."""
    orders, customers, products, sellers = tables["orders"], tables["customers"], tables["products"], tables["sellers"]
    items, payments, reviews, categories = tables["items"], tables["payments"], tables["reviews"], tables["categories"]

    checks = {
        "orders: order_id is unique":                      orders["order_id"].is_unique,
        "customers: customer_id is unique":                customers["customer_id"].is_unique,
        "products: product_id is unique":                  products["product_id"].is_unique,
        "sellers: seller_id is unique":                    sellers["seller_id"].is_unique,
        "order_items: (order_id, order_item_id) is unique": not items.duplicated(["order_id", "order_item_id"]).any(),
        "order_reviews: (review_id, order_id) is unique":  not reviews.duplicated(["review_id", "order_id"]).any(),
        "no missing purchase time":                        orders["purchase_ts"].notna().all(),
        "prices are not negative":                         (items["price"] >= 0).all(),
        "review scores are 1 to 5":                        reviews["review_score"].between(1, 5).all(),
        "every item has a product category":               products["category_name"].notna().all(),
        "every product category has an English name":      products["category_name"].isin(categories["category_name"]).all(),
        "every order has a customer":                      orders["customer_id"].isin(customers["customer_id"]).all(),
        "tables are not empty":                            all(len(t) > 0 for t in (orders, customers, items, products, sellers, payments, reviews)),
    }
    result = pd.Series(checks, name="passed").to_frame()
    display(result)
    failed = [name for name, ok in checks.items() if not ok]
    assert not failed, f"Data quality checks failed: {failed}"
    STATS["quality_checks"] = len(checks)
    print(f"\nAll {len(checks)} quality checks passed.")
