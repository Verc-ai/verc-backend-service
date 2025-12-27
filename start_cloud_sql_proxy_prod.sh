#!/bin/bash
# Start Cloud SQL Proxy for PRODUCTION database
# Connection: verc-prod:us-central1:verc-prod-pg

set -e

INSTANCE="verc-prod:us-central1:verc-prod-pg"
PORT=5433  # Using 5433 since 5432 is already in use

echo "═══════════════════════════════════════════════════════════════"
echo "Starting Cloud SQL Proxy for PRODUCTION"
echo "═══════════════════════════════════════════════════════════════"
echo "Instance: $INSTANCE"
echo "Port: $PORT"
echo ""
echo "⚠️  IMPORTANT: Update your .env to use:"
echo "   DB_HOST=127.0.0.1"
echo "   DB_PORT=$PORT"
echo ""

# Find cloud_sql_proxy
PROXY_CMD=""
if command -v cloud_sql_proxy &> /dev/null; then
    PROXY_CMD="cloud_sql_proxy"
elif command -v cloud-sql-proxy &> /dev/null; then
    PROXY_CMD="cloud-sql-proxy"
elif [ -f "./cloud_sql_proxy" ]; then
    PROXY_CMD="./cloud_sql_proxy"
elif [ -f "./cloud-sql-proxy" ]; then
    PROXY_CMD="./cloud-sql-proxy"
else
    echo "❌ Cloud SQL Proxy not found!"
    echo ""
    echo "Please install it:"
    echo "  macOS: brew install cloud-sql-proxy"
    echo "  Or download from: https://cloud.google.com/sql/docs/postgres/sql-proxy"
    exit 1
fi

echo "✅ Found Cloud SQL Proxy: $PROXY_CMD"
echo ""
echo "Starting proxy..."
echo "   Keep this terminal open while you run migrations"
echo "   Press Ctrl+C to stop"
echo ""

# Start the proxy
$PROXY_CMD $INSTANCE --port=$PORT

