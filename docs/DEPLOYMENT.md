# AutoPlanner AI Gateway — Deployment Guide

This guide documents deploying the AutoPlanner AI Gateway to **Google Cloud Run** using containerized deployment and Secret Manager for upstream Gemini API credentials.

---

## Architecture Overview

```text
┌─────────────────────────────────┐
│     AutoPlanner Mobile / Web    │
└────────────────┬────────────────┘
                 │ HTTPS (Bearer Token, X-Request-ID)
                 ▼
┌─────────────────────────────────┐
│   Google Cloud Run (Managed)    │
│   - Service: autoplanner-ai-gw  │
│   - Port: 8080 (injected $PORT) │
│   - Concurrency: 80 req/instance│
└────────────────┬────────────────┘
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
┌──────────────┐    ┌──────────────┐
│Secret Manager│    │Google Gemini │
│GEMINI_API_KEY│    │REST API v1beta│
└──────────────┘    └──────────────┘
```

---

## 1. Prerequisites

1. **Google Cloud Project**:
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```
2. **Enable Required APIs**:
   ```bash
   gcloud services enable \
     run.googleapis.com \
     artifactregistry.googleapis.com \
     cloudbuild.googleapis.com \
     secretmanager.googleapis.com
   ```

---

## 2. Secrets Configuration (Secret Manager)

Store the upstream Gemini API key securely in Google Secret Manager:

```bash
# Create secret
gcloud secrets create GEMINI_API_KEY --replication-policy="automatic"

# Add secret payload
echo -n "AIzaSy..." | gcloud secrets versions add GEMINI_API_KEY --data-file=-

# Grant Cloud Run service account access to read secrets
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 3. Deploying to Cloud Run

### Option A: Using the Deploy Script

**Linux / macOS:**
```bash
./scripts/deploy_cloud_run.sh
```

**Windows PowerShell:**
```powershell
.\scripts\deploy_cloud_run.ps1
```

### Option B: Manual gcloud CLI

```bash
gcloud run deploy autoplanner-ai-gateway \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production,AUTH_REQUIRED=true \
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest \
  --min-instances 0 \
  --max-instances 10 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 30s
```

---

## 4. Continuous Deployment via GitHub Actions

The repository includes [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) for automated deployments:

1. **Tag Trigger**: Push a git tag (e.g. `git tag v1.0.0 && git push origin v1.0.0`) to trigger automated production deployment.
2. **Manual Trigger**: Go to **Actions** > **Deploy to Cloud Run** > **Run workflow** and choose `staging` or `production`.
3. **Required GitHub Secrets**:
   - `GCP_WORKLOAD_IDENTITY_PROVIDER`: Workload Identity Provider resource name.
   - `GCP_SERVICE_ACCOUNT`: Dedicated deployment service account email with Cloud Run Admin & Artifact Registry Writer permissions.

---

## 5. Verification & Health Monitoring

Once deployed, retrieve the service URL:
```bash
GATEWAY_URL=$(gcloud run services describe autoplanner-ai-gateway --region us-central1 --format='value(status.url)')
echo "Gateway URL: $GATEWAY_URL"
```

Check the health endpoint:
```bash
curl -f "$GATEWAY_URL/health"
# Expected response:
# {"status":"healthy","version":"1.0.0","timestamp":"..."}
```

Point the AutoPlanner Flutter client to your live deployment:
```bash
flutter run --dart-define=AI_GATEWAY_URL=$GATEWAY_URL
```
