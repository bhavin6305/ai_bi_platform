-- ============================================================
-- AI-Powered BI Platform — KPI Views
-- Olist dataset specific — for development and Power BI
-- Replace {PREFIX} with your actual session short ID
-- e.g. d60ba6f1
-- Run AFTER the ETL pipeline has loaded data
-- ============================================================

-- ── View 1: Monthly Revenue Summary ─────────────────────────────────────────
-- Aggregates revenue by month for trend analysis and forecasting
CREATE OR REPLACE VIEW v_monthly_revenue AS
SELECT
    DATE_TRUNC('month', o.order_purchase_timestamp::timestamp) AS month,
    COUNT(DISTINCT o.order_id)           AS total_orders,
    COUNT(DISTINCT o.customer_id)        AS unique_customers,
    ROUND(SUM(oi.price)::numeric, 2)     AS total_revenue,
    ROUND(AVG(oi.price)::numeric, 2)     AS avg_order_value,
    ROUND(SUM(oi.freight_value)::numeric, 2) AS total_freight
FROM "{PREFIX}_olist_orders_dataset"     o
JOIN "{PREFIX}_olist_order_items_dataset" oi
    ON o.order_id = oi.order_id
WHERE
    o.order_purchase_timestamp IS NOT NULL
    AND o.order_status = 'Delivered'
GROUP BY month
ORDER BY month;


-- ── View 2: Revenue by Product Category ──────────────────────────────────────
-- Shows which categories drive the most revenue
CREATE OR REPLACE VIEW v_revenue_by_category AS
SELECT
    p.product_category_name                  AS category,
    COUNT(DISTINCT oi.order_id)              AS total_orders,
    COUNT(DISTINCT oi.product_id)            AS unique_products,
    ROUND(SUM(oi.price)::numeric, 2)         AS total_revenue,
    ROUND(AVG(oi.price)::numeric, 2)         AS avg_price,
    ROUND(
        SUM(oi.price) * 100.0 /
        NULLIF(SUM(SUM(oi.price)) OVER (), 0),
        2
    )                                        AS revenue_share_pct
FROM "{PREFIX}_olist_order_items_dataset"    oi
JOIN "{PREFIX}_olist_products_dataset"       p
    ON oi.product_id = p.product_id
GROUP BY p.product_category_name
ORDER BY total_revenue DESC;


-- ── View 3: Customer Summary ──────────────────────────────────────────────────
-- One row per customer with all their purchase behaviour
-- This is the base table for churn prediction (Member 2 uses this)
CREATE OR REPLACE VIEW v_customer_summary AS
SELECT
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    COUNT(DISTINCT o.order_id)                          AS total_orders,
    ROUND(SUM(oi.price)::numeric, 2)                    AS total_spend,
    ROUND(AVG(oi.price)::numeric, 2)                    AS avg_order_value,
    MIN(o.order_purchase_timestamp::timestamp)          AS first_order_date,
    MAX(o.order_purchase_timestamp::timestamp)          AS last_order_date,
    EXTRACT(DAY FROM (
        MAX(o.order_purchase_timestamp::timestamp) -
        MIN(o.order_purchase_timestamp::timestamp)
    ))                                                  AS customer_tenure_days,
    EXTRACT(DAY FROM (
        NOW() - MAX(o.order_purchase_timestamp::timestamp)
    ))                                                  AS days_since_last_order,
    -- Churn label: 1 = no purchase in last 180 days (churned), 0 = active
    CASE
        WHEN EXTRACT(DAY FROM (NOW() - MAX(o.order_purchase_timestamp::timestamp))) > 180
        THEN 1 ELSE 0
    END                                                  AS churn_label
FROM "{PREFIX}_olist_customers_dataset"        c
JOIN "{PREFIX}_olist_orders_dataset"           o
    ON c.customer_id = o.customer_id
JOIN "{PREFIX}_olist_order_items_dataset"      oi
    ON o.order_id = oi.order_id
WHERE o.order_status = 'Delivered'
GROUP BY
    c.customer_unique_id,
    c.customer_city,
    c.customer_state
ORDER BY total_spend DESC;


-- ── View 4: Order Status Breakdown ────────────────────────────────────────────
-- Shows distribution of order statuses
CREATE OR REPLACE VIEW v_order_status_breakdown AS
SELECT
    order_status,
    COUNT(*)                                AS order_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (),
        2
    )                                       AS percentage
FROM "{PREFIX}_olist_orders_dataset"
GROUP BY order_status
ORDER BY order_count DESC;


-- ── View 5: Top Products ──────────────────────────────────────────────────────
-- Top 20 products by revenue
CREATE OR REPLACE VIEW v_top_products AS
SELECT
    oi.product_id,
    p.product_category_name              AS category,
    COUNT(DISTINCT oi.order_id)          AS times_ordered,
    ROUND(SUM(oi.price)::numeric, 2)     AS total_revenue,
    ROUND(AVG(oi.price)::numeric, 2)     AS avg_price
FROM "{PREFIX}_olist_order_items_dataset" oi
JOIN "{PREFIX}_olist_products_dataset"    p
    ON oi.product_id = p.product_id
GROUP BY oi.product_id, p.product_category_name
ORDER BY total_revenue DESC
LIMIT 20;


-- ── View 6: Geographic Revenue ────────────────────────────────────────────────
-- Revenue breakdown by customer state — for regional analysis
CREATE OR REPLACE VIEW v_revenue_by_state AS
SELECT
    c.customer_state                         AS state,
    COUNT(DISTINCT c.customer_unique_id)     AS unique_customers,
    COUNT(DISTINCT o.order_id)               AS total_orders,
    ROUND(SUM(oi.price)::numeric, 2)         AS total_revenue,
    ROUND(AVG(oi.price)::numeric, 2)         AS avg_order_value
FROM "{PREFIX}_olist_customers_dataset"       c
JOIN "{PREFIX}_olist_orders_dataset"          o
    ON c.customer_id = o.customer_id
JOIN "{PREFIX}_olist_order_items_dataset"     oi
    ON o.order_id = oi.order_id
WHERE o.order_status = 'Delivered'
GROUP BY c.customer_state
ORDER BY total_revenue DESC;


-- ── View 7: Delivery Performance ─────────────────────────────────────────────
-- Measures actual vs estimated delivery time
CREATE OR REPLACE VIEW v_delivery_performance AS
SELECT
    DATE_TRUNC('month', order_purchase_timestamp::timestamp) AS month,
    COUNT(*)                                                  AS total_orders,
    COUNT(CASE WHEN order_delivered_customer_date IS NOT NULL THEN 1 END)
                                                              AS delivered_orders,
    ROUND(AVG(
        EXTRACT(DAY FROM (
            order_delivered_customer_date::timestamp -
            order_purchase_timestamp::timestamp
        ))
    )::numeric, 1)                                            AS avg_delivery_days,
    ROUND(AVG(
        EXTRACT(DAY FROM (
            order_estimated_delivery_date::timestamp -
            order_purchase_timestamp::timestamp
        ))
    )::numeric, 1)                                            AS avg_estimated_days,
    -- Negative = delivered early, Positive = delivered late
    ROUND(AVG(
        EXTRACT(DAY FROM (
            order_delivered_customer_date::timestamp -
            order_estimated_delivery_date::timestamp
        ))
    )::numeric, 1)                                            AS avg_delay_days
FROM "{PREFIX}_olist_orders_dataset"
WHERE order_purchase_timestamp IS NOT NULL
GROUP BY month
ORDER BY month;


-- ── Verification: list all views created ─────────────────────────────────────
SELECT viewname
FROM   pg_views
WHERE  schemaname = 'public'
  AND  viewname LIKE 'v_%'
ORDER  BY viewname;