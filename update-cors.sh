#!/bin/bash
# Update backend CORS settings to allow frontend domains

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🔧 Updating Backend CORS Settings"
echo "==================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Update env.example
if [ -f "env.example" ]; then
    echo -e "${BLUE}Updating env.example...${NC}"
    
    # Backup
    cp env.example env.example.backup
    
    # Update CORS_ALLOWED_ORIGINS
    if grep -q "CORS_ALLOWED_ORIGINS=" env.example; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' 's|CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://app.verc.ai,https://www.verc.ai,https://verc.ai|' env.example
        else
            sed -i 's|CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://app.verc.ai,https://www.verc.ai,https://verc.ai|' env.example
        fi
        echo -e "${GREEN}✅ Updated env.example CORS settings${NC}"
    fi
fi

# Update .env if it exists
if [ -f ".env" ]; then
    echo -e "${BLUE}Updating .env...${NC}"
    
    # Backup
    cp .env .env.backup
    
    # Update CORS_ALLOWED_ORIGINS
    if grep -q "CORS_ALLOWED_ORIGINS=" .env; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' 's|CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://app.verc.ai,https://www.verc.ai,https://verc.ai|' .env
        else
            sed -i 's|CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://app.verc.ai,https://www.verc.ai,https://verc.ai|' .env
        fi
        echo -e "${GREEN}✅ Updated .env CORS settings${NC}"
    else
        echo "CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://app.verc.ai,https://www.verc.ai,https://verc.ai" >> .env
        echo -e "${GREEN}✅ Added CORS settings to .env${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  .env file not found. Create it from env.example${NC}"
fi

echo ""
echo -e "${GREEN}✅ CORS settings update complete!${NC}"
echo ""
echo "Note: If you're using Cloud Run, update the environment variable there:"
echo "  gcloud run services update verc-app-prod \\"
echo "    --update-env-vars CORS_ALLOWED_ORIGINS='http://localhost:3000,http://localhost:5173,https://app.verc.ai,https://www.verc.ai,https://verc.ai' \\"
echo "    --region us-east4 \\"
echo "    --project verc-prod"
echo ""
