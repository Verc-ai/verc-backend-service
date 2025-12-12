#!/bin/bash
# Helper script to create or update secrets for production
# Usage: ./setup-prod-secrets.sh

set -e

PROJECT_ID="verc-prod"

echo "🔐 Production Secrets Setup"
echo "=========================="
echo ""

# List of required secrets
SECRETS=(
  "supabase-url"
  "supabase-anon-key"
  "supabase-service-role-key"
  "openai-api-key"
  "anthropic-api-key"
  "assemblyai-api-key"
  "twilio-account-sid"
  "twilio-auth-token"
  "twilio-phone-number"
  "TWILIO_WEBHOOK_BASE_URL"
)

echo "Checking existing secrets..."
echo ""

for secret in "${SECRETS[@]}"; do
  if gcloud secrets describe "$secret" --project="$PROJECT_ID" &>/dev/null; then
    echo "✅ $secret - exists"
  else
    echo "❌ $secret - MISSING"
    echo ""
    read -p "Do you want to create '$secret' now? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      read -sp "Enter the value for '$secret': " value
      echo ""
      echo -n "$value" | gcloud secrets create "$secret" \
        --data-file=- \
        --project="$PROJECT_ID" \
        --replication-policy="automatic"
      echo "✅ Created $secret"
    fi
    echo ""
  fi
done

echo ""
echo "=========================="
echo "✅ Secret check complete!"
echo ""
echo "To update an existing secret:"
echo "  echo -n 'new-value' | gcloud secrets versions add SECRET_NAME --data-file=- --project=verc-prod"
echo ""
