#!/bin/bash
# Deploy Django Backend to Cloud Run (Staging)

set -e  # Exit on error

PROJECT_ID="verc-staging"
REGION="us-east4"
SERVICE_NAME="verc-app-staging"
REPOSITORY="verc-app-staging"
IMAGE_NAME="django-backend"

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Get git commit hash for image tag
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
IMAGE_TAG="${GIT_HASH}"
FULL_IMAGE_NAME="us-east4-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "🚀 Deploying Django Backend to Cloud Run"
echo "=========================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "Image: ${FULL_IMAGE_NAME}"
echo ""

# Step 1: Build Docker image
echo "📦 Building Docker image for linux/amd64 (Cloud Run requirement)..."
docker build --platform linux/amd64 -t "${FULL_IMAGE_NAME}" .

# Step 2: Authenticate Docker to GCP
echo ""
echo "🔐 Authenticating Docker to GCP..."
gcloud auth configure-docker us-east4-docker.pkg.dev --quiet

# Step 3: Push image to Artifact Registry
echo ""
echo "⬆️  Pushing image to Artifact Registry..."
docker push "${FULL_IMAGE_NAME}"

# Step 4: Get service URL first (for CLOUD_RUN_SERVICE_URL env var)
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format 'value(status.url)' 2>/dev/null || echo "https://verc-app-staging-clw2hnetfa-uk.a.run.app")

# Step 5: Deploy to Cloud Run
echo ""
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${FULL_IMAGE_NAME}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --service-account "391319920980-compute@developer.gserviceaccount.com" \
  --add-cloudsql-instances verc-staging:us-central1:verc-staging-pg \
  --set-env-vars "NODE_ENV=production,ENVIRONMENT=staging,GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},GCP_TASK_QUEUE_NAME=transcription-queue-staging-v2,CLOUD_TASKS_ENABLED=true,CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL=cloud-tasks-invoker@${PROJECT_ID}.iam.gserviceaccount.com,ASSEMBLYAI_PII_REDACTION_ENABLED=true,ASSEMBLYAI_PII_SUBSTITUTION=entity_name,ASSEMBLYAI_GENERATE_REDACTED_AUDIO=true,DJANGO_ENV=production,CLOUD_RUN_SERVICE_URL=${SERVICE_URL}" \
  --set-secrets "SUPABASE_URL=supabase-url:latest,SUPABASE_ANON_KEY=supabase-anon-key:latest,SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key:latest,OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,ASSEMBLYAI_API_KEY=assemblyai-api-key:latest,TWILIO_ACCOUNT_SID=twilio-account-sid:latest,TWILIO_AUTH_TOKEN=twilio-auth-token:latest,TWILIO_PHONE_NUMBER=twilio-phone-number:latest,TWILIO_WEBHOOK_BASE_URL=TWILIO_WEBHOOK_BASE_URL:latest,BUFFALO_PBX_USERNAME=BUFFALO_PBX_USERNAME:latest,BUFFALO_PBX_PASSWORD=BUFFALO_PBX_PASSWORD:latest,BUFFALO_SIP_USERNAME=BUFFALO_SIP_USERNAME:latest,BUFFALO_SIP_PASSWORD=BUFFALO_SIP_PASSWORD:latest" \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5 \
  --concurrency 80 \
  --timeout 300 \
  --quiet

# Step 6: Get service URL (update after deployment)
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "=========================================="
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "🧪 Testing deployment..."
echo ""

# Test health endpoint
if curl -s -f "${SERVICE_URL}/health" > /dev/null; then
  echo "✅ Health check passed"
else
  echo "❌ Health check failed"
fi

echo ""
echo "📝 Next steps:"
echo "1. Update CLOUD_RUN_SERVICE_URL in your .env file:"
echo "   CLOUD_RUN_SERVICE_URL=${SERVICE_URL}"
echo ""
echo "2. Test Cloud Tasks by uploading a file"
echo "3. Check GCP Console for task execution:"
echo "   https://console.cloud.google.com/cloudtasks/queue/us-east4/transcription-queue-staging-v2/tasks?project=${PROJECT_ID}"

