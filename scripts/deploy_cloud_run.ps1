# Deploy AutoPlanner AI Gateway to Google Cloud Run (PowerShell)
param (
    [string]$ServiceName = "autoplanner-ai-gateway",
    [string]$Region = "us-central1",
    [string]$ProjectId = ""
)

$ErrorActionPreference = "Stop"

if (-not $ProjectId) {
    $ProjectId = (gcloud config get-value project 2>$null).Trim()
}

Write-Host "=== Deploying $ServiceName to Google Cloud Run ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectId"
Write-Host "Region:  $Region"

# Deploy service using gcloud source deploy
gcloud run deploy $ServiceName `
    --source . `
    --region $Region `
    --project $ProjectId `
    --platform managed `
    --allow-unauthenticated `
    --set-env-vars ENVIRONMENT=production,AUTH_REQUIRED=true `
    --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest `
    --min-instances 0 `
    --max-instances 10 `
    --memory 512Mi `
    --cpu 1 `
    --timeout 30s

Write-Host "=== Deployment Successful ===" -ForegroundColor Green
$ServiceUrl = gcloud run services describe $ServiceName --region $Region --format='value(status.url)'
Write-Host "Gateway URL: $ServiceUrl" -ForegroundColor Green
