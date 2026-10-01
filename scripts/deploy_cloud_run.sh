#!/usr/bin/env bash
# Deploy AutoPlanner AI Gateway to Google Cloud Run
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-autoplanner-ai-gateway}"
REGION="${REGION:-us-central1}"
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"

echo "=== Deploying $SERVICE_NAME to Google Cloud Run ==="
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"

# Verify Secret Manager secret exists
if ! gcloud secrets describe GEMINI_API_KEY --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "WARNING: Secret 'GEMINI_API_KEY' does not exist in Secret Manager."
    echo "Create it with:"
    echo "  gcloud secrets create GEMINI_API_KEY --replication-policy=\"automatic\""
    echo "  echo -n \"YOUR_KEY\" | gcloud secrets versions add GEMINI_API_KEY --data-file=-"
fi

gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars ENVIRONMENT=production,AUTH_REQUIRED=true \
    --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest \
    --min-instances 0 \
    --max-instances 10 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 30s

echo "=== Deployment Complete ==="
gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)'
