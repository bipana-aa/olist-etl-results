-- =====================================================================
-- SQL REPORTS  (run against database/olist.db)
-- "Revenue" = SUM(price) of items in orders that were not canceled or
-- unavailable. Freight is counted only where noted ("order total").
-- Each query starts with a "-- name:" and "-- question:" line; the
-- pipeline reads these markers to run every query and save its result.
-- =====================================================================


-- name: 01_revenue_by_category
-- question: Which product categories generate the most revenue?
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


-- name: 02_monthly_revenue_and_orders
-- question: How do revenue and the number of orders change month by month?
SELECT o.purchase_year                 AS year,
       o.purchase_month                AS month,
       COUNT(DISTINCT o.order_id)      AS orders,
       ROUND(SUM(oi.price), 2)         AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY o.purchase_year, o.purchase_month
ORDER BY o.purchase_year, o.purchase_month;


-- name: 03_top_10_customers_by_spend
-- question: Which 10 customers spend the most? (customer_unique_id = the real person)
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


-- name: 04_top_10_sellers_by_revenue
-- question: Which sellers earn the most (sellers with at least 10 orders)?
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


-- name: 05_average_order_value
-- question: What is the average order value (items + freight)?
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


-- name: 06_sales_by_customer_state
-- question: Which states buy the most, and how much does each order cost there?
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


-- name: 07_late_vs_on_time_deliveries
-- question: Are late deliveries rated worse than on-time ones?
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


-- name: 08_products_with_revenue_above_average
-- question: Which products earn more than the average product?
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


-- name: 09_payment_type_share
-- question: How do customers pay, and what share of money does each method carry?
SELECT payment_type,
       COUNT(DISTINCT order_id)                                   AS orders,
       ROUND(SUM(payment_value), 2)                               AS total_value,
       ROUND(AVG(payment_installments), 1)                        AS avg_installments,
       ROUND(100.0 * SUM(payment_value) / SUM(SUM(payment_value)) OVER (), 2) AS pct_of_value
FROM order_payments
GROUP BY payment_type
ORDER BY total_value DESC;


-- name: 10_month_over_month_growth
-- question: By what percent did revenue grow or fall versus the previous month?
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


-- name: 11_top_category_in_each_state
-- question: What is the best-selling category in each of the top 10 revenue states?
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
