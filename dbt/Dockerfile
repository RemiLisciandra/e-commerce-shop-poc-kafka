FROM python:3.11-slim

RUN pip install --no-cache-dir dbt-postgres==1.8.0

WORKDIR /dbt
COPY . .

# Default: run dbt models. Override with: docker compose run --rm dbt dbt <command>
CMD ["dbt", "run", "--profiles-dir", "."]
