#!/bin/bash
# Setup script to create .env file from template

echo "Setting up .env file for Django backend..."

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists. Backing up to .env.backup"
    cp .env .env.backup
fi

# Create .env from example
cp env.example .env

echo "✅ Created .env file from env.example"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file and add your actual configuration values"
echo "2. Make sure to set a strong SECRET_KEY for production"
echo "3. Update all API keys and service URLs"
echo ""
echo "To edit: nano .env  or  vim .env"

