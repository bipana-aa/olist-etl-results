# Entity Relationship Diagram

Picture: `ERD.png`. The diagram below is the same design in Mermaid (GitHub draws it automatically).

![ERD](ERD.png)

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : "customer_id"
    ORDERS ||--o{ ORDER_ITEMS : "order_id"
    PRODUCTS ||--o{ ORDER_ITEMS : "product_id"
    SELLERS ||--o{ ORDER_ITEMS : "seller_id"
    ORDERS ||--o{ ORDER_PAYMENTS : "order_id"
    ORDERS ||--o{ ORDER_REVIEWS : "order_id"
    PRODUCT_CATEGORIES ||--o{ PRODUCTS : "category_name"
    CUSTOMERS {
        text customer_id PK
        text customer_unique_id
        integer zip_code_prefix
        text city
        text state
    }
    SELLERS {
        text seller_id PK
        integer zip_code_prefix
        text city
        text state
    }
    GEOLOCATION {
        integer zip_code_prefix PK
        real latitude
        real longitude
        text city
        text state
    }
    PRODUCT_CATEGORIES {
        text category_name PK
        text category_name_en
    }
    PRODUCTS {
        text product_id PK
        text category_name FK
        integer name_length
        integer description_length
        integer photos_qty
        real weight_g
        real length_cm
        real height_cm
        real width_cm
    }
    ORDERS {
        text order_id PK
        text customer_id FK
        text order_status
        text purchase_ts
        text approved_ts
        text delivered_carrier_ts
        text delivered_customer_ts
        text estimated_delivery_date
        integer purchase_year
        integer purchase_month
        real delivery_days
        real delay_days
        integer is_late
    }
    ORDER_ITEMS {
        text order_id PK,FK
        integer order_item_id PK
        text product_id FK
        text seller_id FK
        text shipping_limit_ts
        real price
        real freight_value
        real total_price
    }
    ORDER_PAYMENTS {
        text order_id PK,FK
        integer payment_sequential PK
        text payment_type
        integer payment_installments
        real payment_value
    }
    ORDER_REVIEWS {
        text review_id PK
        text order_id PK,FK
        integer review_score
        text comment_title
        text comment_message
        text creation_date
        text answer_ts
    }
```

**Reading it:** a customer places many orders; an order has many items, payments and reviews; a product belongs to one category; a seller sells many items. `geolocation` is a lookup table joined by `zip_code_prefix` without a foreign key (some zip codes in customers and sellers are missing from the raw geolocation file).
