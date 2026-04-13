---
name: docker
description: >
  Rules and best practices for containerizing applications with Docker and Docker Compose.
  Use this skill when creating or modifying Dockerfiles, writing docker-compose.yml, 
  optimizing image builds, or debugging containerized environments.
---

# Docker — Containerization Best Practices

## 📦 Fichiers de base

Chaque projet conteneurisé doit posséder à sa racine un `Dockerfile`, un `.dockerignore` et un `docker-compose.yml`.

Le `.dockerignore` est **obligatoire** pour ne pas alourdir le contexte de build :
```text
.git
__pycache__
*.pyc
.env
venv/
.pytest_cache/
node_modules/
⚡ Layer Caching — Optimisation du Build
Always separate dependency installation from source code copying to maximize Docker cache hit rate.

Dockerfile
# ✅ Bon — Le cache est préservé si le code change mais pas les dépendances
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/

# ❌ Mauvais — Re-télécharge toutes les dépendances à chaque modification de code
COPY . /app/
RUN pip install -r requirements.txt
🏗️ Dockerfile Design
Image de base
Ne jamais utiliser le tag latest.

Toujours piner la version majeure et mineure.

Préférer les versions slim ou alpine (attention avec Python, slim est souvent plus stable qu'Alpine pour les dépendances C).

Dockerfile
# ✅ Bon
FROM python:3.11-slim

# ❌ Mauvais
FROM python:latest
Multi-stage Builds
Utilisez le multi-stage build pour les langages compilés (Go, Node.js/Next.js) afin de ne pas inclure les outils de build dans l'image de production.

Dockerfile
# Stage 1: Build
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Production
FROM node:20-slim
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
CMD ["node", "dist/index.js"]
🔒 Sécurité : Rootless par défaut
By default, Docker runs processes as root. This is a critical security flaw. Always create a dedicated unprivileged user.

Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Création d'un utilisateur non-root
RUN useradd -m appuser
USER appuser

COPY --chown=appuser:appuser . .

CMD ["python", "main.py"]
🐙 Docker Compose Rules
Always name your containers explicitly using container_name.

Use depends_on with condition: service_healthy for strict startup ordering (e.g., waiting for the database to be ready).

Never hardcode passwords; always map them via .env files.

YAML
version: '3.8'

services:
  database:
    image: postgres:15
    container_name: app_database
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    container_name: app_api
    depends_on:
      database:
        condition: service_healthy
🛠️ Commandes utiles
Bash
docker-compose up -d --build  # Démarre en tâche de fond et force la reconstruction
docker-compose logs -f api    # Suit les logs du service 'api' en direct
docker exec -it app_api bash  # Ouvre un terminal dans le conteneur en cours d'exécution
docker system prune -a        # ⚠️ Nettoie toutes les images et conteneurs inutilisés
🚫 Hard Rules
Never use the latest tag in a Dockerfile.

Never run your application as the root user in production images.

Never store secrets or API keys in the Dockerfile; use environment variables at runtime.

Never write a Dockerfile without an accompanying .dockerignore.

Always split COPY requirements.txt and COPY . to utilize layer caching.