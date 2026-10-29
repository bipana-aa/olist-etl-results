"""EDA on the RAW data: size, types, missing values, duplicates, invalid values, outliers, first charts."""
import pandas as pd

from .config import DATE_COLS
from .plotting import BLUE, INK, plt, save_fig
from .state import STATS
from .utils import display


def iqr_outliers(series):
    s = series.dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    upper = q3 + 1.5 * (q3 - q1)
    return int((s > upper).sum()), round(float(upper), 2), round(float(s.max()), 2)


def formatting_problems(series):
    s = series.dropna().astype(str)
    return {"extra spaces": int((s != s.str.strip()).sum()),
            "not lower-case": int((s != s.str.lower()).sum()),
            "has accents": int(s.str.contains(r"[^\x00-\x7F]").sum())}


def explore_basics(raw):
    """2.1 Size, columns, data types, samples, summary statistics, unique counts."""
    overview = pd.DataFrame({
        "rows":    {k: v.shape[0] for k, v in raw.items()},
        "columns": {k: v.shape[1] for k, v in raw.items()},
        "memory_mb": {k: round(v.memory_usage(deep=True).sum() / 1e6, 1) for k, v in raw.items()},
    })
    display(overview)
    total_cols = int(overview["columns"].sum())
    print(f"\n{len(raw)} tables, {total_cols} columns in total, {overview['rows'].sum():,} rows in total")
    STATS["raw_shapes"] = {k: (int(v.shape[0]), int(v.shape[1])) for k, v in raw.items()}
    STATS["total_columns"] = total_cols

    # Column names and data types of every table
    for name, d in raw.items():
        cols = ", ".join(f"{c} ({str(t)})" for c, t in d.dtypes.items())
        print(f"\n{name}  {d.shape}\n  {cols}")

    # Sample records
    for name in ["orders", "order_items", "customers", "products", "payments", "reviews"]:
        print(f"\n--- sample records: {name}")
        display(raw[name].head(3))

    # Summary statistics of the numeric columns
    display(raw["order_items"][["price", "freight_value"]].describe().round(2))
    display(raw["payments"][["payment_installments", "payment_value"]].describe().round(2))
    display(raw["products"].describe().round(1))
    display(raw["reviews"][["review_score"]].describe().round(2))

    # Number of unique values in the important columns
    unique_counts = pd.Series({
        "orders.order_id":                      raw["orders"]["order_id"].nunique(),
        "orders.order_status":                  raw["orders"]["order_status"].nunique(),
        "customers.customer_id":                raw["customers"]["customer_id"].nunique(),
        "customers.customer_unique_id":         raw["customers"]["customer_unique_id"].nunique(),
        "customers.customer_state":             raw["customers"]["customer_state"].nunique(),
        "customers.customer_city":              raw["customers"]["customer_city"].nunique(),
        "products.product_id":                  raw["products"]["product_id"].nunique(),
        "products.product_category_name":       raw["products"]["product_category_name"].nunique(),
        "sellers.seller_id":                    raw["sellers"]["seller_id"].nunique(),
        "order_items.product_id":               raw["order_items"]["product_id"].nunique(),
        "payments.payment_type":                raw["payments"]["payment_type"].nunique(),
        "reviews.review_score":                 raw["reviews"]["review_score"].nunique(),
    }, name="unique_values")
    display(unique_counts.to_frame())
    STATS["unique_counts"] = unique_counts.astype(int).to_dict()


def check_data_quality(raw):
    """2.2 Missing values, duplicates, wrong types, invalid values, outliers, odd categories."""
    # ---- Missing values ----
    rows = []
    for name, d in raw.items():
        nulls = d.isna().sum()
        for col, count in nulls[nulls > 0].items():
            rows.append((name, col, int(count), round(100 * count / len(d), 2)))
    null_report = pd.DataFrame(rows, columns=["table", "column", "missing", "missing_pct"]) \
                    .sort_values("missing", ascending=False).reset_index(drop=True)
    display(null_report)
    STATS["null_report"] = null_report

    # ---- Duplicates ----
    full_row_dups = {name: int(d.duplicated().sum()) for name, d in raw.items()}
    key_dups = {
        "orders: repeated order_id":                         int(raw["orders"]["order_id"].duplicated().sum()),
        "customers: repeated customer_id":                   int(raw["customers"]["customer_id"].duplicated().sum()),
        "products: repeated product_id":                     int(raw["products"]["product_id"].duplicated().sum()),
        "sellers: repeated seller_id":                       int(raw["sellers"]["seller_id"].duplicated().sum()),
        "order_items: repeated (order_id, order_item_id)":    int(raw["order_items"].duplicated(["order_id", "order_item_id"]).sum()),
        "reviews: repeated review_id":                       int(raw["reviews"]["review_id"].duplicated().sum()),
        "reviews: repeated (review_id, order_id)":           int(raw["reviews"].duplicated(["review_id", "order_id"]).sum()),
    }
    print("Fully duplicated rows per table:")
    display(pd.Series(full_row_dups, name="duplicate_rows").to_frame())
    print("Duplicated keys:")
    display(pd.Series(key_dups, name="duplicates").to_frame())
    STATS["full_row_dups"], STATS["key_dups"] = full_row_dups, key_dups

    # ---- Incorrect data types: date columns are read as plain text ----
    wrong_types = pd.DataFrame(
        [(t, c, str(raw[t][c].dtype)) for t, cols in DATE_COLS.items() for c in cols],
        columns=["table", "column", "current_dtype"])
    wrong_types["should_be"] = "datetime"
    display(wrong_types)
    STATS["wrong_types"] = len(wrong_types)

    # ---- Invalid or inconsistent values ----
    o = raw["orders"]
    purchase = pd.to_datetime(o["order_purchase_timestamp"], errors="coerce")
    delivered = pd.to_datetime(o["order_delivered_customer_date"], errors="coerce")

    invalid = {
        "payments: payment_value = 0":                      int((raw["payments"]["payment_value"] == 0).sum()),
        "payments: payment_type = 'not_defined'":           int((raw["payments"]["payment_type"] == "not_defined").sum()),
        "payments: payment_installments = 0":               int((raw["payments"]["payment_installments"] == 0).sum()),
        "order_items: price <= 0":                          int((raw["order_items"]["price"] <= 0).sum()),
        "order_items: freight_value < 0":                   int((raw["order_items"]["freight_value"] < 0).sum()),
        "products: weight_g = 0":                           int((raw["products"]["product_weight_g"] == 0).sum()),
        "products: missing category name":                  int(raw["products"]["product_category_name"].isna().sum()),
        "reviews: review_score outside 1 to 5":             int((~raw["reviews"]["review_score"].between(1, 5)).sum()),
        "orders: 'delivered' but no delivery date":         int(((o["order_status"] == "delivered") & delivered.isna()).sum()),
        "orders: delivered before purchase":                int((delivered < purchase).sum()),
        "orders: not delivered but has a delivery date":    int(((o["order_status"] != "delivered") & delivered.notna()).sum()),
    }
    invalid_df = pd.Series(invalid, name="rows").to_frame()
    display(invalid_df)
    STATS["invalid"] = invalid

    # ---- Outliers (IQR rule: beyond Q3 + 1.5 x IQR) ----
    delivery_days_raw = (delivered - purchase).dt.total_seconds() / 86400
    outlier_rows = []
    for label, series in [("order_items.price", raw["order_items"]["price"]),
                          ("order_items.freight_value", raw["order_items"]["freight_value"]),
                          ("payments.payment_value", raw["payments"]["payment_value"]),
                          ("delivery time (days)", delivery_days_raw)]:
        n_out, upper, biggest = iqr_outliers(series)
        outlier_rows.append((label, n_out, upper, biggest))
    outliers = pd.DataFrame(outlier_rows, columns=["column", "outliers", "upper_limit", "max_value"])
    display(outliers)
    STATS["outliers"] = outliers

    # ---- Unexpected categories and inconsistent formatting ----
    print("Order status:");   display(raw["orders"]["order_status"].value_counts().to_frame())
    print("Payment type:");   display(raw["payments"]["payment_type"].value_counts().to_frame())

    translated = set(raw["category_translation"]["product_category_name"])
    untranslated = sorted(set(raw["products"]["product_category_name"].dropna()) - translated)
    print(f"Product categories with no English translation: {len(untranslated)} -> {untranslated}")

    formatting = pd.DataFrame({
        "customers.city": formatting_problems(raw["customers"]["customer_city"]),
        "sellers.city": formatting_problems(raw["sellers"]["seller_city"]),
        "geolocation.city": formatting_problems(raw["geolocation"]["geolocation_city"]),
    }).T
    display(formatting)
    STATS["untranslated"] = untranslated
    STATS["formatting"] = formatting


def explore_business(raw):
    """2.3 First look at the business with groupby, filters and three charts."""
    items_raw = raw["order_items"]

    # groupby + agg + sort_values: best-selling products by revenue
    by_product = (items_raw.groupby("product_id")
                  .agg(units_sold=("order_id", "count"), revenue=("price", "sum"))
                  .sort_values("revenue", ascending=False))
    print("Top 5 products by revenue (head / iloc):")
    display(by_product.iloc[:5].round(2))

    # loc[] + filtering: expensive items
    expensive = items_raw.loc[items_raw["price"] > 1000, ["order_id", "product_id", "price"]]
    print(f"Items priced above R$ 1,000: {len(expensive):,} ({100 * len(expensive) / len(items_raw):.2f}% of all items)")

    # calculated column: total value of an item line = price + freight
    items_calc = items_raw.assign(total_price=items_raw["price"] + items_raw["freight_value"])
    print("Average item total (price + freight): R$", round(items_calc["total_price"].mean(), 2))

    # value_counts: customers by state
    print("\nCustomers by state (top 5):")
    display(raw["customers"]["customer_state"].value_counts().head(5).to_frame())

    # Chart 1: orders per month (trend over time)
    purchase_ts_raw = pd.to_datetime(raw["orders"]["order_purchase_timestamp"], errors="coerce")
    STATS["first_purchase_date"] = purchase_ts_raw.min().date()
    STATS["last_purchase_date"] = purchase_ts_raw.max().date()
    orders_per_month = purchase_ts_raw.dt.to_period("M").value_counts().sort_index()

    fig, ax = plt.subplots()
    ax.plot(orders_per_month.index.to_timestamp(), orders_per_month.values, color=BLUE, linewidth=2)
    ax.set_title("Orders per month")
    ax.set_ylabel("Number of orders")
    peak = orders_per_month.idxmax()
    ax.annotate(f"Peak: {peak}  ({orders_per_month.max():,} orders)",
                (peak.to_timestamp(), orders_per_month.max()), xytext=(8, -4),
                textcoords="offset points", color=INK, fontsize=9)
    save_fig("01_orders_per_month.png")
    STATS["eda_peak_orders_month"] = (str(peak), int(orders_per_month.max()))

    # Chart 2: review scores
    score_counts = raw["reviews"]["review_score"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(score_counts.index.astype(str), score_counts.values, color=BLUE, width=0.6)
    ax.set_title("Review score distribution")
    ax.set_xlabel("Review score (1 = worst, 5 = best)")
    ax.set_ylabel("Number of reviews")
    ax.grid(axis="x", visible=False)
    for x, v in zip(score_counts.index.astype(str), score_counts.values):
        ax.text(x, v, f"{v:,}", ha="center", va="bottom", fontsize=9, color=INK)
    save_fig("02_review_scores.png")
    STATS["eda_five_star_pct"] = round(100 * (raw["reviews"]["review_score"] == 5).mean(), 1)

    # Chart 3: item prices (long right tail, so the chart stops at the 99th percentile)
    cap = items_raw["price"].quantile(0.99)
    fig, ax = plt.subplots()
    ax.hist(items_raw["price"].clip(upper=cap), bins=40, color=BLUE, edgecolor="white", linewidth=0.5)
    ax.set_title(f"Item price distribution (capped at the 99th percentile, R$ {cap:,.0f})")
    ax.set_xlabel("Price (R$)")
    ax.set_ylabel("Number of items")
    ax.grid(axis="x", visible=False)
    save_fig("03_price_distribution.png")
    STATS["eda_price_median"] = round(float(items_raw["price"].median()), 2)


def run_eda(raw):
    """Run all EDA steps on the raw tables (nothing is changed, results go to STATS and docs/figures)."""
    explore_basics(raw)
    check_data_quality(raw)
    explore_business(raw)
