"""Clean: fix every problem found in the EDA, one function per group of tables. Each step is logged with its reason."""
import numpy as np
import pandas as pd

from .config import DATE_RENAME
from .state import STATS
from .utils import clean_text, display, log


def most_common(frame, column):
    counts = frame.groupby(["zip_code_prefix", column]).size().reset_index(name="n")
    return (counts.sort_values("n").drop_duplicates("zip_code_prefix", keep="last")
            .set_index("zip_code_prefix")[column])


def keep_valid(frame, column, valid_ids, table, parent):
    ok = frame[column].isin(valid_ids)
    log(table, f"orphan rows removed ({column} not found in {parent})", (~ok).sum(),
        "a foreign key cannot point to a missing parent")
    return frame[ok]


def clean_orders(raw):
    """Orders: dates to datetime, status text, duplicates, new delivery columns."""
    orders = raw["orders"].copy()

    # 1) Text -> datetime, and clearer column names
    for col in DATE_RENAME:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")
    orders = orders.rename(columns=DATE_RENAME)
    log("orders", "date columns converted from text to datetime", len(DATE_RENAME),
        "text dates cannot be sorted, grouped by month or subtracted")

    # 2) Standardise status text
    orders["order_status"] = orders["order_status"].str.strip().str.lower()

    # 3) Duplicate orders
    n = orders.duplicated("order_id").sum()
    orders = orders.drop_duplicates("order_id")
    log("orders", "duplicate order_id rows removed", n, "order_id is the primary key")

    # 4) An order with no purchase time cannot be analysed
    n = orders["purchase_ts"].isna().sum()
    orders = orders.dropna(subset=["purchase_ts"])
    log("orders", "rows without purchase time removed", n, "purchase time is needed for every time-based report")

    # 5) Delivered before it was bought is impossible: blank the bad delivery date
    bad = orders["delivered_customer_ts"] < orders["purchase_ts"]
    orders.loc[bad, "delivered_customer_ts"] = pd.NaT
    log("orders", "impossible delivery dates set to missing", bad.sum(), "delivery cannot happen before purchase")

    # 6) New columns for time analysis and delivery performance
    orders["purchase_year"] = orders["purchase_ts"].dt.year
    orders["purchase_month"] = orders["purchase_ts"].dt.month
    orders["delivery_days"] = ((orders["delivered_customer_ts"] - orders["purchase_ts"])
                               .dt.total_seconds() / 86400).round(2)
    orders["delay_days"] = (orders["delivered_customer_ts"].dt.normalize()
                            - orders["estimated_delivery_date"].dt.normalize()).dt.days
    orders["is_late"] = np.where(orders["delay_days"].isna(), np.nan, (orders["delay_days"] > 0).astype(float))
    log("orders", "new columns: purchase_year, purchase_month, delivery_days, delay_days, is_late",
        len(orders), "needed to answer questions about monthly trends and late deliveries")
    print(f"\nOrders still without a delivery date (not delivered yet or canceled): {orders['delivered_customer_ts'].isna().sum():,} (kept as missing: this is real information)")
    return orders


def clean_customers_sellers(raw):
    """Customers and sellers: duplicates and city/state text formatting."""
    customers = raw["customers"].rename(columns={
        "customer_zip_code_prefix": "zip_code_prefix", "customer_city": "city", "customer_state": "state"}).copy()
    n = customers.duplicated("customer_id").sum()
    customers = customers.drop_duplicates("customer_id")
    log("customers", "duplicate customer_id rows removed", n, "customer_id is the primary key")
    changed = (customers["city"] != clean_text(customers["city"])).sum()
    customers["city"] = clean_text(customers["city"])
    customers["state"] = customers["state"].str.strip().str.upper()
    log("customers", "city names standardised (spaces, accents, capital letters)", changed,
        "'sao paulo', 'São Paulo' and 'SAO PAULO ' must be one group in reports")

    sellers = raw["sellers"].rename(columns={
        "seller_zip_code_prefix": "zip_code_prefix", "seller_city": "city", "seller_state": "state"}).copy()
    n = sellers.duplicated("seller_id").sum()
    sellers = sellers.drop_duplicates("seller_id")
    log("sellers", "duplicate seller_id rows removed", n, "seller_id is the primary key")
    changed = (sellers["city"] != clean_text(sellers["city"])).sum()
    sellers["city"] = clean_text(sellers["city"])
    sellers["state"] = sellers["state"].str.strip().str.upper()
    log("sellers", "city names standardised (spaces, accents, capital letters)", changed,
        "same reason as customer cities")
    return customers, sellers


def clean_products_categories(raw):
    """Products and categories: missing values, wrong spellings, English names."""
    products = raw["products"].rename(columns={
        "product_category_name": "category_name",
        "product_name_lenght": "name_length",              # the original column name has a spelling mistake
        "product_description_lenght": "description_length",
        "product_photos_qty": "photos_qty",
        "product_weight_g": "weight_g",
        "product_length_cm": "length_cm",
        "product_height_cm": "height_cm",
        "product_width_cm": "width_cm",
    }).copy()

    n = products.duplicated("product_id").sum()
    products = products.drop_duplicates("product_id")
    log("products", "duplicate product_id rows removed", n, "product_id is the primary key")

    # Missing category -> 'unknown' (keeps the product and its sales in the reports)
    products["category_name"] = products["category_name"].str.strip().str.lower()
    n = products["category_name"].isna().sum()
    products["category_name"] = products["category_name"].fillna("unknown")
    log("products", "missing category set to 'unknown'", n, "removing them would delete real sales")

    # Weight of 0 g is impossible -> treat as missing
    n = (products["weight_g"] == 0).sum()
    products.loc[products["weight_g"] == 0, "weight_g"] = np.nan
    log("products", "weight of 0 g treated as missing", n, "a product cannot weigh 0 g")

    # Fill missing numeric details with the median (the middle value is not affected by extremes)
    for col in ["name_length", "description_length", "photos_qty", "weight_g", "length_cm", "height_cm", "width_cm"]:
        n = products[col].isna().sum()
        if n:
            products[col] = products[col].fillna(products[col].median())
            log("products", f"missing {col} filled with the median", n, "keeps the row; median is safe against outliers")
    for col in ["name_length", "description_length", "photos_qty"]:
        products[col] = products[col].round().astype(int)

    # Category table: Portuguese name -> English name
    categories = raw["category_translation"].rename(columns={"product_category_name": "category_name",
                                                             "product_category_name_english": "category_name_en"}).copy()
    categories["category_name"] = categories["category_name"].str.strip().str.lower()
    categories["category_name_en"] = categories["category_name_en"].str.strip().str.lower()

    used = set(products["category_name"].unique()) | {"unknown"}
    extra = sorted(used - set(categories["category_name"]))
    extra_df = pd.DataFrame({"category_name": extra,
                             "category_name_en": [c.replace("_", " ") for c in extra]})
    categories = pd.concat([categories, extra_df], ignore_index=True).drop_duplicates("category_name")
    log("product_categories", "categories without an English name added (underscores -> spaces)", len(extra),
        f"these categories had no translation: {extra}")
    return products, categories


def clean_items_payments_reviews(raw):
    """Order items, payments and reviews: types, duplicates, invalid values."""
    items = raw["order_items"].rename(columns={"shipping_limit_date": "shipping_limit_ts"}).copy()
    items["shipping_limit_ts"] = pd.to_datetime(items["shipping_limit_ts"], errors="coerce")
    log("order_items", "shipping_limit_ts converted to datetime", len(items), "text dates cannot be used in calculations")

    n = items.duplicated(["order_id", "order_item_id"]).sum()
    items = items.drop_duplicates(["order_id", "order_item_id"])
    log("order_items", "duplicate (order_id, order_item_id) rows removed", n, "this pair is the primary key")

    n = ((items["price"] < 0) | (items["freight_value"] < 0)).sum()
    items = items[(items["price"] >= 0) & (items["freight_value"] >= 0)]
    log("order_items", "rows with negative price or freight removed", n, "money values cannot be negative")

    # Outliers: very expensive items are REAL purchases, so we keep them
    q1, q3 = items["price"].quantile([0.25, 0.75])
    n = (items["price"] > q3 + 1.5 * (q3 - q1)).sum()
    log("order_items", "price outliers kept (checked, not removed)", n,
        "high prices are genuine purchases (for example furniture, appliances), not errors")

    items["total_price"] = (items["price"] + items["freight_value"]).round(2)
    log("order_items", "new column total_price = price + freight_value", len(items), "needed for order value reports")

    # ---------------- payments ----------------
    payments = raw["payments"].copy()
    payments["payment_type"] = payments["payment_type"].str.strip().str.lower()
    n = (payments["payment_type"] == "not_defined").sum()
    payments = payments[payments["payment_type"] != "not_defined"]
    log("payments", "rows with payment_type 'not_defined' removed", n, "the payment method is unknown, so the row carries no information")
    n = (payments["payment_installments"] == 0).sum()
    payments.loc[payments["payment_installments"] == 0, "payment_installments"] = 1
    log("payments", "installments of 0 changed to 1", n, "a payment has at least 1 installment")
    n = payments.duplicated(["order_id", "payment_sequential"]).sum()
    payments = payments.drop_duplicates(["order_id", "payment_sequential"])
    log("payments", "duplicate (order_id, payment_sequential) rows removed", n, "this pair is the primary key")

    # ---------------- reviews ----------------
    reviews = raw["reviews"].rename(columns={
        "review_comment_title": "comment_title", "review_comment_message": "comment_message",
        "review_creation_date": "creation_date", "review_answer_timestamp": "answer_ts"}).copy()
    reviews["creation_date"] = pd.to_datetime(reviews["creation_date"], errors="coerce")
    reviews["answer_ts"] = pd.to_datetime(reviews["answer_ts"], errors="coerce")
    log("reviews", "date columns converted to datetime", 2, "text dates cannot be used in calculations")

    n = (~reviews["review_score"].between(1, 5)).sum()
    reviews = reviews[reviews["review_score"].between(1, 5)]
    log("reviews", "rows with review_score outside 1 to 5 removed", n, "scores must be 1 to 5")

    n = reviews.duplicated(["review_id", "order_id"]).sum()
    reviews = reviews.sort_values("answer_ts").drop_duplicates(["review_id", "order_id"], keep="last")
    log("reviews", "duplicate (review_id, order_id) rows removed (latest answer kept)", n, "the same review was stored more than once")
    # Empty comments are normal (most people only give a score), so they stay NULL.
    return items, payments, reviews


def clean_geolocation(raw):
    """Geolocation: from about 1 million rows to one averaged row per zip prefix."""
    geo = raw["geolocation"].rename(columns={
        "geolocation_zip_code_prefix": "zip_code_prefix", "geolocation_lat": "latitude",
        "geolocation_lng": "longitude", "geolocation_city": "city", "geolocation_state": "state"}).copy()
    rows_before = len(geo)

    n = geo.duplicated().sum()
    geo = geo.drop_duplicates()
    log("geolocation", "fully duplicated rows removed", n, "identical rows add nothing")

    inside_brazil = geo["latitude"].between(-34, 6) & geo["longitude"].between(-74, -34)
    log("geolocation", "points outside Brazil removed", (~inside_brazil).sum(), "wrong coordinates are outliers")
    geo = geo[inside_brazil]

    geo["city"] = clean_text(geo["city"])
    geo["state"] = geo["state"].str.strip().str.upper()

    geolocation = (geo.groupby("zip_code_prefix")
                   .agg(latitude=("latitude", "mean"), longitude=("longitude", "mean")).round(6))
    geolocation["city"] = most_common(geo, "city")
    geolocation["state"] = most_common(geo, "state")
    geolocation = geolocation.reset_index()
    log("geolocation", f"{rows_before:,} raw rows reduced to one row per zip prefix", len(geolocation),
        "one averaged coordinate per zip code is enough for maps and joins")
    return geolocation


def remove_orphans(orders, customers, products, sellers, items, payments, reviews):
    """Referential integrity: remove child rows whose parent row does not exist."""
    orders = keep_valid(orders, "customer_id", customers["customer_id"], "orders", "customers")
    items = keep_valid(items, "order_id", orders["order_id"], "order_items", "orders")
    items = keep_valid(items, "product_id", products["product_id"], "order_items", "products")
    items = keep_valid(items, "seller_id", sellers["seller_id"], "order_items", "sellers")
    payments = keep_valid(payments, "order_id", orders["order_id"], "payments", "orders")
    reviews = keep_valid(reviews, "order_id", orders["order_id"], "reviews", "orders")
    return orders, items, payments, reviews


def record_clean_shapes(orders, customers, sellers, products, categories, items, payments, reviews, geolocation):
    """Store and show the number of rows left in every clean table."""
    STATS["clean_shapes"] = {"orders": len(orders), "customers": len(customers), "sellers": len(sellers),
                             "products": len(products), "product_categories": len(categories),
                             "order_items": len(items), "order_payments": len(payments),
                             "order_reviews": len(reviews), "geolocation": len(geolocation)}
    display(pd.Series(STATS["clean_shapes"], name="rows after cleaning").to_frame())


def clean_all(raw):
    """Run every cleaning step and return the clean tables as a dictionary."""
    orders = clean_orders(raw)
    customers, sellers = clean_customers_sellers(raw)
    products, categories = clean_products_categories(raw)
    items, payments, reviews = clean_items_payments_reviews(raw)
    geolocation = clean_geolocation(raw)

    orders, items, payments, reviews = remove_orphans(
        orders, customers, products, sellers, items, payments, reviews)
    record_clean_shapes(orders, customers, sellers, products, categories, items, payments, reviews, geolocation)

    return {"orders": orders, "customers": customers, "sellers": sellers, "products": products,
            "categories": categories, "items": items, "payments": payments, "reviews": reviews,
            "geolocation": geolocation}
