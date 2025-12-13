# Frontend Deployment Guide

## ✅ Completed Setup

### 1. Frontend API Configuration
- ✅ `.env.production` → `VITE_API_URL=https://verc.ai`
- ✅ `.env.preview` → `VITE_API_URL=https://staging.verc.ai`

### 2. Backend CORS Configuration
- ✅ `env.example` updated with frontend domains
- ✅ Cloud Run Production CORS configured
- ✅ Cloud Run Staging CORS configured

**Allowed Origins:**
- `http://localhost:3000`
- `http://localhost:5173`
- `https://app.verc.ai`
- `https://www.verc.ai`
- `https://verc.ai`
- `https://app-staging.verc.ai` (staging)
- `https://staging.verc.ai` (staging)

## 🚀 Next Steps

### Step 1: Set Vercel Environment Variables

```bash
cd verc-frontend-service

# Set production API URL
vercel env add VITE_API_URL production
# When prompted, enter: https://verc.ai

# Set preview/staging API URL
vercel env add VITE_API_URL preview
# When prompted, enter: https://staging.verc.ai

# Verify other required variables are set
vercel env ls production
```

### Step 2: Add Custom Domain in Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your frontend project
3. Navigate to **Settings** → **Domains**
4. Click **Add Domain**
5. Enter: `app.verc.ai` (or `www.verc.ai`)
6. Vercel will provide DNS instructions

### Step 3: Add DNS Record

1. In Vercel Dashboard → **Domains** → `verc.ai`
2. Click **DNS Records**
3. Add the CNAME record provided by Vercel:
   - **Type:** CNAME
   - **Name:** `app` (for app.verc.ai)
   - **Value:** [Vercel's CNAME value]
   - **TTL:** 3600

### Step 4: Deploy Frontend

```bash
cd verc-frontend-service
./scripts/deploy-production.sh
```

Or use Vercel CLI directly:
```bash
vercel --prod
```

## 📋 Verification Checklist

After deployment:

- [ ] Frontend accessible at `https://app.verc.ai`
- [ ] API calls go to `https://verc.ai`
- [ ] No CORS errors in browser console
- [ ] Authentication flow works
- [ ] All API endpoints respond correctly

## 🔧 Useful Scripts

- `update-api-url.sh` - Update frontend API URLs
- `update-cors.sh` - Update backend CORS settings

## 📚 Current Configuration

| Component | Status | URL |
|-----------|--------|-----|
| Backend (Production) | ✅ Working | `https://verc.ai` |
| Backend (Staging) | ✅ Working | `https://staging.verc.ai` |
| Frontend API Config | ✅ Updated | Points to `https://verc.ai` |
| Backend CORS | ✅ Configured | Allows all frontend domains |
| Frontend Deployment | ⏳ Pending | Needs Vercel deployment |

## Troubleshooting

### CORS Errors
- Verify Cloud Run environment variable is set correctly
- Check browser console for specific CORS error
- Ensure frontend domain is in CORS_ALLOWED_ORIGINS

### API Connection Issues
- Verify `VITE_API_URL` in Vercel environment variables
- Test backend directly: `curl https://verc.ai/health`
- Check browser network tab for failed requests

### DNS Issues
- Wait 5-30 minutes for DNS propagation
- Check DNS: `dig app.verc.ai`
- Verify CNAME record in Vercel domain settings
