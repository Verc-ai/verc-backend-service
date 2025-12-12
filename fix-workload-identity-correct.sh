#!/bin/bash
# Fix Workload Identity Pool binding for production
# Using the correct project number from existing bindings

set -e

PROJECT_ID="verc-prod"
SERVICE_ACCOUNT="github-ci@verc-prod.iam.gserviceaccount.com"
# Using project 480289563704 (from existing binding) instead of 391319920980
WORKLOAD_IDENTITY_PROVIDER="projects/480289563704/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
GITHUB_REPO="Verc-ai/verc-backend-service"

echo "🔧 Fixing Workload Identity Pool Binding"
echo "========================================"
echo ""

# Construct the member string with repository attribute
MEMBER="principalSet://iam.googleapis.com/projects/480289563704/locations/global/workloadIdentityPools/github-pool/attribute.repository/${GITHUB_REPO}"

echo "Service Account: $SERVICE_ACCOUNT"
echo "Member: $MEMBER"
echo ""

# Check current bindings
echo "📋 Checking current bindings..."
CURRENT_POLICY=$(gcloud iam service-accounts get-iam-policy "$SERVICE_ACCOUNT" --project="$PROJECT_ID" 2>&1)

if echo "$CURRENT_POLICY" | grep -q "attribute.repository/${GITHUB_REPO}"; then
  echo "✅ Repository-specific binding already exists"
  echo ""
  echo "Current repository binding:"
  echo "$CURRENT_POLICY" | grep -A 2 "attribute.repository"
else
  echo "❌ Repository-specific binding NOT found"
  echo ""
  echo "Adding repository-specific binding..."
  gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT" \
    --project="$PROJECT_ID" \
    --role="roles/iam.workloadIdentityUser" \
    --member="$MEMBER"
  
  echo ""
  echo "✅ Repository-specific binding added!"
fi

echo ""
echo "📋 Verifying all bindings..."
gcloud iam service-accounts get-iam-policy "$SERVICE_ACCOUNT" --project="$PROJECT_ID"

echo ""
echo "========================================"
echo "Done!"
echo ""
echo "Note: You may have both repository_owner and repository bindings."
echo "The repository-specific binding is more secure and should work for GitHub Actions."
