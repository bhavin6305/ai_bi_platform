-- ============================================================
-- AI-Powered BI Platform — Analytical Query Templates
-- These are the types of queries the AI chatbot will generate
-- Replace {PREFIX} with your session short ID
-- ============================================================


-- ── Query 1: Revenue This Month vs Last Month ─────────────────────────────
-- Answers: "How is revenue performing vs last month?"
SELECT
    DATE_TRUNC('month', NOW())                          AS current_month,
    ROUND(SUM(CASE
        WHEN DATE_TRUNC('month', o.order_purchase_timestamp::timestamp)
             = DATE_TRUNC('month', NOW())
        THEN oi.price ELSE 0
    END)::numeric, 2)                                   AS revenue_this_month,
    ROUND(SUM(CASE
        WHEN DATE_TRUNC('month', o.order_purchase_timestamp::timestamp)
             = DATE_TRUNC('month', NOW() - INTERVAL '1 month')
        THEN oi.price ELSE 0
    END)::numeric, 2)                                   AS revenue_last_month
FROM "{PREFIX}_olist_orders_dataset"       o
JOIN "{PREFIX}_olist_order_items_dataset"  oi
    ON o.order_id = oi.order_id;


-- ── Query 2: Top 5 Categories This Month ──────────────────────────────────
-- Answers: "Which categories are performing best?"
SELECT
    p.product_category_name                 AS category,
    COUNT(DISTINCT oi.order_id)             AS orders,
    ROUND(SUM(oi.price)::numeric, 2)        AS revenue
FROM "{PREFIX}_olist_order_items_dataset"   oi
JOIN "{PREFIX}_olist_products_dataset"      p
    ON oi.product_id = p.product_id
JOIN "{PREFIX}_olist_orders_dataset"        o
    ON oi.order_id = o.order_id
WHERE
    o.order_status = 'Delivered'
    AND DATE_TRUNC('month', o.order_purchase_timestamp::timestamp)
        = DATE_TRUNC('month', NOW() - INTERVAL '1 month')
GROUP BY p.product_category_name
ORDER BY revenue DESC
LIMIT 5;


-- ── Query 3: Customer Churn Risk ──────────────────────────────────────────
-- Answers: "Which customers are at risk of churning?"
SELECT
    customer_unique_id,
    customer_state,
    total_orders,
    total_spend,
    days_since_last_order,
    CASE
        WHEN days_since_last_order > 180 THEN 'High Risk'
        WHEN days_since_last_order > 90  THEN 'Medium Risk'
        ELSE 'Active'
    END AS churn_risk
FROM v_customer_summary
WHERE days_since_last_order > 90
ORDER BY days_since_last_order DESC
LIMIT 20;


-- ── Query 4: Revenue Growth Rate (MoM) ────────────────────────────────────
-- Answers: "What is our month-over-month growth?"
SELECT
    month,
    total_revenue,
    LAG(total_revenue) OVER (ORDER BY month)        AS prev_month_revenue,
    ROUND(
        (total_revenue - LAG(total_revenue) OVER (ORDER BY month))
        * 100.0
        / NULLIF(LAG(total_revenue) OVER (ORDER BY month), 0),
        2
    )                                               AS mom_growth_pct
FROM v_monthly_revenue
ORDER BY month;


-- ── Query 5: Best Selling Products ────────────────────────────────────────
-- Answers: "What are our best selling products?"
SELECT * FROM v_top_products LIMIT 10;


-- ── Query 6: Regional Performance ─────────────────────────────────────────
-- Answers: "Which regions are performing best?"
SELECT * FROM v_revenue_by_state LIMIT 10;


-- ── Query 7: Delivery Issues ──────────────────────────────────────────────
-- Answers: "Are there delivery problems?"
SELECT
    month,
    avg_delivery_days,
    avg_estimated_days,
    avg_delay_days,
    CASE
        WHEN avg_delay_days > 3  THEN 'Significant Delays'
        WHEN avg_delay_days > 0  THEN 'Minor Delays'
        WHEN avg_delay_days <= 0 THEN 'On Time or Early'
    END AS delivery_status
FROM v_delivery_performance
ORDER BY month DESC
LIMIT 12;


-- ── Query 8: Low Stock / High Demand Products ─────────────────────────────
-- Answers: "Which products need attention?"
SELECT
    p.product_category_name              AS category,
    COUNT(oi.order_id)                   AS recent_orders,
    ROUND(SUM(oi.price)::numeric, 2)     AS recent_revenue
FROM "{PREFIX}_olist_order_items_dataset"   oi
JOIN "{PREFIX}_olist_products_dataset"      p
    ON oi.product_id = p.product_id
JOIN "{PREFIX}_olist_orders_dataset"        o
    ON oi.order_id = o.order_id
WHERE
    o.order_purchase_timestamp::timestamp
    >= NOW() - INTERVAL '30 days'
GROUP BY p.product_category_name
ORDER BY recent_orders DESC
LIMIT 10;