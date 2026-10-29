-- ===== PART 1: DATABASE AND TABLE CREATION =====
-- =====================================================================
-- Olist E-Commerce database (SQLite)
-- Run order matters: parent tables first, child tables after.
-- =====================================================================
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS order_reviews;
DROP TABLE IF EXISTS order_payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS product_categories;
DROP TABLE IF EXISTS sellers;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS geolocation;

-- ---------------------------------------------------------------------
-- Lookup: one row per zip-code prefix (averaged coordinates).
-- Not linked by a foreign key: a few customer/seller zip codes do not
-- exist in the raw geolocation file, so a FK would reject valid rows.
-- ---------------------------------------------------------------------
CREATE TABLE geolocation (
    zip_code_prefix  INTEGER PRIMARY KEY,
    latitude         REAL    NOT NULL,
    longitude        REAL    NOT NULL,
    city             TEXT,
    state            TEXT
);

-- ---------------------------------------------------------------------
-- customers: customer_id is generated PER ORDER in Olist.
-- customer_unique_id identifies the real person across orders.
-- ---------------------------------------------------------------------
CREATE TABLE customers (
    customer_id        TEXT PRIMARY KEY,
    customer_unique_id TEXT NOT NULL,
    zip_code_prefix    INTEGER,
    city               TEXT,
    state              TEXT CHECK (length(state) = 2)
);

CREATE TABLE sellers (
    seller_id        TEXT PRIMARY KEY,
    zip_code_prefix  INTEGER,
    city             TEXT,
    state            TEXT CHECK (length(state) = 2)
);

-- ---------------------------------------------------------------------
-- product_categories: Portuguese name -> English name
-- ---------------------------------------------------------------------
CREATE TABLE product_categories (
    category_name     TEXT PRIMARY KEY,   -- original Portuguese name
    category_name_en  TEXT NOT NULL       -- English name
);

CREATE TABLE products (
    product_id          TEXT PRIMARY KEY,
    category_name       TEXT,
    name_length         INTEGER CHECK (name_length >= 0),
    description_length  INTEGER CHECK (description_length >= 0),
    photos_qty          INTEGER CHECK (photos_qty >= 0),
    weight_g            REAL    CHECK (weight_g >= 0),
    length_cm           REAL    CHECK (length_cm >= 0),
    height_cm           REAL    CHECK (height_cm >= 0),
    width_cm            REAL    CHECK (width_cm >= 0),
    FOREIGN KEY (category_name) REFERENCES product_categories (category_name)
);

CREATE TABLE orders (
    order_id                  TEXT PRIMARY KEY,
    customer_id               TEXT NOT NULL,
    order_status              TEXT NOT NULL CHECK (order_status IN (
                                  'created','approved','invoiced','processing',
                                  'shipped','delivered','unavailable','canceled')),
    purchase_ts               TEXT NOT NULL,   -- 'YYYY-MM-DD HH:MM:SS'
    approved_ts               TEXT,
    delivered_carrier_ts      TEXT,
    delivered_customer_ts     TEXT,
    estimated_delivery_date   TEXT,
    purchase_year             INTEGER NOT NULL,
    purchase_month            INTEGER NOT NULL CHECK (purchase_month BETWEEN 1 AND 12),
    delivery_days             REAL,            -- purchase -> customer
    delay_days                REAL,            -- delivered - estimated (>0 = late)
    is_late                   INTEGER CHECK (is_late IN (0, 1)),
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE TABLE order_items (
    order_id            TEXT    NOT NULL,
    order_item_id       INTEGER NOT NULL,
    product_id          TEXT    NOT NULL,
    seller_id           TEXT    NOT NULL,
    shipping_limit_ts   TEXT,
    price               REAL    NOT NULL CHECK (price >= 0),
    freight_value       REAL    NOT NULL CHECK (freight_value >= 0),
    total_price         REAL    NOT NULL,      -- price + freight_value
    PRIMARY KEY (order_id, order_item_id),
    FOREIGN KEY (order_id)   REFERENCES orders   (order_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id),
    FOREIGN KEY (seller_id)  REFERENCES sellers  (seller_id)
);

CREATE TABLE order_payments (
    order_id              TEXT    NOT NULL,
    payment_sequential    INTEGER NOT NULL,
    payment_type          TEXT    NOT NULL CHECK (payment_type IN (
                              'credit_card','boleto','voucher','debit_card','not_defined')),
    payment_installments  INTEGER NOT NULL CHECK (payment_installments >= 0),
    payment_value         REAL    NOT NULL CHECK (payment_value >= 0),
    PRIMARY KEY (order_id, payment_sequential),
    FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

-- A few review_ids are reused for different orders in the raw data,
-- so the primary key is the pair (review_id, order_id).
CREATE TABLE order_reviews (
    review_id         TEXT    NOT NULL,
    order_id          TEXT    NOT NULL,
    review_score      INTEGER NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    comment_title     TEXT,
    comment_message   TEXT,
    creation_date     TEXT,
    answer_ts         TEXT,
    PRIMARY KEY (review_id, order_id),
    FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

-- Indexes for the joins and filters used in the reports
CREATE INDEX idx_orders_customer   ON orders (customer_id);
CREATE INDEX idx_orders_purchase   ON orders (purchase_year, purchase_month);
CREATE INDEX idx_items_product     ON order_items (product_id);
CREATE INDEX idx_items_seller      ON order_items (seller_id);
CREATE INDEX idx_products_category ON products (category_name);
CREATE INDEX idx_customers_unique  ON customers (customer_unique_id);
CREATE INDEX idx_customers_state   ON customers (state);


-- ===== PART 2: SQL REPORTING QUERIES =====
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
