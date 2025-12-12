#!/bin/bash
# Production Setup - Run this after authenticating with gcloud
# First run: gcloud auth login && gcloud auth application-default login

set -e

PROJECT_ID="verc-prod"
REGION="us-east4"
SERVICE_NAME="verc-app-prod"
REPOSITORY="verc-app-prod"
SERVICE_ACCOUNT="github-ci@verc-prod.iam.gserviceaccount.com"
WORKLOAD_IDENTITY_PROVIDER="projects/391319920980/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
GITHUB_REPO="Verc-ai/verc-backend-service"

echo "🚀 Setting up Production Environment"
echo "===================================="
echo ""

# Step 1: Enable APIs
echo "📋 Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudtasks.googleapis.com \
  iamcredentials.googleapis.com \
  --project="$PROJECT_ID"
echo "✅ APIs enabled"
echo ""

# Step 2: Create Artifact Registry repository
echo "📋 Creating Artifact Registry repository..."
if gcloud artifacts repositories describe "$REPOSITORY" --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
  echo "✅ Repository $REPOSITORY already exists"
else
  gcloud artifacts repositories create "$REPOSITORY" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Production Docker images for Verc backend" \
    --project="$PROJECT_ID"
  echo "✅ Repository $REPOSITORY created"
fi
echo ""

# Step 3: Verify service account
echo "📋 Verifying service account..."
if gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project="$PROJECT_ID" &>/dev/null; then
  echo "✅ Service account exists: $SERVICE_ACCOUNT"
else
  echo "❌ Service account not found: $SERVICE_ACCOUNT"
  exit 1
fi
echo ""

# Step 4: Set up Workload Identity Pool binding
echo "📋 Setting up Workload Identity Pool binding..."
MEMBER="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_PROVIDER}/attribute.repository/${GITHUB_REPO}"

# Check if binding exists
EXISTING_BINDING=$(gcloud iam service-accounts get-iam-policy "$SERVICE_ACCOUNT" --project="$PROJECT_ID" 2>/dev/null | grep -c "workloadIdentityUser" || echo "0")

if [ "$EXISTING_BINDING" -gt 0 ]; then
  echo "✅ Workload Identity binding already exists"
else
  echo "   Adding Workload Identity binding..."
  gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT" \
    --project="$PROJECT_ID" \
    --role="roles/iam.workloadIdentityUser" \
    --member="$MEMBER"
  echo "✅ Workload Identity binding added"
fi
echo ""

# Step 5: Create Cloud Tasks queue
echo "📋 Creating Cloud Tasks queue..."
QUEUE_NAME="transcription-queue-prod-v2"
if gcloud tasks queues describe "$QUEUE_NAME" --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
  echo "✅ Queue $QUEUE_NAME already exists"
else
  gcloud tasks queues create "$QUEUE_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" || echo "⚠️  Could not create queue (may need additional permissions)"
  echo "✅ Queue created or skipped"
fi
echo ""

# Step 6: List secrets
echo "📋 Checking secrets..."
echo "Required secrets:"
REQUIRED_SECRETS=(
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

EXISTING_SECRETS=$(gcloud secrets list --project="$PROJECT_ID" --format="value(name)" 2>/dev/null || echo "")

for secret in "${REQUIRED_SECRETS[@]}"; do
  if echo "$EXISTING_SECRETS" | grep -q "^${secret}$"; then
    echo "  ✅ $secret"
  else
    echo "  ❌ $secret - MISSING"
  fi
done
echo ""

echo "===================================="
echo "✅ Infrastructure setup complete!"
echo "===================================="
echo ""
echo "Next steps:"
echo "1. Create missing secrets using: ./setup-prod-secrets.sh"
echo "2. Or create them manually in GCP Console"
echo "3. Deploy via GitHub Actions workflow"
echo ""
