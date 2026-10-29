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
