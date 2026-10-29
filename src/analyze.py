"""Analyze: seven business questions answered with Pandas, with charts and written insights."""
import textwrap

import numpy as np
import pandas as pd

from .plotting import BLUE, INK, THOUSANDS, plt, save_fig
from .state import INSIGHTS, STATS
from .utils import display


def run_analysis(tables, sales, order_totals, customer_orders):
    """Answer the 7 business questions. Returns the numbers the SQL cross-check needs."""
    customers, payments, orders, reviews = tables["customers"], tables["payments"], tables["orders"], tables["reviews"]

    cat_rev = (sales.groupby("category_name_en")
               .agg(revenue=("price", "sum"), orders=("order_id", "nunique"), items_sold=("order_item_id", "count"))
               .sort_values("revenue", ascending=False))
    cat_rev["share_pct"] = (100 * cat_rev["revenue"] / cat_rev["revenue"].sum()).round(2)
    top10 = cat_rev.head(10)
    display(top10.round(2))

    fig, ax = plt.subplots(figsize=(9, 5))
    ordered = top10.iloc[::-1]
    labels = [textwrap.shorten(c.replace("_", " "), 30, placeholder="...") for c in ordered.index]
    ax.barh(labels, ordered["revenue"], color=BLUE, height=0.6)
    ax.xaxis.set_major_formatter(THOUSANDS)
    ax.set_title("Top 10 product categories by revenue")
    ax.set_xlabel("Revenue (R$)")
    ax.grid(axis="y", visible=False)
    for y, value in enumerate(ordered["revenue"]):
        ax.text(value, y, f"  {value / 1000:,.0f}k", va="center", fontsize=9, color=INK)
    save_fig("04_top_categories_revenue.png")

    top5_share = cat_rev["share_pct"].head(5).sum()
    INSIGHTS.append(
        f"'{cat_rev.index[0]}' is the top category: R$ {cat_rev['revenue'].iloc[0]:,.0f} of revenue, "
        f"{cat_rev['share_pct'].iloc[0]}% of all sales. The 5 biggest categories together make up "
        f"{top5_share:.1f}% of revenue, "
        + ("so sales depend on a few categories." if top5_share >= 40 else "so sales are spread across many categories."))

    # ---- Q2. Which month has the highest revenue, and how do sales change over time? ----

    monthly = (sales.groupby("year_month")
               .agg(revenue=("price", "sum"), orders=("order_id", "nunique")).reset_index())
    display(monthly.sort_values("revenue", ascending=False).head(5).round(2))

    fig, ax = plt.subplots()
    x = pd.to_datetime(monthly["year_month"])
    ax.plot(x, monthly["revenue"], color=BLUE, linewidth=2)
    ax.set_title("Monthly revenue")
    ax.yaxis.set_major_formatter(THOUSANDS)
    ax.set_ylabel("Revenue (R$)")
    best = monthly.loc[monthly["revenue"].idxmax()]
    ax.scatter([pd.to_datetime(best["year_month"])], [best["revenue"]], color=BLUE, s=40, zorder=3)
    ax.annotate(f"Highest: {best['year_month']}  (R$ {best['revenue']:,.0f})",
                (pd.to_datetime(best["year_month"]), best["revenue"]), xytext=(-150, -6),
                textcoords="offset points", fontsize=9, color=INK)
    save_fig("05_monthly_revenue.png")

    INSIGHTS.append(
        f"{best['year_month']} had the highest revenue (R$ {best['revenue']:,.0f}), "
        f"{best['revenue'] / monthly['revenue'].mean():.1f} times the average month "
        f"(R$ {monthly['revenue'].mean():,.0f}).")

    # ---- Q3. Which states have the most customers? ----

    state_customers = (customers.groupby("state")["customer_unique_id"].nunique()
                       .sort_values(ascending=False))
    state_share = (100 * state_customers / state_customers.sum()).round(1)
    display(pd.DataFrame({"customers": state_customers, "share_pct": state_share}).head(10))

    top_states = state_customers.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(top_states.index, top_states.values, color=BLUE, height=0.6)
    ax.set_title("Top 10 states by number of customers")
    ax.set_xlabel("Unique customers")
    ax.grid(axis="y", visible=False)
    for y, value in enumerate(top_states.values):
        ax.text(value, y, f"  {value:,}", va="center", fontsize=9, color=INK)
    save_fig("06_customers_by_state.png")

    INSIGHTS.append(
        f"{state_customers.index[0]} has the most customers ({state_customers.iloc[0]:,}, {state_share.iloc[0]}% of all). "
        f"The top 3 states ({', '.join(state_customers.index[:3])}) hold {state_share.head(3).sum():.1f}% of customers.")

    # ---- Q4. How do customers pay? ----

    pay = (payments.groupby("payment_type")
           .agg(total_value=("payment_value", "sum"), orders=("order_id", "nunique"),
                avg_installments=("payment_installments", "mean"))
           .sort_values("total_value", ascending=False))
    pay["share_pct"] = (100 * pay["total_value"] / pay["total_value"].sum()).round(1)
    display(pay.round(2))

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(pay.index.str.replace("_", " "), pay["total_value"], color=BLUE, width=0.55)
    ax.yaxis.set_major_formatter(THOUSANDS)
    ax.set_title("Payment value by payment type")
    ax.set_ylabel("Total paid (R$)")
    ax.grid(axis="x", visible=False)
    for xpos, (value, share) in enumerate(zip(pay["total_value"], pay["share_pct"])):
        ax.text(xpos, value, f"{share}%", ha="center", va="bottom", fontsize=9, color=INK)
    save_fig("07_payment_types.png")

    INSIGHTS.append(
        f"'{pay.index[0]}' is the most used payment method: {pay['share_pct'].iloc[0]}% of all money paid, "
        f"with {pay['avg_installments'].iloc[0]:.1f} installments on average.")

    # ---- Q5. What is the average order value? ----

    aov = order_totals["order_total"].mean()
    median_order = order_totals["order_total"].median()
    print(f"Orders: {len(order_totals):,}")
    print(f"Average order value (items + freight): R$ {aov:,.2f}")
    print(f"Median order value: R$ {median_order:,.2f}")

    by_state_aov = (order_totals.groupby("state")["order_total"].agg(["mean", "count"])
                    .query("count >= 100").sort_values("mean", ascending=False).round(2))
    display(by_state_aov.head(5))

    if aov > 1.1 * median_order:
        aov_note = "a few expensive orders pull the average up, so the typical customer spends less than the average suggests."
    else:
        aov_note = "the two are close, so order values are fairly even."
    INSIGHTS.append(
        f"The average order value is R$ {aov:,.2f} and the median is R$ {median_order:,.2f}: " + aov_note)

    # ---- Q6. Do late deliveries get worse reviews? ----

    delivered = (orders[orders["order_status"] == "delivered"]
                 .merge(reviews[["order_id", "review_score"]], on="order_id"))
    delivered = delivered.dropna(subset=["is_late", "delivery_days"])

    late_pct = 100 * delivered["is_late"].mean()
    score_late = delivered.loc[delivered["is_late"] == 1, "review_score"].mean()
    score_ok = delivered.loc[delivered["is_late"] == 0, "review_score"].mean()
    print(f"Late deliveries: {late_pct:.1f}% | average review: late {score_late:.2f} vs on time {score_ok:.2f}")

    delivered["delivery_bucket"] = pd.cut(delivered["delivery_days"], [0, 7, 14, 21, 30, np.inf],
                                          labels=["0-7", "8-14", "15-21", "22-30", "over 30"])
    by_bucket = delivered.groupby("delivery_bucket", observed=True)["review_score"].agg(["mean", "count"]).round(2)
    display(by_bucket)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(by_bucket.index.astype(str), by_bucket["mean"], color=BLUE, width=0.55)
    ax.set_title("Average review score by delivery time")
    ax.set_xlabel("Days from purchase to delivery")
    ax.set_ylabel("Average review score (1-5)")
    ax.set_ylim(0, 5)
    ax.grid(axis="x", visible=False)
    for xpos, value in enumerate(by_bucket["mean"]):
        ax.text(xpos, value, f"{value:.2f}", ha="center", va="bottom", fontsize=9, color=INK)
    save_fig("08_delivery_vs_review.png")

    delay_verdict = ("slow delivery clearly hurts customer satisfaction." if score_late < score_ok
                     else "late delivery does not lower the average score in this data.")
    INSIGHTS.append(
        f"{late_pct:.1f}% of delivered orders arrived after the estimated date. Late orders score "
        f"{score_late:.2f} on average, against {score_ok:.2f} for on-time orders: " + delay_verdict)
    INSIGHTS.append(
        f"Average review score is {by_bucket['mean'].iloc[0]:.2f} when delivery takes up to 7 days and "
        f"{by_bucket['mean'].iloc[-1]:.2f} when it takes over 30 days.")

    # ---- Q7. How many customers buy again? ----

    segments = customer_orders["segment"].value_counts().reindex(["One-time", "Two orders", "3+ orders"])
    repeat_pct = 100 * (customer_orders["orders"] > 1).mean()
    repeat_revenue_pct = 100 * customer_orders.loc[customer_orders["orders"] > 1, "total_spent"].sum() / customer_orders["total_spent"].sum()
    display(segments.to_frame("customers"))
    top_spenders = customer_orders.sort_values("total_spent", ascending=False).head(5).round(2)
    display(top_spenders)

    repeat_note = ("Most customers buy a single time, so repeat-purchase campaigns are a big growth opportunity."
                   if repeat_pct < 50 else "Most customers come back, which shows strong loyalty.")
    INSIGHTS.append(
        f"{repeat_pct:.1f}% of customers ordered more than once; they bring {repeat_revenue_pct:.1f}% of revenue. " + repeat_note)

    print("\nKEY INSIGHTS")
    for i, insight in enumerate(INSIGHTS, 1):
        print(f"{i}. {insight}")
    STATS["insights"] = list(INSIGHTS)
    return {"cat_rev": cat_rev, "aov": aov}
