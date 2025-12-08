#!/bin/bash
# Test script for Django backend

set -e  # Exit on error

echo "🧪 Testing Django Backend Service"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating one...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
# Check Python version first
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
if python -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
    echo -e "${GREEN}✅ Python $PYTHON_VERSION is compatible (3.12+)${NC}"
else
    echo -e "${YELLOW}⚠️  Python 3.12+ recommended. Found: $PYTHON_VERSION${NC}"
fi

if ! python -c "import django" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Dependencies not installed. Installing...${NC}"
    pip install -q -r requirements-dev.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}✅ Dependencies already installed${NC}"
fi

echo ""
echo "🔍 Running Django system checks..."
python manage.py check --deploy || python manage.py check

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Django system checks passed${NC}"
else
    echo -e "${RED}❌ Django system checks failed${NC}"
    exit 1
fi

echo ""
echo "📊 Checking environment variables..."
python -c "
import os
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

print(f'  DJANGO_ENV: {os.getenv(\"DJANGO_ENV\", \"not set\")}')
print(f'  DEBUG: {settings.DEBUG}')
print(f'  API_PORT: {settings.APP_SETTINGS.api_port}')
print(f'  Supabase URL: {\"✅\" if settings.APP_SETTINGS.supabase.url else \"❌\"}')
print(f'  OpenAI Key: {\"✅\" if settings.APP_SETTINGS.ai.openai_api_key else \"❌\"}')
print(f'  Twilio SID: {\"✅\" if settings.APP_SETTINGS.twilio.account_sid else \"❌\"}')
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Environment configuration loaded${NC}"
else
    echo -e "${YELLOW}⚠️  Could not verify environment (this is OK if .env is missing)${NC}"
fi

echo ""
echo "🌐 Testing server startup (5 second test)..."
timeout 5 python manage.py runserver 0.0.0.0:4000 > /tmp/django-test.log 2>&1 &
SERVER_PID=$!
sleep 3

if ps -p $SERVER_PID > /dev/null; then
    echo -e "${GREEN}✅ Server started successfully${NC}"
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
else
    echo -e "${RED}❌ Server failed to start${NC}"
    echo "Last 20 lines of log:"
    tail -20 /tmp/django-test.log
    exit 1
fi

echo ""
echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "🚀 To start the server manually:"
echo "   1. Activate virtual environment: source venv/bin/activate"
echo "   2. Run server: python manage.py runserver"
echo "   3. Test health endpoint: curl http://localhost:4000/health"

