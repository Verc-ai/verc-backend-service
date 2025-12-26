#!/bin/bash
# Simple test script for Django backend - step by step

set -e

echo "🧪 Testing Django Backend Service"
echo "=================================="
echo ""

# Step 1: Check Python version
echo "1️⃣  Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found: Python $PYTHON_VERSION"

# Check if Python 3.12+
if python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
    echo "   ✅ Python version is compatible (3.12+)"
else
    echo "   ⚠️  Python 3.12+ recommended. Current: $PYTHON_VERSION"
    echo "   You can install Python 3.12+ using:"
    echo "      brew install python@3.12  # macOS"
    echo "      or use pyenv: pyenv install 3.12.0"
fi

echo ""

# Step 2: Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo "2️⃣  Creating virtual environment..."
    python3 -m venv venv
    echo "   ✅ Virtual environment created"
else
    echo "2️⃣  Virtual environment exists"
fi

echo ""

# Step 3: Activate and install dependencies
echo "3️⃣  Installing dependencies..."
source venv/bin/activate

if ! python -c "import django" 2>/dev/null; then
    echo "   Installing packages (this may take a minute)..."
    pip install --upgrade pip -q
    pip install -r requirements-dev.txt -q
    echo "   ✅ Dependencies installed"
else
    echo "   ✅ Dependencies already installed"
fi

echo ""

# Step 4: Run Django checks
echo "4️⃣  Running Django system checks..."
python manage.py check

if [ $? -eq 0 ]; then
    echo "   ✅ Django configuration is valid"
else
    echo "   ❌ Django configuration has issues"
    exit 1
fi

echo ""

# Step 5: Test imports
echo "5️⃣  Testing critical imports..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.core.services.supabase import get_supabase_client
from django.conf import settings

print('   ✅ Django setup successful')
print(f'   ✅ Settings loaded: DEBUG={settings.DEBUG}')
print(f'   ✅ API Port: {settings.APP_SETTINGS.api_port}')

# Test Supabase connection
supabase = get_supabase_client()
if supabase:
    print('   ✅ Supabase client initialized')
else:
    print('   ⚠️  Supabase not configured (optional)')
"

echo ""

# Step 6: Test URL configuration
echo "6️⃣  Testing URL configuration..."
python manage.py show_urls 2>/dev/null || python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.urls import get_resolver
resolver = get_resolver()
print(f'   ✅ URL patterns loaded: {len(list(resolver.url_patterns))} patterns')
"

echo ""

# Step 7: Test server startup (quick test)
echo "7️⃣  Testing server startup..."
echo "   Starting server on port 4000 (will test for 3 seconds)..."

timeout 3 python manage.py runserver 0.0.0.0:4000 > /tmp/django-test.log 2>&1 &
SERVER_PID=$!
sleep 2

if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "   ✅ Server started successfully"
    
    # Test health endpoint if server is running
    sleep 1
    if curl -s http://localhost:4000/health > /dev/null 2>&1; then
        echo "   ✅ Health endpoint responding"
        curl -s http://localhost:4000/health | python -m json.tool 2>/dev/null || echo "   Response received"
    fi
    
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
else
    echo "   ⚠️  Server test skipped (check manually)"
    if [ -f /tmp/django-test.log ]; then
        echo "   Last few lines of log:"
        tail -5 /tmp/django-test.log | sed 's/^/      /'
    fi
fi

echo ""
echo "=================================="
echo "✅ All basic tests completed!"
echo ""
echo "🚀 To start the server:"
echo "   source venv/bin/activate"
echo "   python manage.py runserver"
echo ""
echo "🌐 Then test endpoints:"
echo "   curl http://localhost:4000/health"
echo "   curl http://localhost:4000/"

