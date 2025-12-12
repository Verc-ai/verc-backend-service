#!/bin/bash
# Fix Workload Identity Pool binding for production

set -e

PROJECT_ID="verc-prod"
SERVICE_ACCOUNT="github-ci@verc-prod.iam.gserviceaccount.com"
WORKLOAD_IDENTITY_PROVIDER="projects/391319920980/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
GITHUB_REPO="Verc-ai/verc-backend-service"

echo "🔧 Fixing Workload Identity Pool Binding"
echo "========================================"
echo ""

# Construct the member string
MEMBER="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_PROVIDER}/attribute.repository/${GITHUB_REPO}"

echo "Service Account: $SERVICE_ACCOUNT"
echo "Member: $MEMBER"
echo ""

# Check current bindings
echo "📋 Checking current bindings..."
CURRENT_POLICY=$(gcloud iam service-accounts get-iam-policy "$SERVICE_ACCOUNT" --project="$PROJECT_ID" 2>&1)

if echo "$CURRENT_POLICY" | grep -q "workloadIdentityUser"; then
  echo "✅ Workload Identity binding exists"
  echo ""
  echo "Current bindings:"
  echo "$CURRENT_POLICY" | grep -A 5 "workloadIdentityUser"
else
  echo "❌ Workload Identity binding NOT found"
  echo ""
  echo "Adding binding..."
  gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT" \
    --project="$PROJECT_ID" \
    --role="roles/iam.workloadIdentityUser" \
    --member="$MEMBER"
  
  echo ""
  echo "✅ Binding added!"
fi

echo ""
echo "📋 Verifying binding..."
VERIFIED=$(gcloud iam service-accounts get-iam-policy "$SERVICE_ACCOUNT" --project="$PROJECT_ID" 2>&1 | grep -c "workloadIdentityUser" || echo "0")

if [ "$VERIFIED" -gt 0 ]; then
  echo "✅ Verification successful - binding is configured"
else
  echo "❌ Verification failed - binding may not be correct"
  echo ""
  echo "Please check:"
  echo "1. Service account exists: $SERVICE_ACCOUNT"
  echo "2. Repository name is correct: $GITHUB_REPO"
  echo "3. Workload Identity Pool exists"
fi

echo ""
echo "========================================"
echo "Done!"
echo ""
