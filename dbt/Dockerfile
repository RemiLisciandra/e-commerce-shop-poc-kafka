FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir dbt-postgres==1.8.0

WORKDIR /dbt
COPY . .

# Default: run dbt models. Override with: docker compose run --rm dbt dbt <command>
CMD ["dbt", "run", "--profiles-dir", "."]
