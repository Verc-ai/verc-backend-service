#!/bin/bash
# Simple script to run Django backend locally

set -e

echo "🚀 Starting Django Backend Service"
echo "===================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python3.12 -m venv venv
    echo "✅ Virtual environment created"
    echo ""
    echo "📦 Installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements-dev.txt -q
    echo "✅ Dependencies installed"
    echo ""
else
    echo "✅ Virtual environment found"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "   Creating from env.example..."
    if [ -f "env.example" ]; then
        cp env.example .env
        echo "   ✅ Created .env file - please update with your values"
    else
        echo "   ❌ env.example not found either"
        exit 1
    fi
fi

# Run Django checks
echo ""
echo "🔍 Running Django system checks..."
python manage.py check --deploy 2>/dev/null || python manage.py check

if [ $? -eq 0 ]; then
    echo "✅ Django configuration is valid"
else
    echo "❌ Django configuration has issues"
    exit 1
fi

echo ""
echo "🌐 Starting development server on http://localhost:4000"
echo "   Press Ctrl+C to stop"
echo ""
echo "📡 Available endpoints:"
echo "   - Health: http://localhost:4000/health"
echo "   - Root: http://localhost:4000/"
echo "   - API Auth: http://localhost:4000/api/auth/"
echo "   - API Twilio: http://localhost:4000/api/twilio/"
echo ""

# Start the server
python manage.py runserver 0.0.0.0:4000

