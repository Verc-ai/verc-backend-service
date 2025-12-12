# Production Deployment Checklist

## Pre-Deployment Verification

- [ ] All secrets created in Secret Manager (`verc-prod`)
- [ ] Artifact Registry repository exists (`verc-app-prod`)
- [ ] Workload Identity Pool binding configured
- [ ] Service account has required permissions
- [ ] Cloud Tasks queue created (if using Cloud Tasks)

## Deployment Steps

### 1. Verify Secrets
```bash
gcloud secrets list --project=verc-prod
```

Required secrets:
- [ ] `supabase-url`
- [ ] `supabase-anon-key`
- [ ] `supabase-service-role-key`
- [ ] `openai-api-key`
- [ ] `anthropic-api-key`
- [ ] `assemblyai-api-key`
- [ ] `twilio-account-sid`
- [ ] `twilio-auth-token`
- [ ] `twilio-phone-number`
- [ ] `TWILIO_WEBHOOK_BASE_URL`

### 2. Deploy via GitHub Actions

1. Go to: https://github.com/Verc-ai/verc-backend-service/actions
2. Click on **"Deploy"** workflow
3. Click **"Run workflow"** button (top right)
4. Select **"production"** from the environment dropdown
5. Click **"Run workflow"**

### 3. Monitor Deployment

Watch the workflow execution:
- Build and push Docker image
- Deploy to Cloud Run
- Health check

Expected duration: ~5-10 minutes

### 4. Verify Deployment

After successful deployment:

1. **Get the service URL** from the workflow output
2. **Test health endpoint:**
   ```bash
   curl https://<service-url>/health
   ```
   Should return: `{"status": "healthy"}`

3. **Check Cloud Run service:**
   ```bash
   gcloud run services describe verc-app-prod \
     --region=us-east4 \
     --project=verc-prod
   ```

## Post-Deployment

- [ ] Update frontend configuration with production backend URL
- [ ] Test API endpoints
- [ ] Set up monitoring/alerts
- [ ] Configure custom domain (if needed)
- [ ] Update documentation with production URL

## Troubleshooting

### Deployment Fails

1. **Check workflow logs** in GitHub Actions
2. **Verify service account permissions:**
   ```bash
   gcloud projects get-iam-policy verc-prod \
     --flatten="bindings[].members" \
     --filter="bindings.members:serviceAccount:github-ci@verc-prod.iam.gserviceaccount.com"
   ```

3. **Check Artifact Registry:**
   ```bash
   gcloud artifacts repositories describe verc-app-prod \
     --location=us-east4 \
     --project=verc-prod
   ```

4. **Verify secrets exist:**
   ```bash
   gcloud secrets list --project=verc-prod
   ```

### Health Check Fails

1. Check Cloud Run logs:
   ```bash
   gcloud run services logs read verc-app-prod \
     --region=us-east4 \
     --project=verc-prod
   ```

2. Verify environment variables are set correctly
3. Check that secrets are accessible

## Quick Commands Reference

```bash
# Get service URL
gcloud run services describe verc-app-prod \
  --region=us-east4 \
  --project=verc-prod \
  --format='value(status.url)'

# View logs
gcloud run services logs read verc-app-prod \
  --region=us-east4 \
  --project=verc-prod \
  --limit=50

# List all secrets
gcloud secrets list --project=verc-prod

# Check service status
gcloud run services describe verc-app-prod \
  --region=us-east4 \
  --project=verc-prod
```
