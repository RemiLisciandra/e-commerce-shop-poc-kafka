# ShopItem — E-commerce + Data Pipeline (Debezium / Kafka / Airflow)

Application e-commerce complète avec pipeline de données temps réel.  
Les modifications en base MariaDB sont capturées via **Debezium CDC**, transitent par **Kafka**, sont répliquées dans **PostgreSQL** (schéma `staging`), puis transformées par **Apache Airflow** en couches DWH (`dwh.*`) et Data Mart analytiques (`dmart.*`).

---

## Architecture

```
┌──────────────┐      binlogs       ┌──────────────┐       topics       ┌──────────────────┐
│   MariaDB    │ ──────────────────▶ │    Kafka      │ ──────────────────▶ │    PostgreSQL    │
│  (OLTP)      │     Debezium CDC    │   (Broker)    │    JDBC Sink       │ schema: staging  │
└──────────────┘                     └──────────────┘                     └────────┬─────────┘
       ▲                                                                           │
       │                                                              Airflow DAG (*/15 min)
┌──────┴───────┐                                                   ┌───────────────▼─────────────┐
│   FastAPI    │                                                   │  dwh.stg_*   (7 tables)     │
│   (Shop)     │                                                   │  dmart.mart_* (6 tables)    │
└──────────────┘                                                   └─────────────────────────────┘
```

---

## Services

| Service           | Image                    | Port    | Description                                     |
| ----------------- | ------------------------ | ------- | ----------------------------------------------- |
| `mariadb`         | `mariadb:10.11`          | `3306`  | Base de données OLTP avec binlogs ROW activés   |
| `api`             | Build `./api`            | `8000`  | Application FastAPI (e-commerce + admin)        |
| `adminer`         | `adminer:4.8.1`          | `8080`  | Interface d'administration de la BDD            |
| `zookeeper`       | `cp-zookeeper:7.6.0`     | —       | Coordination Kafka                              |
| `kafka`           | `cp-kafka:7.6.0`         | `29092` | Broker de messages                              |
| `kafka-connect`   | Build `./kafka-connect`  | `8083`  | Debezium (source) + JDBC (sink)                 |
| `kafka-ui`        | `provectuslabs/kafka-ui` | `8081`  | Interface de monitoring Kafka                   |
| `postgres-dwh`      | `postgres:16`            | `5433`  | PostgreSQL DWH (schémas `staging` / `dwh` / `dmart`)          |
| `postgres-airflow`  | `postgres:16`            | `5434`  | Base de métadonnées Airflow                                   |
| `airflow-webserver` | `apache/airflow:2.9.2`   | `8082`  | Interface Web Airflow (DAGs, logs, statuts)                   |
| `airflow-scheduler` | `apache/airflow:2.9.2`   | —       | Planificateur Airflow (exécute les DAGs)                      |
| `airflow-init`      | `apache/airflow:2.9.2`   | —       | Initialisation Airflow (migrate DB + créer admin) (one-shot)  |
| `mariadb-setup`     | `mariadb:10.11`          | —       | Création de l'utilisateur Debezium (one-shot)                 |
| `connector-setup`   | `alpine/curl`            | —       | Enregistrement des connecteurs Kafka (one-shot)               |

---

## Prérequis

- **Docker** et **Docker Compose** installés
- Ports `3306`, `5433`, `5434`, `8000`, `8080`, `8081`, `8082`, `8083`, `29092` disponibles

---

## Commandes Docker

### Lancer tous les services

```bash
docker compose up --build -d
```

### Arrêter les services (données persistées)

```bash
docker compose down
```

### Reconstruire et relancer

```bash
docker compose down && docker compose up --build -d
```

### Voir les logs

```bash
# Tous les services
docker compose logs -f

# Un service spécifique
docker compose logs -f api
docker compose logs -f kafka-connect
```

### Vérifier l'état des services

```bash
docker compose ps
```

### Supprimer les volumes (reset complet des données)

```bash
docker compose down -v
```

---

## Commandes Kafka Connect

### Lister les connecteurs enregistrés

```bash
curl http://localhost:8083/connectors
```

### Vérifier le statut d'un connecteur

```bash
# Source (Debezium → MariaDB)
curl http://localhost:8083/connectors/mariadb-ecommerce-source/status

# Sink (Kafka → PostgreSQL)
curl http://localhost:8083/connectors/postgres-ecommerce-sink/status
```

### Redémarrer un connecteur

```bash
curl -X POST http://localhost:8083/connectors/mariadb-ecommerce-source/restart
```

### Supprimer et recréer un connecteur

```bash
curl -X DELETE http://localhost:8083/connectors/mariadb-ecommerce-source
# Puis relancer le setup :
docker compose restart connector-setup
```

---

## Commandes Airflow

Airflow tourne en continu avec un schedule `*/15 * * * *`. Le DAG peut aussi être déclenché manuellement.

### Accéder à l'interface Web

`http://localhost:8082` — identifiants : `admin` / `admin`

### Déclencher le DAG manuellement

```bash
# Via l'UI : bouton "Trigger DAG" sur le DAG ecommerce_transformations

# Via CLI :
docker compose exec airflow-scheduler airflow dags trigger ecommerce_transformations
```

### Voir les logs d'exécution

```bash
docker compose logs -f airflow-scheduler
docker compose logs -f airflow-webserver
```

### Vérifier l'état du DAG

```bash
docker compose exec airflow-scheduler airflow dags list
docker compose exec airflow-scheduler airflow tasks list ecommerce_transformations
```

### Mettre le DAG en pause / reprendre

```bash
docker compose exec airflow-scheduler airflow dags pause ecommerce_transformations
docker compose exec airflow-scheduler airflow dags unpause ecommerce_transformations
```

---

## Tests

L'API dispose d'une suite de **150 tests** avec **100 % de couverture** de code.

### Installer les dépendances de test

```bash
cd api
pip install -r requirements.txt
```

### Lancer les tests

```bash
python -m pytest tests/ -v
```

### Lancer les tests avec couverture

```bash
python -m pytest tests/ --cov=. --cov-config=.coveragerc --cov-report=term-missing
```

### Générer un rapport HTML de couverture

```bash
python -m pytest tests/ --cov=. --cov-config=.coveragerc --cov-report=html
open htmlcov/index.html
```

> Les tests utilisent une base SQLite in-memory et ne nécessitent ni Docker ni MariaDB.

---

## Accès aux interfaces

| Interface              | URL                               | Identifiants                                                                                                   |
| ---------------------- | --------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Boutique**           | http://localhost:8000             | Créer un compte client                                                                                         |
| **Admin**              | http://localhost:8000/admin/login | `admin@shop.com` / `admin123`                                                                                  |
| **Adminer** (BDD)      | http://localhost:8080             | Serveur : `mariadb` · Utilisateur : `ecommerce_user` · Mot de passe : `ecommercepassword` · Base : `ecommerce` |
| **Kafka UI**           | http://localhost:8081             | —                                                                                                              |
| **Kafka Connect REST** | http://localhost:8083             | —                                                                                                              |
| **Airflow**            | http://localhost:8082             | `admin` / `admin`                                                                                              |

### Identifiants complets (POC)

| Service                | Hôte / Serveur                    | Utilisateur         | Mot de passe                           | Base de données |
| ---------------------- | --------------------------------- | ------------------- | -------------------------------------- | --------------- |
| **Admin e-commerce**   | http://localhost:8000/admin/login | `admin@shop.com`    | `admin123`                             | —               |
| **MariaDB (app)**      | `mariadb:3306`                    | `ecommerce_user`    | `ecommercepassword`                    | `ecommerce`     |
| **MariaDB (root)**     | `mariadb:3306`                    | `root`              | `rootpassword`                         | `ecommerce`     |
| **MariaDB (Debezium)** | `mariadb:3306`                    | `debezium`          | `debeziumpassword`                     | `ecommerce`     |
| **PostgreSQL DWH**     | `postgres-dwh:5432`               | `dwh_user`          | `dwhpassword`                          | `ecommerce_dwh` |
| **PostgreSQL Airflow** | `localhost:5434`                  | `airflow`           | `airflow`                              | `airflow`       |
| **Airflow UI**         | http://localhost:8082             | `admin`             | `admin`                                | —               |
| **Adminer**            | http://localhost:8080             | Serveur : `mariadb` | `ecommerce_user` / `ecommercepassword` | `ecommerce`     |

> **Note** : pour se connecter au PostgreSQL DWH depuis Adminer, choisir le système **PostgreSQL**, serveur `postgres-dwh`, utilisateur `dwh_user`, mot de passe `dwhpassword`, base `ecommerce_dwh`.

---

## Fonctionnalités e-commerce

### Espace Admin (`/admin`)

- **Authentification admin** — connexion par email/mot de passe, cookie sécurisé `access_token`
- **CRUD Articles** — création, modification, suppression d'articles avec :
  - Titre, description
  - **Upload d'image** (stockage serveur dans `/app/uploads/`, nettoyage automatique à la suppression)
  - Prix HT, taux de TVA (0%, 5.5%, 10%, 20%), calcul automatique du TTC
  - Gestion du stock (quantité)
- **Seed automatique** — un compte admin (`admin@shop.com` / `admin123`) est créé au démarrage

### Espace Client (`/`)

- **Catalogue** — grille d'articles avec image, prix TTC/HT, indicateur de stock
- **Section "Commander à nouveau"** — en haut du catalogue, affiche les produits déjà achetés par le client connecté pour faciliter le réachat
- **Panier** (cookie, 7 jours) — ajout, modification de quantité, suppression, contrôle du stock max
- **Commande** — récapitulatif avant confirmation, décrémentation automatique du stock
- **Paiement automatique** — à la confirmation, un paiement fictif est enregistré (méthode aléatoire : carte, virement, PayPal)
- **Facturation automatique** — une facture est générée avec numéro unique (`INV-YYYYMMDD-XXXXXX`), échéance à 30 jours

### Espace Mon Compte (`/account`)

- **Historique de commandes** — liste de toutes les commandes avec détail des articles, statut, montants
- **Mes paiements** — tableau des paiements (transaction ID, méthode, statut, montant, date)
- **Mes factures** — tableau des factures (numéro, montants HT/TVA/TTC, date d'émission)
- **Téléchargement PDF** — chaque facture est téléchargeable en PDF avec détail des lignes, infos client et totaux

### Authentification Client

- **Inscription** avec recherche d'adresse française (API `api-adresse.data.gouv.fr`, autocomplétion)
- **Connexion / Déconnexion** — cookie sécurisé `customer_token` (8h)

---

## Pipeline de données

### 1. Capture (Debezium CDC)

Debezium lit les **binlogs MariaDB** en temps réel et publie chaque insertion, modification et suppression dans des topics Kafka.

**Tables capturées :**
`admins`, `customers`, `items`, `orders`, `order_items`, `payments`, `invoices`

**Configuration clé :**

- Mode snapshot : `initial` (copie complète au premier lancement, puis suivi incrémental)
- SMT `ExtractNewRecordState` : aplatit l'enveloppe Debezium, ajoute les champs `__op`, `__ts_ms`, `__source_ts_ms`
- Gestion des suppressions : mode `rewrite` (ajoute `__deleted = true` au lieu de supprimer)

### 2. Transport (Kafka)

Chaque table correspond à un topic Kafka :

- `ecommerce.ecommerce.items`
- `ecommerce.ecommerce.customers`
- `ecommerce.ecommerce.orders`
- etc.

### 3. Ingestion (JDBC Sink)

Le connecteur JDBC sink réplique les données vers **PostgreSQL** dans le schéma `staging` :

- Schéma cible : `staging` (tables brutes avec métadonnées Debezium `__deleted`, `__source_ts_ms`)
- Mode : `upsert` sur la colonne `id` (gère les créations et modifications)
- Auto-création des tables (`auto.create: true`)
- Auto-évolution du schéma (`auto.evolve: true`)

### 4. Transformation (Apache Airflow)

Le DAG `ecommerce_transformations` (schedule `*/15 * * * *`) exécute les transformations en deux couches successives.

#### Couche DWH — tables nettoyées (`dwh.stg_*`)

Nettoyage et typage des tables brutes du schéma `staging`. Filtrage des lignes supprimées (`__deleted = false`).

| Table                   | Description                                                     |
| ----------------------- | --------------------------------------------------------------- |
| `dwh.stg_admins`        | Comptes admin (id, email, nom, prénom, statut)                  |
| `dwh.stg_customers`     | Comptes clients (id, email, nom, prénom, téléphone, adresse)    |
| `dwh.stg_items`         | Articles (id, titre, prix HT/TTC, TVA, stock)                   |
| `dwh.stg_orders`        | Commandes (id, client, statut, totaux HT/TTC)                   |
| `dwh.stg_order_items`   | Lignes de commande + calcul `line_total_ht` / `line_total_ttc`  |
| `dwh.stg_payments`      | Paiements (id, commande, montant, méthode, statut, transaction) |
| `dwh.stg_invoices`      | Factures (id, numéro, commande, montants, dates)                |

#### Couche DMART — tables analytiques (`dmart.mart_*`)

Tables matérialisées prêtes pour la BI, reconstruites à chaque run Airflow.

| Table                          | Description                                                                              | Clé                       |
| ------------------------------ | ---------------------------------------------------------------------------------------- | ------------------------- |
| `dmart.mart_sales_daily`       | CA HT/TTC par jour, nombre de commandes, unités vendues, cumul glissant                  | `order_date`              |
| `dmart.mart_revenue_by_item`   | Revenus et quantités vendues par article, stock actuel                                   | `item_id`                 |
| `dmart.mart_customer_lifetime` | LTV client, panier moyen, segmentation (`no_order` / `one_time` / `recurring` / `loyal`) | `customer_id`             |
| `dmart.mart_customer_reorders` | Produits achetés par client : quantité totale, nombre de commandes, dernier achat        | `customer_id` + `item_id` |
| `dmart.mart_payments`          | Paiements enrichis avec infos client et commande                                         | `payment_id`              |
| `dmart.mart_invoices`          | Factures enrichies avec statut d'échéance (`overdue` / `on_time`)                        | `invoice_id`              |

#### Graphe du DAG

```
init_schemas
    ├── dwh_stg_admins ──────┐
    ├── dwh_stg_customers ───┤
    ├── dwh_stg_items ────────┤
    ├── dwh_stg_orders ───────┼──▶ dwh_done ──┬── dmart_sales_daily
    ├── dwh_stg_order_items ──┤              ├── dmart_revenue_by_item
    ├── dwh_stg_payments ─────┤              ├── dmart_customer_lifetime
    └── dwh_stg_invoices ─────┘              ├── dmart_customer_reorders
                                             ├── dmart_payments
                                             └── dmart_invoices
```

---

## Stack technique

| Composant        | Technologie                   | Version     |
| ---------------- | ----------------------------- | ----------- |
| Backend          | FastAPI + Jinja2 + SQLAlchemy | 0.104 / 2.0 |
| Base OLTP        | MariaDB                       | 10.11       |
| Data Warehouse   | PostgreSQL                    | 16          |
| CDC              | Debezium (MySQL connector)    | 2.5.4       |
| Streaming        | Apache Kafka (Confluent)      | 7.6.0       |
| Transformation   | Apache Airflow                | 2.9.2       |
| Connecteur Sink  | Confluent JDBC Sink           | 10.7.6      |
| CSS              | Tailwind CSS (CDN)            | —           |
| PDF              | fpdf2                         | 2.7.9       |
| Auth             | JWT (python-jose) + bcrypt    | —           |
| Conteneurisation | Docker Compose                | —           |

---

## Structure du projet

```
├── api/
│   ├── auth/                  # JWT + bcrypt (admin + customer)
│   ├── models/                # SQLAlchemy (7 tables)
│   ├── routers/
│   │   ├── admin/items.py     # CRUD articles (upload image)
│   │   ├── auth.py            # Login/logout admin
│   │   └── shop/
│   │       ├── account.py     # Historique, paiements, factures, PDF
│   │       ├── auth.py        # Login/register/logout client
│   │       ├── cart.py        # Panier (cookie)
│   │       ├── catalog.py     # Catalogue + suggestions réachat
│   │       └── orders.py      # Commande + paiement/facture auto
│   ├── templates/             # Jinja2 + Tailwind
│   ├── Dockerfile
│   └── requirements.txt
├── airflow/
│   └── dags/
│       └── ecommerce_transformations.py   # DAG : staging → dwh → dmart
├── postgres-dwh/
│   └── init.sql               # Création des schémas staging / dwh / dmart
├── kafka-connect/
│   ├── connectors/
│   │   ├── source-mariadb.json   # Debezium → MariaDB
│   │   ├── sink-postgres.json    # Kafka → PostgreSQL
│   │   └── register.sh           # Script d'enregistrement
│   └── Dockerfile
└── docker-compose.yml
```
