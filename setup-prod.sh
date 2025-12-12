#!/bin/bash
# Production Environment Setup Script for Verc Backend
# Run this script to set up all prerequisites for production deployment

set -e  # Exit on error

PROJECT_ID="verc-prod"
REGION="us-east4"
SERVICE_NAME="verc-app-prod"
REPOSITORY="verc-app-prod"
SERVICE_ACCOUNT="github-ci@verc-prod.iam.gserviceaccount.com"
WORKLOAD_IDENTITY_PROVIDER="projects/391319920980/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
GITHUB_REPO="Verc-ai/verc-backend-service"

echo "🚀 Setting up Production Environment"
echo "===================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Step 1: Set project
echo "📋 Step 1: Setting GCP project..."
gcloud config set project "$PROJECT_ID"
echo "✅ Project set to $PROJECT_ID"
echo ""

# Step 2: Enable APIs
echo "📋 Step 2: Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudtasks.googleapis.com \
  iamcredentials.googleapis.com \
  --project="$PROJECT_ID"
echo "✅ APIs enabled"
echo ""

# Step 3: Create Artifact Registry repository
echo "📋 Step 3: Creating Artifact Registry repository..."
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

# Step 4: Verify service account exists
echo "📋 Step 4: Verifying service account..."
if gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project="$PROJECT_ID" &>/dev/null; then
  echo "✅ Service account exists: $SERVICE_ACCOUNT"
else
  echo "❌ Service account not found: $SERVICE_ACCOUNT"
  echo "   Please create it first or update the SERVICE_ACCOUNT variable"
  exit 1
fi
echo ""

# Step 5: Set up Workload Identity Pool binding
echo "📋 Step 5: Setting up Workload Identity Pool binding..."
MEMBER="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_PROVIDER}/attribute.repository/${GITHUB_REPO}"

# Check if binding exists
if gcloud iam service-accounts get-iam-policy "$SERVICE_ACCOUNT" --project="$PROJECT_ID" 2>/dev/null | grep -q "workloadIdentityUser"; then
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

# Step 6: Verify service account permissions
echo "📋 Step 6: Verifying service account permissions..."
echo "   Checking IAM bindings for $SERVICE_ACCOUNT..."
gcloud projects get-iam-policy "$PROJECT_ID" \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${SERVICE_ACCOUNT}" \
  --format="table(bindings.role)" || echo "⚠️  Could not list permissions (this is okay if you don't have permission)"
echo ""

# Step 7: Create Cloud Tasks queue (optional)
echo "📋 Step 7: Creating Cloud Tasks queue..."
QUEUE_NAME="transcription-queue-prod-v2"
if gcloud tasks queues describe "$QUEUE_NAME" --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
  echo "✅ Queue $QUEUE_NAME already exists"
else
  echo "   Creating queue $QUEUE_NAME..."
  gcloud tasks queues create "$QUEUE_NAME" \
    --location="$REGION" \
    --project="$PROJECT_ID" || echo "⚠️  Could not create queue (may need additional permissions)"
  echo "✅ Queue created (or skipped if permissions insufficient)"
fi
echo ""

# Step 8: List required secrets
echo "📋 Step 8: Required secrets in Secret Manager"
echo "   The following secrets need to exist in Secret Manager:"
echo "   - supabase-url"
echo "   - supabase-anon-key"
echo "   - supabase-service-role-key"
echo "   - openai-api-key"
echo "   - anthropic-api-key"
echo "   - assemblyai-api-key"
echo "   - twilio-account-sid"
echo "   - twilio-auth-token"
echo "   - twilio-phone-number"
echo "   - TWILIO_WEBHOOK_BASE_URL"
echo ""
echo "   Checking existing secrets..."
EXISTING_SECRETS=$(gcloud secrets list --project="$PROJECT_ID" --format="value(name)" 2>/dev/null || echo "")
if [ -z "$EXISTING_SECRETS" ]; then
  echo "   ⚠️  No secrets found. You'll need to create them manually."
else
  echo "   Existing secrets:"
  echo "$EXISTING_SECRETS" | while read -r secret; do
    echo "     - $secret"
  done
fi
echo ""

# Step 9: Summary
echo "===================================="
echo "✅ Setup Complete!"
echo "===================================="
echo ""
echo "Next steps:"
echo "1. Create any missing secrets in Secret Manager"
echo "2. Verify service account has required IAM roles:"
echo "   - Artifact Registry Administrator"
echo "   - Cloud Run Admin"
echo "   - Secret Manager Secret Accessor"
echo "   - Service Account User"
echo ""
echo "3. Deploy via GitHub Actions:"
echo "   - Go to Actions → Deploy workflow"
echo "   - Run workflow with 'production' environment"
echo ""
echo "Service will be created automatically on first deployment."
echo ""
