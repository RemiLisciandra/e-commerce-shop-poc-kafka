"""
DAG : ecommerce_dwh_load
--------------------------
Schedule : toutes les 15 minutes

Charge les tables brutes du schéma `staging` (injectées par le JDBC Sink Kafka Connect)
vers le schéma `dwh` (données nettoyées, typées, lignes supprimées filtrées).

À la fin, déclenche automatiquement le DAG `ecommerce_dmart_load`.

Connexion PostgreSQL : variable d'environnement AIRFLOW_CONN_POSTGRES_DWH
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

CONN_ID = "postgres_dwh"

with DAG(
    dag_id="ecommerce_dwh_load",
    description="staging.* → dwh.* : nettoyage et typage des données brutes Debezium",
    schedule_interval="*/15 * * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["ecommerce", "dwh"],
) as dag:

    # ── 0. Initialisation des schémas ──────────────────────────────────────────
    init_schemas = PostgresOperator(
        task_id="init_schemas",
        postgres_conn_id=CONN_ID,
        sql="""
            CREATE SCHEMA IF NOT EXISTS staging;
            CREATE SCHEMA IF NOT EXISTS dwh;
            CREATE SCHEMA IF NOT EXISTS dmart;
        """,
    )

    # ── 1. Chargement DWH — 7 tables en parallèle ─────────────────────────────

    load_admins = PostgresOperator(
        task_id="load_admins",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dwh.admins CASCADE;
            CREATE TABLE dwh.admins AS
            SELECT
                id                                              AS admin_id,
                email,
                first_name,
                last_name,
                (is_active = 1)                                 AS is_active,
                TO_TIMESTAMP("__source_ts_ms" / 1000.0)         AS source_updated_at
            FROM staging.admins
            WHERE COALESCE("__deleted", 'false') = 'false';
        """,
    )

    load_customers = PostgresOperator(
        task_id="load_customers",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dwh.customers CASCADE;
            CREATE TABLE dwh.customers AS
            SELECT
                id                                              AS customer_id,
                email,
                first_name,
                last_name,
                phone,
                address,
                (is_active = 1)                                 AS is_active,
                TO_TIMESTAMP("__source_ts_ms" / 1000.0)         AS source_updated_at
            FROM staging.customers
            WHERE COALESCE("__deleted", 'false') = 'false';
        """,
    )

    load_items = PostgresOperator(
        task_id="load_items",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dwh.items CASCADE;
            CREATE TABLE dwh.items AS
            SELECT
                id                                              AS item_id,
                title,
                description,
                image_url,
                price_ht::NUMERIC(10, 2)                        AS price_ht,
                tva_rate::NUMERIC(5, 2)                         AS tva_rate,
                price_ttc::NUMERIC(10, 2)                       AS price_ttc,
                quantity::INTEGER                               AS quantity,
                TO_TIMESTAMP("__source_ts_ms" / 1000.0)         AS source_updated_at
            FROM staging.items
            WHERE COALESCE("__deleted", 'false') = 'false';
        """,
    )

    load_orders = PostgresOperator(
        task_id="load_orders",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dwh.orders CASCADE;
            CREATE TABLE dwh.orders AS
            SELECT
                id                                              AS order_id,
                customer_id,
                status,
                total_ht::NUMERIC(10, 2)                        AS total_ht,
                total_ttc::NUMERIC(10, 2)                       AS total_ttc,
                TO_TIMESTAMP("__source_ts_ms" / 1000.0)         AS source_updated_at
            FROM staging.orders
            WHERE COALESCE("__deleted", 'false') = 'false';
        """,
    )

    load_order_items = PostgresOperator(
        task_id="load_order_items",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dwh.order_items CASCADE;
            CREATE TABLE dwh.order_items AS
            SELECT
                id                                              AS order_item_id,
                order_id,
                item_id,
                quantity::INTEGER                               AS quantity,
                unit_price_ht::NUMERIC(10, 2)                   AS unit_price_ht,
                unit_price_ttc::NUMERIC(10, 2)                  AS unit_price_ttc,
                (quantity * unit_price_ht)::NUMERIC(10, 2)      AS line_total_ht,
                (quantity * unit_price_ttc)::NUMERIC(10, 2)     AS line_total_ttc
            FROM staging.order_items
            WHERE COALESCE("__deleted", 'false') = 'false';
        """,
    )

    load_payments = PostgresOperator(
        task_id="load_payments",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dwh.payments CASCADE;
            CREATE TABLE dwh.payments AS
            SELECT
                id                                              AS payment_id,
                order_id,
                amount::NUMERIC(10, 2)                          AS amount,
                status                                          AS payment_status,
                payment_method,
                transaction_id,
                TO_TIMESTAMP("__source_ts_ms" / 1000.0)         AS source_updated_at
            FROM staging.payments
            WHERE COALESCE("__deleted", 'false') = 'false';
        """,
    )

    load_invoices = PostgresOperator(
        task_id="load_invoices",
        postgres_conn_id=CONN_ID,
        sql="""
            DROP TABLE IF EXISTS dwh.invoices CASCADE;
            CREATE TABLE dwh.invoices AS
            SELECT
                id                                              AS invoice_id,
                order_id,
                invoice_number,
                TO_TIMESTAMP(issued_at / 1000.0)                AS issued_at,
                TO_TIMESTAMP(due_date / 1000.0)                 AS due_date,
                total_ht::NUMERIC(10, 2)                        AS total_ht,
                total_tva::NUMERIC(10, 2)                       AS total_tva,
                total_ttc::NUMERIC(10, 2)                       AS total_ttc,
                TO_TIMESTAMP("__source_ts_ms" / 1000.0)         AS source_updated_at
            FROM staging.invoices
            WHERE COALESCE("__deleted", 'false') = 'false';
        """,
    )

    # ── 2. Synchronisation + déclenchement du DAG DMART ───────────────────────
    dwh_done = EmptyOperator(task_id="dwh_done")

    trigger_dmart = TriggerDagRunOperator(
        task_id="trigger_dmart_load",
        trigger_dag_id="ecommerce_dmart_load",
        wait_for_completion=False,
    )

    # ── Dépendances ────────────────────────────────────────────────────────────
    dwh_tasks = [
        load_admins,
        load_customers,
        load_items,
        load_orders,
        load_order_items,
        load_payments,
        load_invoices,
    ]

    for task in dwh_tasks:
        init_schemas >> task >> dwh_done

    dwh_done >> trigger_dmart
