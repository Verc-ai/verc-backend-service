#!/bin/bash
# Start Cloud SQL Proxy for staging database
# Connection: verc-staging:us-central1:verc-staging-pg

set -e

INSTANCE="verc-staging:us-central1:verc-staging-pg"
PORT=5432

echo "═══════════════════════════════════════════════════════════════"
echo "Starting Cloud SQL Proxy"
echo "═══════════════════════════════════════════════════════════════"
echo "Instance: $INSTANCE"
echo "Port: $PORT"
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
    echo "  brew install cloud-sql-proxy"
    echo ""
    echo "Or download from:"
    echo "  https://cloud.google.com/sql/docs/postgres/sql-proxy"
    exit 1
fi

echo "Using: $PROXY_CMD"
echo ""
echo "Starting proxy in background..."
echo "To stop it later, run: pkill -f cloud_sql_proxy"
echo ""

# Start proxy in background
# Newer cloud-sql-proxy uses different syntax
if [[ "$PROXY_CMD" == *"cloud-sql-proxy"* ]]; then
    # New syntax: cloud-sql-proxy INSTANCE --port PORT
    $PROXY_CMD $INSTANCE --port $PORT > /tmp/cloud_sql_proxy.log 2>&1 &
else
    # Old syntax: cloud_sql_proxy -instances=INSTANCE=tcp:PORT
    $PROXY_CMD -instances=$INSTANCE=tcp:$PORT > /tmp/cloud_sql_proxy.log 2>&1 &
fi
PROXY_PID=$!

# Wait a moment for it to start
sleep 2

# Check if it's running
if ps -p $PROXY_PID > /dev/null; then
    echo "✅ Cloud SQL Proxy started (PID: $PROXY_PID)"
    echo "   Logs: /tmp/cloud_sql_proxy.log"
    echo ""
    echo "You can now run security tests:"
    echo "  ./run_security_tests.sh staging"
    echo ""
    echo "To stop the proxy:"
    echo "  kill $PROXY_PID"
    echo "  or: pkill -f cloud_sql_proxy"
else
    echo "❌ Failed to start Cloud SQL Proxy"
    echo "Check logs: cat /tmp/cloud_sql_proxy.log"
    exit 1
fi

