#!/bin/sh
# Waits for Kafka Connect REST API then registers all connectors.
# Always deletes and re-registers to ensure the latest config is applied.

CONNECT_URL="http://kafka-connect:8083"

echo "Waiting for Kafka Connect to be fully ready..."
until curl -sf "${CONNECT_URL}/connectors" > /dev/null; do
  echo "  not ready yet, retrying in 5s..."
  sleep 5
done
echo "Kafka Connect is ready."

register() {
  local name=$1
  local file=$2

  # Delete if already exists to ensure config changes are always applied
  status=$(curl -so /dev/null -w "%{http_code}" "${CONNECT_URL}/connectors/${name}")
  if [ "$status" = "200" ]; then
    echo "[DELETE] Connector '${name}' already exists, deleting before re-register..."
    curl -s -X DELETE "${CONNECT_URL}/connectors/${name}"
    sleep 2
  fi

  echo "[REGISTER] ${name}..."
  response=$(curl -s -o /tmp/response.json -w "%{http_code}" \
    -X POST "${CONNECT_URL}/connectors" \
    -H "Content-Type: application/json" \
    -d @"${file}")

  if [ "$response" = "201" ] || [ "$response" = "200" ]; then
    echo "[OK] ${name} registered (HTTP ${response})"
  else
    echo "[ERROR] ${name} failed (HTTP ${response})"
    cat /tmp/response.json
    exit 1
  fi
}

register "mariadb-ecommerce-source" "/connectors/source-mariadb.json"
register "postgres-ecommerce-sink"  "/connectors/sink-postgres.json"

echo "All connectors registered successfully."
