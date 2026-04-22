-- Initialisation des schémas du Data Warehouse
-- Exécuté automatiquement au premier démarrage du conteneur postgres-dwh

-- staging : données brutes injectées par le JDBC Sink (Debezium → Kafka → PostgreSQL)
CREATE SCHEMA IF NOT EXISTS staging;

-- dwh : données nettoyées et typées par Airflow (couche intermédiaire)
CREATE SCHEMA IF NOT EXISTS dwh;

-- dmart : tables analytiques matérialisées par Airflow (couche Data Mart)
CREATE SCHEMA IF NOT EXISTS dmart;
