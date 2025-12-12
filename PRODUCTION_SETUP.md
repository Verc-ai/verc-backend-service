# Production Environment Setup Guide

This guide will help you set up the production environment for the Verc backend service in the `verc-prod` GCP project.

## Prerequisites

- Access to the `verc-prod` GCP project
- `gcloud` CLI installed and authenticated
- Appropriate permissions (Project Owner or Editor)

## Step 1: Enable Required APIs

```bash
# Set the project
gcloud config set project verc-prod

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudtasks.googleapis.com \
  iamcredentials.googleapis.com
```

## Step 2: Create Artifact Registry Repository

```bash
# Create the Docker repository for production images
gcloud artifacts repositories create verc-app-prod \
  --repository-format=docker \
  --location=us-east4 \
  --description="Production Docker images for Verc backend" \
  --project=verc-prod

# Verify it was created
gcloud artifacts repositories list --location=us-east4 --project=verc-prod
```

## Step 3: Set Up Secrets in Secret Manager

Create all required secrets. You can either create them manually or copy from staging:

```bash
# List of required secrets:
# - supabase-url
# - supabase-anon-key
# - supabase-service-role-key
# - openai-api-key
# - anthropic-api-key
# - assemblyai-api-key
# - twilio-account-sid
# - twilio-auth-token
# - twilio-phone-number
# - TWILIO_WEBHOOK_BASE_URL

# Example: Create a secret (replace with actual values)
echo -n "your-secret-value" | gcloud secrets create supabase-url \
  --data-file=- \
  --project=verc-prod

# Or copy from staging (if secrets exist there)
# gcloud secrets versions access latest --secret="supabase-url" --project=verc-staging | \
#   gcloud secrets create supabase-url --data-file=- --project=verc-prod
```

**Required Secrets:**
1. `supabase-url` - Your Supabase project URL
2. `supabase-anon-key` - Supabase anonymous key
3. `supabase-service-role-key` - Supabase service role key
4. `openai-api-key` - OpenAI API key
5. `anthropic-api-key` - Anthropic API key
6. `assemblyai-api-key` - AssemblyAI API key
7. `twilio-account-sid` - Twilio account SID
8. `twilio-auth-token` - Twilio auth token
9. `twilio-phone-number` - Twilio phone number
10. `TWILIO_WEBHOOK_BASE_URL` - Twilio webhook base URL

## Step 4: Verify Workload Identity Pool Binding

Ensure the production service account is bound to the Workload Identity Pool:

```bash
# Check current bindings
gcloud iam service-accounts get-iam-policy \
  github-ci@verc-prod.iam.gserviceaccount.com \
  --project=verc-prod

# If not bound, add the binding:
gcloud iam service-accounts add-iam-policy-binding \
  github-ci@verc-prod.iam.gserviceaccount.com \
  --project=verc-prod \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/391319920980/locations/global/workloadIdentityPools/github-pool/attribute.repository/Verc-ai/verc-backend-service"
```

## Step 5: Verify Service Account Permissions

Ensure the service account has the required permissions:

```bash
# Check IAM policy for the project
gcloud projects get-iam-policy verc-prod \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:github-ci@verc-prod.iam.gserviceaccount.com"
```

**Required Roles:**
- `Artifact Registry Administrator` (or `roles/artifactregistry.writer`)
- `Cloud Run Admin` (or `roles/run.admin`)
- `Secret Manager Secret Accessor` (for accessing secrets)
- `Service Account User` (for Cloud Run service account)

## Step 6: (Optional) Create Cloud Tasks Queue

If you're using Cloud Tasks, create the queue:

```bash
# Create the Cloud Tasks queue
gcloud tasks queues create transcription-queue-prod-v2 \
  --location=us-east4 \
  --project=verc-prod

# Verify it was created
gcloud tasks queues list --location=us-east4 --project=verc-prod
```

## Step 7: (Optional) Pre-create Cloud Run Service

The workflow will automatically create the service on first deployment, but you can pre-create it:

```bash
# Create a placeholder service (will be updated on first deployment)
gcloud run deploy verc-app-prod \
  --image=us-east4-docker.pkg.dev/verc-prod/verc-app-prod/placeholder:latest \
  --region=us-east4 \
  --project=verc-prod \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=5 \
  --concurrency=80 \
  --timeout=300
```

**Note:** This is optional - the workflow will create it automatically on first deployment.

## Step 8: Verify Setup

Run these commands to verify everything is set up:

```bash
# 1. Verify Artifact Registry
gcloud artifacts repositories describe verc-app-prod \
  --location=us-east4 \
  --project=verc-prod

# 2. Verify secrets exist
gcloud secrets list --project=verc-prod

# 3. Verify service account exists
gcloud iam service-accounts describe github-ci@verc-prod.iam.gserviceaccount.com \
  --project=verc-prod

# 4. Verify Workload Identity binding
gcloud iam service-accounts get-iam-policy \
  github-ci@verc-prod.iam.gserviceaccount.com \
  --project=verc-prod | grep workloadIdentityUser

# 5. (Optional) Verify Cloud Tasks queue
gcloud tasks queues describe transcription-queue-prod-v2 \
  --location=us-east4 \
  --project=verc-prod
```

## Step 9: Deploy via GitHub Actions

Once everything is set up:

1. Go to your GitHub repository
2. Navigate to **Actions** → **Deploy** workflow
3. Click **Run workflow**
4. Select **production** from the environment dropdown
5. Click **Run workflow**

The workflow will:
- Build the Docker image
- Push to Artifact Registry
- Deploy to Cloud Run (creating the service if it doesn't exist)
- Run health checks

## Troubleshooting

### Service Account Authentication Issues

If you get "Unauthenticated request" errors:
1. Verify Workload Identity Pool binding (Step 4)
2. Check service account permissions (Step 5)
3. Ensure the repository name matches: `Verc-ai/verc-backend-service`

### Missing Secrets

If deployment fails due to missing secrets:
1. Verify all secrets exist: `gcloud secrets list --project=verc-prod`
2. Ensure secrets are named exactly as expected (case-sensitive)
3. Check that the Cloud Run service account has Secret Manager access

### Artifact Registry Issues

If image push fails:
1. Verify repository exists: `gcloud artifacts repositories list --location=us-east4 --project=verc-prod`
2. Check service account has `Artifact Registry Administrator` role
3. Verify Docker authentication: `gcloud auth configure-docker us-east4-docker.pkg.dev`

## Next Steps

After successful deployment:
1. Test the health endpoint: `curl https://<service-url>/health`
2. Update any external configurations that reference the backend URL
3. Set up monitoring and alerting
4. Configure custom domain (if needed)

---

**Note:** The Cloud Run service name must match `verc-app-prod` as defined in the workflow. The workflow will automatically create the service on first deployment if it doesn't exist.
