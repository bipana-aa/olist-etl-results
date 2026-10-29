# SQL Reports: queries and results

Database: `database/olist.db` (SQLite). 11 reporting queries.


## 01_revenue_by_category

**Question:** Which product categories generate the most revenue?

```sql
SELECT pc.category_name_en                       AS category,
       COUNT(DISTINCT oi.order_id)               AS orders,
       COUNT(*)                                  AS items_sold,
       ROUND(SUM(oi.price), 2)                   AS revenue,
       ROUND(100.0 * SUM(oi.price) /
             (SELECT SUM(i2.price)
                FROM order_items i2
                JOIN orders o2 ON o2.order_id = i2.order_id
               WHERE o2.order_status NOT IN ('canceled', 'unavailable')), 2) AS pct_of_total
FROM order_items oi
JOIN orders o              ON o.order_id = oi.order_id
JOIN products p            ON p.product_id = oi.product_id
JOIN product_categories pc ON pc.category_name = p.category_name
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY pc.category_name_en
ORDER BY revenue DESC
LIMIT 15;
```

**Result:**

| category | orders | items_sold | revenue | pct_of_total |
|---|---|---|---|---|
| health_beauty | 8800 | 9634 | 1,255,695.13 | 9.31 |
| watches_gifts | 5604 | 5970 | 1,198,185.21 | 8.88 |
| bed_bath_table | 9399 | 11097 | 1,035,964.06 | 7.68 |
| sports_leisure | 7673 | 8590 | 979,740.92 | 7.26 |
| computers_accessories | 6654 | 7781 | 904,322.02 | 6.70 |
| furniture_decor | 6425 | 8298 | 727,465.05 | 5.39 |
| housewares | 5847 | 6915 | 626,825.80 | 4.65 |
| cool_stuff | 3616 | 3779 | 620,770.49 | 4.60 |
| auto | 3872 | 4204 | 586,585.73 | 4.35 |
| garden_tools | 3505 | 4328 | 481,009.94 | 3.56 |
| toys | 3855 | 4083 | 479,808.54 | 3.56 |
| baby | 2868 | 3043 | 410,312.20 | 3.04 |
| perfumery | 3146 | 3402 | 396,599.31 | 2.94 |
| telephony | 4183 | 4527 | 322,342.64 | 2.39 |
| office_furniture | 1272 | 1690 | 273,580.70 | 2.03 |


## 02_monthly_revenue_and_orders

**Question:** How do revenue and the number of orders change month by month?

```sql
SELECT o.purchase_year                 AS year,
       o.purchase_month                AS month,
       COUNT(DISTINCT o.order_id)      AS orders,
       ROUND(SUM(oi.price), 2)         AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY o.purchase_year, o.purchase_month
ORDER BY o.purchase_year, o.purchase_month;
```

**Result:**

| year | month | orders | revenue |
|---|---|---|---|
| 2,016.00 | 9.00 | 2.00 | 207.86 |
| 2,016.00 | 10.00 | 290.00 | 44,507.30 |
| 2,016.00 | 12.00 | 1.00 | 10.90 |
| 2,017.00 | 1.00 | 787.00 | 120,098.27 |
| 2,017.00 | 2.00 | 1,718.00 | 244,959.35 |
| 2,017.00 | 3.00 | 2,617.00 | 368,341.32 |
| 2,017.00 | 4.00 | 2,377.00 | 353,842.98 |
| 2,017.00 | 5.00 | 3,640.00 | 503,159.19 |
| 2,017.00 | 6.00 | 3,205.00 | 429,916.61 |
| 2,017.00 | 7.00 | 3,946.00 | 492,287.30 |
| 2,017.00 | 8.00 | 4,272.00 | 568,245.79 |
| 2,017.00 | 9.00 | 4,227.00 | 621,415.91 |
| 2,017.00 | 10.00 | 4,547.00 | 660,179.62 |
| 2,017.00 | 11.00 | 7,421.00 | 1,003,862.14 |
| 2,017.00 | 12.00 | 5,618.00 | 742,183.79 |

*(first 15 of 24 rows)*


## 03_top_10_customers_by_spend

**Question:** Which 10 customers spend the most? (customer_unique_id = the real person)

```sql
SELECT c.customer_unique_id,
       MAX(c.state)                                  AS state,
       COUNT(DISTINCT o.order_id)                    AS orders,
       ROUND(SUM(oi.price + oi.freight_value), 2)    AS total_spent
FROM customers c
JOIN orders o       ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY c.customer_unique_id
ORDER BY total_spent DESC
LIMIT 10;
```

**Result:**

| customer_unique_id | state | orders | total_spent |
|---|---|---|---|
| 0a0a92112bd4c708ca5fde585afaa872 | RJ | 1 | 13,664.08 |
| da122df9eeddfedc1dc1f5349a1a690c | RJ | 2 | 7,571.63 |
| 763c8b1c9c68a0229c42c9fc6f662b93 | ES | 1 | 7,274.88 |
| dc4802a71eae9be1dd28f5d788ceb526 | MS | 1 | 6,929.31 |
| 459bef486812aa25204be022145caa62 | ES | 1 | 6,922.21 |
| ff4159b92c40ebe40454e3e6a7c35ed6 | SP | 1 | 6,726.66 |
| 4007669dec559734d6f53e029e360987 | MG | 1 | 6,081.54 |
| eebb5dda148d3893cdaf5b5ca3040ccb | SP | 1 | 4,764.34 |
| 48e1ac109decbb87765a3eade6854098 | PB | 1 | 4,681.78 |
| c8460e4251689ba205045f3ea17884a1 | RS | 4 | 4,655.88 |


## 04_top_10_sellers_by_revenue

**Question:** Which sellers earn the most (sellers with at least 10 orders)?

```sql
SELECT s.seller_id,
       s.state,
       COUNT(DISTINCT oi.order_id)   AS orders,
       ROUND(SUM(oi.price), 2)       AS revenue,
       ROUND(AVG(oi.price), 2)       AS avg_item_price
FROM sellers s
JOIN order_items oi ON oi.seller_id = s.seller_id
JOIN orders o       ON o.order_id = oi.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY s.seller_id, s.state
HAVING COUNT(DISTINCT oi.order_id) >= 10
ORDER BY revenue DESC
LIMIT 10;
```

**Result:**

| seller_id | state | orders | revenue | avg_item_price |
|---|---|---|---|---|
| 4869f7a5dfa277a7dca6462dcf3b52b2 | SP | 1131 | 229,237.63 | 198.47 |
| 53243585a1d6dc2643021fd1853d8905 | BA | 358 | 222,776.05 | 543.36 |
| 4a3ca9315b744ce9f8e9374361493884 | SP | 1804 | 200,326.12 | 100.92 |
| fa1c13f2614d7b5c4749cbc52fecda94 | SP | 584 | 192,842.13 | 329.64 |
| 7c67e1448b00f6e969d365cea6b010ab | SP | 982 | 187,923.89 | 137.77 |
| 7e93a43ef30c4f03f38b393420bc753a | SP | 332 | 172,583.88 | 513.64 |
| da8622b14eb17ae2831f4ac5b9dab84a | SP | 1314 | 160,236.57 | 103.31 |
| 7a67c85e85bb2ce8582c35f2203ad736 | SP | 1159 | 141,715.54 | 121.12 |
| 1025f0e2d44d7041d6cf58b6550e0bfa | SP | 915 | 138,968.55 | 97.32 |
| 955fee9216a65b617aa5c0531780ce60 | SP | 1286 | 135,159.70 | 90.23 |


## 05_average_order_value

**Question:** What is the average order value (items + freight)?

```sql
SELECT COUNT(*)                       AS orders,
       ROUND(AVG(order_total), 2)     AS avg_order_value,
       ROUND(MIN(order_total), 2)     AS smallest_order,
       ROUND(MAX(order_total), 2)     AS largest_order
FROM (SELECT oi.order_id,
             SUM(oi.price + oi.freight_value) AS order_total
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
       WHERE o.order_status NOT IN ('canceled', 'unavailable')
       GROUP BY oi.order_id);
```

**Result:**

| orders | avg_order_value | smallest_order | largest_order |
|---|---|---|---|
| 98,199.00 | 160.24 | 9.59 | 13,664.08 |


## 06_sales_by_customer_state

**Question:** Which states buy the most, and how much does each order cost there?

```sql
SELECT c.state,
       COUNT(DISTINCT c.customer_unique_id)   AS customers,
       COUNT(DISTINCT o.order_id)             AS orders,
       ROUND(SUM(oi.price), 2)                AS revenue,
       ROUND(SUM(oi.price) / COUNT(DISTINCT o.order_id), 2) AS revenue_per_order
FROM customers c
JOIN orders o       ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY c.state
HAVING COUNT(DISTINCT o.order_id) > 0
ORDER BY revenue DESC;
```

**Result:**

| state | customers | orders | revenue | revenue_per_order |
|---|---|---|---|---|
| SP | 39747 | 41125 | 5,163,867.22 | 125.57 |
| RJ | 12241 | 12697 | 1,811,623.42 | 142.68 |
| MG | 11134 | 11496 | 1,573,508.20 | 136.87 |
| RS | 5233 | 5415 | 742,559.78 | 137.13 |
| PR | 4824 | 4982 | 676,883.06 | 135.87 |
| SC | 3501 | 3599 | 518,578.28 | 144.09 |
| BA | 3244 | 3344 | 507,108.83 | 151.65 |
| DF | 2057 | 2120 | 300,886.45 | 141.93 |
| GO | 1934 | 1998 | 287,870.46 | 144.08 |
| ES | 1950 | 2018 | 273,532.13 | 135.55 |
| PE | 1600 | 1643 | 261,739.94 | 159.31 |
| CE | 1301 | 1323 | 226,264.06 | 171.02 |
| PA | 944 | 969 | 178,821.12 | 184.54 |
| MT | 872 | 902 | 156,313.53 | 173.30 |
| MA | 715 | 736 | 119,291.62 | 162.08 |

*(first 15 of 27 rows)*


## 07_late_vs_on_time_deliveries

**Question:** Are late deliveries rated worse than on-time ones?

```sql
SELECT CASE WHEN o.is_late = 1 THEN 'Late' ELSE 'On time' END AS delivery_status,
       COUNT(DISTINCT o.order_id)          AS orders,
       ROUND(AVG(o.delivery_days), 1)      AS avg_delivery_days,
       ROUND(AVG(r.review_score), 2)       AS avg_review_score
FROM orders o
JOIN order_reviews r ON r.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND o.is_late IS NOT NULL
GROUP BY delivery_status
ORDER BY delivery_status DESC;
```

**Result:**

| delivery_status | orders | avg_delivery_days | avg_review_score |
|---|---|---|---|
| On time | 89443 | 11.00 | 4.29 |
| Late | 6381 | 33.80 | 2.27 |


## 08_products_with_revenue_above_average

**Question:** Which products earn more than the average product?

```sql
WITH product_revenue AS (
    SELECT oi.product_id,
           pc.category_name_en   AS category,
           SUM(oi.price)         AS revenue,
           COUNT(*)              AS units_sold
      FROM order_items oi
      JOIN orders o              ON o.order_id = oi.order_id
      JOIN products p            ON p.product_id = oi.product_id
      JOIN product_categories pc ON pc.category_name = p.category_name
     WHERE o.order_status NOT IN ('canceled', 'unavailable')
     GROUP BY oi.product_id, pc.category_name_en
)
SELECT product_id, category, ROUND(revenue, 2) AS revenue, units_sold
FROM product_revenue
WHERE revenue > (SELECT AVG(revenue) FROM product_revenue)
ORDER BY revenue DESC
LIMIT 15;
```

**Result:**

| product_id | category | revenue | units_sold |
|---|---|---|---|
| bb50f2e236e5eea0100680137654686c | health_beauty | 63,885.00 | 195 |
| 6cdd53843498f92890544667809f1595 | health_beauty | 54,730.20 | 156 |
| d6160fb7873f184099d9bc95e30376af | computers | 48,899.34 | 35 |
| d1c427060a0f73f6b889a5c7c61f2ac4 | computers_accessories | 46,916.51 | 341 |
| 99a4788cb24856965c36a24e339b6058 | bed_bath_table | 42,938.66 | 487 |
| 3dd2a17168ec895c781a9191c1e95ad7 | computers_accessories | 41,082.60 | 274 |
| 25c38557cf793876c5abdd5931f922db | baby | 38,907.32 | 38 |
| 5f504b3a1c75b73d6151be81eb05bdc9 | cool_stuff | 37,733.90 | 63 |
| 53b36df67ebb7c41585e8d54d6772e08 | watches_gifts | 37,683.42 | 323 |
| aca2eb7d00ea1a7b8ebd4e68314663af | furniture_decor | 37,608.90 | 527 |
| e0d64dcfaa3b6db5c54ca298ae101d05 | watches_gifts | 31,786.82 | 194 |
| d285360f29ac7fd97640bf0baef03de0 | watches_gifts | 31,623.81 | 123 |
| 7a10781637204d8d10485c71a6108a2e | watches_gifts | 30,467.50 | 143 |
| f1c7f353075ce59d8a6f3cf58f419c9c | bed_bath_table | 29,997.36 | 154 |
| f819f0c84a64f02d3a5606ca95edd272 | watches_gifts | 29,024.48 | 45 |


## 09_payment_type_share

**Question:** How do customers pay, and what share of money does each method carry?

```sql
SELECT payment_type,
       COUNT(DISTINCT order_id)                                   AS orders,
       ROUND(SUM(payment_value), 2)                               AS total_value,
       ROUND(AVG(payment_installments), 1)                        AS avg_installments,
       ROUND(100.0 * SUM(payment_value) / SUM(SUM(payment_value)) OVER (), 2) AS pct_of_value
FROM order_payments
GROUP BY payment_type
ORDER BY total_value DESC;
```

**Result:**

| payment_type | orders | total_value | avg_installments | pct_of_value |
|---|---|---|---|---|
| credit_card | 76505 | 12,542,084.19 | 3.50 | 78.34 |
| boleto | 19784 | 2,869,361.27 | 1.00 | 17.92 |
| voucher | 3866 | 379,436.87 | 1.00 | 2.37 |
| debit_card | 1528 | 217,989.79 | 1.00 | 1.36 |


## 10_month_over_month_growth

**Question:** By what percent did revenue grow or fall versus the previous month?

```sql
WITH monthly AS (
    SELECT o.purchase_year * 100 + o.purchase_month AS year_month,
           SUM(oi.price)                            AS revenue
      FROM orders o
      JOIN order_items oi ON oi.order_id = o.order_id
     WHERE o.order_status NOT IN ('canceled', 'unavailable')
     GROUP BY o.purchase_year, o.purchase_month
),
with_prev AS (
    SELECT year_month,
           revenue,
           LAG(revenue) OVER (ORDER BY year_month) AS prev_revenue
      FROM monthly
)
SELECT year_month,
       ROUND(revenue, 2)                                   AS revenue,
       ROUND(prev_revenue, 2)                              AS prev_month_revenue,
       ROUND(100.0 * (revenue - prev_revenue) / prev_revenue, 1) AS growth_pct
FROM with_prev
ORDER BY year_month;
```

**Result:**

| year_month | revenue | prev_month_revenue | growth_pct |
|---|---|---|---|
| 201,609.00 | 207.86 | nan | nan |
| 201,610.00 | 44,507.30 | 207.86 | 21,312.20 |
| 201,612.00 | 10.90 | 44,507.30 | -100.00 |
| 201,701.00 | 120,098.27 | 10.90 | 1,101,719.00 |
| 201,702.00 | 244,959.35 | 120,098.27 | 104.00 |
| 201,703.00 | 368,341.32 | 244,959.35 | 50.40 |
| 201,704.00 | 353,842.98 | 368,341.32 | -3.90 |
| 201,705.00 | 503,159.19 | 353,842.98 | 42.20 |
| 201,706.00 | 429,916.61 | 503,159.19 | -14.60 |
| 201,707.00 | 492,287.30 | 429,916.61 | 14.50 |
| 201,708.00 | 568,245.79 | 492,287.30 | 15.40 |
| 201,709.00 | 621,415.91 | 568,245.79 | 9.40 |
| 201,710.00 | 660,179.62 | 621,415.91 | 6.20 |
| 201,711.00 | 1,003,862.14 | 660,179.62 | 52.10 |
| 201,712.00 | 742,183.79 | 1,003,862.14 | -26.10 |

*(first 15 of 24 rows)*


## 11_top_category_in_each_state

**Question:** What is the best-selling category in each of the top 10 revenue states?

```sql
WITH state_cat AS (
    SELECT c.state,
           pc.category_name_en AS category,
           SUM(oi.price)       AS revenue
      FROM order_items oi
      JOIN orders o              ON o.order_id = oi.order_id
      JOIN customers c           ON c.customer_id = o.customer_id
      JOIN products p            ON p.product_id = oi.product_id
      JOIN product_categories pc ON pc.category_name = p.category_name
     WHERE o.order_status NOT IN ('canceled', 'unavailable')
     GROUP BY c.state, pc.category_name_en
),
ranked AS (
    SELECT state, category, revenue,
           RANK() OVER (PARTITION BY state ORDER BY revenue DESC) AS rnk,
           SUM(revenue) OVER (PARTITION BY state)                 AS state_revenue
      FROM state_cat
)
SELECT state, category, ROUND(revenue, 2) AS category_revenue,
       ROUND(100.0 * revenue / state_revenue, 1) AS pct_of_state
FROM ranked
WHERE rnk = 1
ORDER BY state_revenue DESC
LIMIT 10;
```

**Result:**

| state | category | category_revenue | pct_of_state |
|---|---|---|---|
| SP | bed_bath_table | 477,794.20 | 9.30 |
| RJ | watches_gifts | 183,931.50 | 10.20 |
| MG | health_beauty | 157,433.32 | 10.00 |
| RS | bed_bath_table | 60,270.74 | 8.10 |
| PR | watches_gifts | 59,859.04 | 8.80 |
| SC | sports_leisure | 43,466.90 | 8.40 |
| BA | health_beauty | 51,217.91 | 10.10 |
| DF | watches_gifts | 32,730.37 | 10.90 |
| GO | watches_gifts | 32,358.72 | 11.20 |
| ES | watches_gifts | 29,461.00 | 10.80 |
