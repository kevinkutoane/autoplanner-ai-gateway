# AutoPlanner AI Gateway — Phase 3.0 MVP

The **AutoPlanner AI Gateway** is a FastAPI service that forms the authoritative server-side AI boundary for the [AutoPlanner AI](https://github.com/kevinkutoane/autoplanner_ai) mobile application.

The gateway decouples the Flutter mobile application from specific upstream language models, serving as the central control point for prompt template ownership, model selection, rate limiting, abuse guardrails, and usage telemetry.

---

## 🏛️ Architecture

```text
┌────────────────────────────────────────────────────────┐
│             AutoPlanner Mobile Client (Flutter)        │
│                                                        │
│   UI Features → AIService → AIInvocation               │
│                    │                                   │
│                    ▼                                   │
│             CloudAIProvider                            │
└────────────────────┬───────────────────────────────────┘
                     │
                     │ HTTPS (Bearer Auth, X-Request-ID, X-Client-Version)
                     ▼
┌────────────────────────────────────────────────────────┐
│             AutoPlanner AI Gateway (Cloud Run)         │
│                                                        │
│  1. Request Correlation & Size Guard (413)             │
│  2. Authentication (Bearer IdentityProvider)           │
│  3. Rate Limiter (InMemory sliding window)             │
│  4. Operation Allowlist & Validation (Fail-Closed)     │
│  5. Prompt Registry (Server-owned versioned templates) │
│  6. Model Router (Fast vs. Pro Gemini tiers)           │
│  7. AI Provider (Async httpx Gemini API)               │
│  8. Output Normalization & JSON Schema Validation      │
│  9. Usage Telemetry (Structured, zero prompt/PII)      │
│  10. Normalized Error Envelope                         │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
           Google Gemini 2.5 Flash / Pro
```

### Core Architectural Principle
> **"AI decides what something means. Deterministic application logic decides what is valid and executable."**
The gateway orchestrates language models and interprets unstructured inputs. It **never** mutates domain state directly. The Flutter client's deterministic domain logic remains solely authoritative for tasks, calendars, schedules, and local persistence.

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.12+ (or 3.14+)
- Google Gemini API Key

### 2. Environment Setup
```bash
cd autoplanner-ai-gateway

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Copy the template and set your configuration:
```bash
cp .env.example .env
```
Edit `.env`:
```ini
ENVIRONMENT=development
PORT=8080
AUTH_REQUIRED=true
DEV_BEARER_TOKEN=dev-secret-token
GEMINI_API_KEY=your-real-gemini-api-key
FAST_MODEL=gemini-2.5-flash
PRO_MODEL=gemini-2.5-pro
RATE_LIMIT_RPM=60
```

### 4. Run Locally
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## 📡 API Contract

### 1. Health Check
```http
GET /health
```

**Response (`200 OK`)**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-09-22T00:00:00Z"
}
```

---

### 2. Execute AI Invocation
```http
POST /v1/ai/complete
Content-Type: application/json
Authorization: Bearer dev-secret-token
X-Request-ID: 7b5a1f28-a28d-4e92-bc10-18e3c1d9b3a4
X-Client-Version: 2.3.1+1
```

**Request Body**:
```json
{
  "id": "7b5a1f28-a28d-4e92-bc10-18e3c1d9b3a4",
  "operation": "parse_tasks",
  "input": {
    "text": "Call accountant tomorrow at 10am and review tax draft"
  },
  "context": {
    "memories": ["User works best in mornings"]
  },
  "client": {
    "appVersion": "2.3.1+1"
  },
  "timestamp": "2026-09-22T00:00:00Z"
}
```

**Response (`200 OK`)**:
```json
{
  "text": "[{\"title\": \"Call accountant\", \"startTime\": \"10:00\", \"estimatedMinutes\": 30, \"priority\": 2, \"tags\": [\"finance\"]}, {\"title\": \"Review tax draft\", \"startTime\": null, \"estimatedMinutes\": 45, \"priority\": 2, \"tags\": [\"finance\"]}]",
  "promptTokens": 142,
  "completionTokens": 58,
  "model": "gemini-2.5-flash"
}
```

---

### 3. Error Responses
All errors adhere to a standardized, machine-readable JSON structure:
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "AI rate limit exceeded. Retry after 30 seconds.",
    "requestId": "7b5a1f28-a28d-4e92-bc10-18e3c1d9b3a4"
  }
}
```

Supported error codes:
* `400 INVALID_REQUEST`: Malformed JSON, missing fields, or failed input constraints.
* `401 UNAUTHENTICATED`: Missing, malformed, or invalid Bearer token.
* `403 FORBIDDEN`: Insufficient entitlements.
* `404 UNKNOWN_OPERATION`: Unregistered or invalid operation string.
* `413 REQUEST_TOO_LARGE`: Payload exceeds `MAX_REQUEST_BYTES` (256 KB).
* `429 RATE_LIMITED`: Exceeded `RATE_LIMIT_RPM`.
* `502 AI_PROVIDER_ERROR`: Upstream model failure or malformed model output.
* `503 AI_SERVICE_UNAVAILABLE`: Upstream network timeout or transient gateway outage.
* `500 INTERNAL_ERROR`: Unexpected internal server exception (stack traces stripped).

---

## 📋 Semantic AI Operations Registry

The gateway owns the authoritative prompt templates and models for all 13 AutoPlanner semantic operations:

| Operation Wire Name | Version | Model Tier | Output Type | Expected Inputs |
| :--- | :---: | :---: | :---: | :--- |
| `brain_dump` | `brain_dump:v1` | `PRO_MODEL` | Structured JSON | `text` / `rawInput`, optional `suggestedStartTime` |
| `parse_tasks` | `parse_tasks:v1` | `FAST_MODEL` | Structured JSON | `text`, optional `memories` |
| `plan_day` | `plan_day:v1` | `PRO_MODEL` | Structured JSON | `additionalInput`, `existingTasks`, `workStartHour`, `workHoursPerDay` |
| `chat_coach` | `chat_coach:v1` | `PRO_MODEL` | Plain text | `message`, `history` |
| `daily_insight` | `daily_insight:v1` | `FAST_MODEL` | Plain text | `tasks`, `goals`, `memories` |
| `suggest_reschedule` | `suggest_reschedule:v1` | `FAST_MODEL` | Slot Index | `taskTitle`, `durationMinutes`, `candidateSlots` |
| `summarize_note` | `summarize_note:v1` | `FAST_MODEL` | Plain text | `content` |
| `generate_tags` | `generate_tags:v1` | `FAST_MODEL` | JSON Array | `content` |
| `extract_memory` | `extract_memory:v1` | `FAST_MODEL` | Plain text | `context`, `sourceType` |
| `extract_patterns` | `extract_patterns:v1` | `FAST_MODEL` | Structured JSON | `completedHistory` |
| `suggest_tasks` | `suggest_tasks:v1` | `FAST_MODEL` | JSON Array | `dayName`, `memories` |
| `weekly_review` | `weekly_review:v1` | `PRO_MODEL` | Markdown | `tasksCount`, `completedCount`, `completionRate`, `goals` |
| `parse_schedule_command` | `parse_schedule_command:v1` | `FAST_MODEL` | Structured JSON | `query`, `referenceTime` |

---

## 🔒 Security & Privacy Boundaries

1. **Zero Secret Leakage**:
   - `GEMINI_API_KEY` is loaded strictly on the server and is never passed to client applications.
   - Bearer tokens are never written to logs or included in error traces.
2. **Zero Content Persistence / Logging**:
   - `UsageService` logs and stores operational telemetry (`requestId`, `operation`, `model`, token counts, `latencyMs`).
   - Raw user input, prompts, context payloads, and generated text are **never logged or persisted**.
3. **No Arbitrary Prompt Endpoints**:
   - There are no `/raw-prompt` endpoints. Only allowlisted semantic operations are executed.
4. **Rate Limiting Boundary**:
   - An in-memory sliding window limiter protects the service during MVP.
   - *Note*: In-memory rate limiting is suitable for local/staging validation, but is not distributed production enforcement when multiple Cloud Run instances or auto-scaling replicas are active.

---

## 🧪 Testing

Run the automated pytest test suite:
```bash
pytest -v
```

Coverage spans:
- Health checks and secret sanitization
- Bearer authentication and development bypass
- Request validation, size guards, and unknown operation rejection
- Operation registry and prompt versioning
- Prompt ownership independence (server ignores client prompts)
- Model routing determinism
- Mock Gemini provider execution and error translation (429, 503, timeouts)
- Structured JSON output validation and code-fence stripping
- In-memory rate limiting thresholds
- Operational telemetry recording without sensitive content logging

---

## ☁️ Google Cloud Run Deployment Guide

### 1. Build and Test Container Locally
```bash
docker build -t autoplanner-ai-gateway:latest .
docker run -p 8080:8080 -e GEMINI_API_KEY=test-key autoplanner-ai-gateway:latest
```

### 2. Store Gemini Secret in Google Cloud Secret Manager
```bash
gcloud secrets create autoplanner-gemini-key \
  --replication-policy="automatic" \
  --project="PROJECT_ID"

echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets versions add autoplanner-gemini-key \
  --data-file=- \
  --project="PROJECT_ID"
```

### 3. Deploy to Cloud Run with Injected Secret
```bash
gcloud run deploy autoplanner-ai-gateway \
  --image="gcr.io/PROJECT_ID/autoplanner-ai-gateway:latest" \
  --region="us-central1" \
  --platform="managed" \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production,AUTH_REQUIRED=true,FAST_MODEL=gemini-2.5-flash,PRO_MODEL=gemini-2.5-pro,RATE_LIMIT_RPM=60" \
  --set-secrets="GEMINI_API_KEY=autoplanner-gemini-key:latest" \
  --project="PROJECT_ID"
```
