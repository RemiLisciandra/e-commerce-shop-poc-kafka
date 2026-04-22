"""
DAG : ecommerce_dmart_load
----------------------------
Schedule : None (déclenché par ecommerce_dwh_load via TriggerDagRunOperator)

Construit les tables analytiques du schéma `dmart` à partir des données
propres du schéma `dwh`. Toutes les tables DMART sont reconstruites en parallèle.

Connexion PostgreSQL : variable d'environnement AIRFLOW_CONN_POSTGRES_DWH
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

CONN_ID = "postgres_dwh"

with DAG(
    dag_id="ecommerce_dmart_load",
    description="dwh.* → dmart.* : construction des tables analytiques",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["ecommerce", "dmart"],
) as dag:

    # ── Tables analytiques — 6 tâches en parallèle ────────────────────────────

    mart_sales_daily = PostgresOperator(
        task_id="mart_sales_daily",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dmart.mart_sales_daily CASCADE;
            DO $$ BEGIN
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'orders')
                AND EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'order_items')
                THEN
                    CREATE TABLE dmart.mart_sales_daily AS
                    WITH daily AS (
                        SELECT
                            DATE_TRUNC('day', o.source_updated_at)::DATE    AS order_date,
                            COUNT(DISTINCT o.order_id)                      AS nb_orders,
                            SUM(oi.quantity)                                AS units_sold,
                            SUM(oi.line_total_ht)                           AS revenue_ht,
                            SUM(oi.line_total_ttc)                          AS revenue_ttc
                        FROM dwh.orders o
                        JOIN dwh.order_items oi ON oi.order_id = o.order_id
                        WHERE o.status = 'confirmed'
                        GROUP BY 1
                    )
                    SELECT
                        order_date,
                        nb_orders,
                        units_sold,
                        revenue_ht,
                        revenue_ttc,
                        SUM(revenue_ttc) OVER (ORDER BY order_date)     AS cumulative_revenue_ttc
                    FROM daily
                    ORDER BY order_date;
                END IF;
            END $$;
        """,
    )

    mart_revenue_by_item = PostgresOperator(
        task_id="mart_revenue_by_item",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dmart.mart_revenue_by_item CASCADE;
            DO $$ BEGIN
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'items')
                AND EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'order_items')
                AND EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'orders')
                THEN
                    CREATE TABLE dmart.mart_revenue_by_item AS
                    WITH sales AS (
                        SELECT
                            oi.item_id,
                            COUNT(DISTINCT oi.order_id)         AS nb_orders,
                            SUM(oi.quantity)                    AS total_units_sold,
                            SUM(oi.line_total_ht)               AS total_revenue_ht,
                            SUM(oi.line_total_ttc)              AS total_revenue_ttc
                        FROM dwh.order_items oi
                        JOIN dwh.orders o ON o.order_id = oi.order_id
                        WHERE o.status = 'confirmed'
                        GROUP BY oi.item_id
                    )
                    SELECT
                        i.item_id,
                        i.title,
                        i.price_ht,
                        i.price_ttc,
                        i.tva_rate,
                        i.quantity                              AS current_stock,
                        COALESCE(s.nb_orders, 0)               AS nb_orders,
                        COALESCE(s.total_units_sold, 0)        AS total_units_sold,
                        COALESCE(s.total_revenue_ht, 0)        AS total_revenue_ht,
                        COALESCE(s.total_revenue_ttc, 0)       AS total_revenue_ttc
                    FROM dwh.items i
                    LEFT JOIN sales s ON s.item_id = i.item_id
                    ORDER BY total_revenue_ttc DESC;
                END IF;
            END $$;
        """,
    )

    mart_customer_lifetime = PostgresOperator(
        task_id="mart_customer_lifetime",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dmart.mart_customer_lifetime CASCADE;
            DO $$ BEGIN
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'customers')
                AND EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'orders')
                THEN
                    CREATE TABLE dmart.mart_customer_lifetime AS
                    SELECT
                        c.customer_id,
                        c.first_name,
                        c.last_name,
                        c.email,
                        COUNT(o.order_id)                                       AS nb_orders,
                        COALESCE(SUM(o.total_ttc), 0)                           AS lifetime_value_ttc,
                        COALESCE(AVG(o.total_ttc), 0)                           AS avg_basket_ttc,
                        MIN(o.source_updated_at)                                AS first_order_at,
                        MAX(o.source_updated_at)                                AS last_order_at,
                        CASE
                            WHEN COUNT(o.order_id) = 0               THEN 'no_order'
                            WHEN COUNT(o.order_id) = 1               THEN 'one_time'
                            WHEN COUNT(o.order_id) BETWEEN 2 AND 4   THEN 'recurring'
                            ELSE 'loyal'
                        END                                                     AS customer_segment
                    FROM dwh.customers c
                    LEFT JOIN dwh.orders o
                        ON o.customer_id = c.customer_id AND o.status = 'confirmed'
                    GROUP BY c.customer_id, c.first_name, c.last_name, c.email
                    ORDER BY lifetime_value_ttc DESC;
                END IF;
            END $$;
        """,
    )

    mart_customer_reorders = PostgresOperator(
        task_id="mart_customer_reorders",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dmart.mart_customer_reorders CASCADE;
            DO $$ BEGIN
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'order_items')
                AND EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'orders')
                AND EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'items')
                THEN
                    CREATE TABLE dmart.mart_customer_reorders AS
                    SELECT
                        o.customer_id,
                        oi.item_id,
                        i.title,
                        i.price_ttc,
                        SUM(oi.quantity)                                AS total_qty_purchased,
                        COUNT(DISTINCT oi.order_id)                     AS nb_orders_with_item,
                        MAX(o.source_updated_at)                        AS last_purchased_at,
                        i.quantity                                      AS current_stock
                    FROM dwh.order_items oi
                    JOIN dwh.orders  o ON o.order_id = oi.order_id
                    JOIN dwh.items   i ON i.item_id  = oi.item_id
                    WHERE o.status = 'confirmed'
                    GROUP BY o.customer_id, oi.item_id, i.title, i.price_ttc, i.quantity
                    ORDER BY o.customer_id, last_purchased_at DESC;
                END IF;
            END $$;
        """,
    )

    mart_payments = PostgresOperator(
        task_id="mart_payments",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dmart.mart_payments CASCADE;
            DO $$ BEGIN
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'payments')
                AND EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'orders')
                AND EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'customers')
                THEN
                    CREATE TABLE dmart.mart_payments AS
                    SELECT
                        p.payment_id,
                        p.order_id,
                        o.customer_id,
                        c.first_name,
                        c.last_name,
                        c.email,
                        p.amount,
                        p.payment_status,
                        p.payment_method,
                        p.transaction_id,
                        p.source_updated_at                             AS paid_at
                    FROM dwh.payments   p
                    JOIN dwh.orders     o ON o.order_id    = p.order_id
                    JOIN dwh.customers  c ON c.customer_id = o.customer_id
                    ORDER BY p.source_updated_at DESC;
                END IF;
            END $$;
        """,
    )

    mart_invoices = PostgresOperator(
        task_id="mart_invoices",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dmart.mart_invoices CASCADE;
            DO $$ BEGIN
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'invoices')
                AND EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'orders')
                AND EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'dwh' AND table_name = 'customers')
                THEN
                    CREATE TABLE dmart.mart_invoices AS
                    SELECT
                        i.invoice_id,
                        i.invoice_number,
                        i.order_id,
                        o.customer_id,
                        c.first_name,
                        c.last_name,
                        c.email,
                        i.total_ht,
                        i.total_tva,
                        i.total_ttc,
                        i.issued_at,
                        i.due_date,
                        CASE
                            WHEN i.due_date < CURRENT_DATE THEN 'overdue'
                            ELSE 'on_time'
                        END                                             AS due_status
                    FROM dwh.invoices    i
                    JOIN dwh.orders      o ON o.order_id    = i.order_id
                    JOIN dwh.customers   c ON c.customer_id = o.customer_id
                    ORDER BY i.issued_at DESC;
                END IF;
            END $$;
        """,
    )

    # Toutes les tâches DMART sont indépendantes et s'exécutent en parallèle
    [
        mart_sales_daily,
        mart_revenue_by_item,
        mart_customer_lifetime,
        mart_customer_reorders,
        mart_payments,
        mart_invoices,
    ]
