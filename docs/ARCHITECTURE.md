# AutoPlanner AI Gateway — Architecture & System Design

## 1. System Overview

The **AutoPlanner AI Gateway** is the authoritative server-side boundary for all artificial intelligence capabilities within the AutoPlanner ecosystem.

Prior to Phase 3.0, the mobile application (Flutter) communicated directly with Google Gemini via client-side SDKs. The AI Gateway decouples the client from language model vendors, establishing a secure, auditable cloud boundary.

```text
┌────────────────────────────────────────────────────────┐
│             AutoPlanner Flutter Application            │
│                                                        │
│  [UI Screens: Dashboard / Focus / Planner / Calendar]  │
│                           │                            │
│                           ▼                            │
│                      [AIService]                       │
│                           │                            │
│                           ▼ creates AIInvocation       │
│                   [CloudAIProvider]                    │
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS (Bearer Auth, X-Request-ID)
                            ▼
┌────────────────────────────────────────────────────────┐
│             AutoPlanner AI Gateway (FastAPI)           │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 1. Request Guard & Correlation Middleware        │  │
│  │    - X-Request-ID propagation                    │  │
│  │    - 413 Payload size limit enforcement          │  │
│  └────────────────────────┬─────────────────────────┘  │
│                           │                            │
│  ┌────────────────────────▼─────────────────────────┐  │
│  │ 2. Security & Rate Limiting Boundary             │  │
│  │    - IdentityProvider (Bearer token verification)│  │
│  │    - RateLimiter (Sliding-window RPM limiter)    │  │
│  └────────────────────────┬─────────────────────────┘  │
│                           │                            │
│  ┌────────────────────────▼─────────────────────────┐  │
│  │ 3. Operation Validation & Prompt Engineering     │  │
│  │    - Allowlist verification (Fail-closed)        │  │
│  │    - PromptRegistry (Server-owned templates)     │  │
│  │    - ModelRouter (Fast vs. Pro tier routing)     │  │
│  └────────────────────────┬─────────────────────────┘  │
│                           │                            │
│  ┌────────────────────────▼─────────────────────────┐  │
│  │ 4. Provider Layer & Output Normalization         │  │
│  │    - GeminiModelProvider (Async httpx client)    │  │
│  │    - Output JSON schema validation               │  │
│  │    - UsageService (Zero prompt/PII telemetry)    │  │
│  └────────────────────────┬─────────────────────────┘  │
└───────────────────────────┼────────────────────────────┘
                            │
                            ▼
           Google Gemini REST API (v1beta)
```

---

## 2. Core Architectural Principles

### "AI Interprets; Deterministic Logic Decides"
The gateway is strictly an interpretation, synthesis, and scoring engine.
- The gateway **never** writes directly to user databases, task lists, calendar events, or goals.
- All domain invariants (task non-overlap, immovable anchors, DAG dependency ordering, calendar conflict detection) remain enforced deterministically inside the client application.

### Server Prompt Ownership
The server maintains authoritative ownership of prompt templates.
- While the client may send legacy prompt strings for backward compatibility, the gateway builds prompts exclusively from semantic operations and structured input/context payloads.
- Changes to system prompts or schemas require zero mobile client app store updates.

---

## 3. Component Design

### 3.1 Authentication Boundary (`app/security/auth.py`)
Authentication is abstracted behind the `IdentityProvider` interface:
```python
class IdentityProvider(ABC):
    async def verify_token(self, token: str) -> AuthenticatedIdentity: ...
```
- In production, `AUTH_REQUIRED=true` guarantees that anonymous requests are rejected with `401 UNAUTHENTICATED`.
- Tokens are verified without being logged or echoed in exceptions.
- The interface enables seamless migration to Firebase Authentication or custom OAuth2/JWT issuers in future phases.

### 3.2 Abuse Protection & Rate Limiting (`app/services/rate_limit.py`)
- Request payload size is limited to `MAX_REQUEST_BYTES` (256 KB) via streaming middleware before body parsing, returning `413 REQUEST_TOO_LARGE`.
- Rate limiting is handled via `RateLimiter` interface with an `InMemoryRateLimiter` implementing a sliding-window algorithm.
- *Limitation Note*: In-memory rate limiting applies per instance. Distributed enforcement across multiple Cloud Run replicas will transition to Redis in subsequent phases.

### 3.3 Semantic Operations & Prompt Registry (`app/ai/prompts.py`)
All 13 operations map to dedicated, versioned templates in `PromptRegistry`:
```python
OperationPrompt(
    operation=AIOperation.PARSE_TASKS,
    version="parse_tasks:v1",
    system_instruction="...",
    builder=_build_parse_tasks,
    is_json=True,
)
```
Each builder dynamically injects structured data and user context into curated prompt layouts, enforcing precise JSON response structures where needed.

### 3.4 Model Routing (`app/ai/router.py`)
The `ModelRouter` inspects the requested operation and selects the appropriate model tier:
- `FAST_MODEL` (`gemini-2.5-flash`): Used for lightweight, latency-sensitive tasks like `parse_tasks`, `generate_tags`, `daily_insight`, and `suggest_reschedule`.
- `PRO_MODEL` (`gemini-2.5-pro`): Used for complex reasoning and multi-entity synthesis like `brain_dump`, `plan_day`, `weekly_review`, and `chat_coach`.
Clients have zero control over model selection.

### 3.5 Upstream Gemini Integration (`app/ai/providers/gemini.py`)
The gateway communicates with Google Gemini's REST API using `httpx.AsyncClient`:
- Bounded timeouts (`UPSTREAM_TIMEOUT_SECONDS=25.0`).
- Upstream transient errors (HTTP 429, 502, 503, timeouts) trigger bounded exponential backoff (max 2 retries).
- Client errors (HTTP 400, 401, 403) fail fast.
- Output text and token usage counts (`promptTokenCount`, `candidatesTokenCount`) are normalized into `ProviderResult`.

### 3.6 Output Normalization & JSON Validation (`app/ai/schemas.py`)
For operations expecting structured outputs:
1. Strips markdown fences (e.g. ````json ... ````) if emitted by the model.
2. Validates JSON syntactical and structural integrity.
3. If the model produces malformed or missing fields, the gateway raises `502 AI_PROVIDER_ERROR` instead of returning corrupted data to the client.

### 3.7 Usage Telemetry & Privacy (`app/services/usage.py`)
`UsageService` records structured operational metrics:
- `requestId`, `operation`, `model`, `promptVersion`, `promptTokens`, `completionTokens`, `totalTokens`, `latencyMs`, `timestamp`, `success`.
- **Privacy Guarantee**: Prompts, user text, personal context, and model output strings are **never logged or persisted**.

---

## 4. Google Cloud Run Deployment & IAM Architecture

### Architecture Diagram
```text
┌────────────────────────────────────────────────────────┐
│                   Google Cloud Platform                │
│                                                        │
│  ┌───────────────────────┐   Injects Secret            │
│  │ Google Secret Manager │──────────────────────────┐  │
│  │ (GEMINI_API_KEY)      │                          │  │
│  └───────────────────────┘                          │  │
│                                                     ▼  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Google Cloud Run (autoplanner-ai-gateway)        │  │
│  │ - Service Account: gateway-sa@PROJECT.iam        │  │
│  │ - Container: python:3.12-slim (Non-root user)    │  │
│  │ - Environment: Production                        │  │
│  └──────────────────────────┬───────────────────────┘  │
│                             │ HTTPS (x-goog-api-key)   │
│                             ▼                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Google Gemini API                                │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### Deployment Instructions

#### 1. Service Account & Secret Manager Access
```bash
# Create service account for Cloud Run
gcloud iam service-accounts create autoplanner-gateway-sa \
  --display-name="AutoPlanner AI Gateway Service Account" \
  --project="PROJECT_ID"

# Grant Secret Manager Secret Accessor role to the service account
gcloud secrets add-iam-policy-binding autoplanner-gemini-key \
  --member="serviceAccount:autoplanner-gateway-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project="PROJECT_ID"
```

#### 2. Cloud Run Service Deployment
```bash
gcloud run deploy autoplanner-ai-gateway \
  --image="gcr.io/PROJECT_ID/autoplanner-ai-gateway:latest" \
  --region="us-central1" \
  --platform="managed" \
  --service-account="autoplanner-gateway-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production,AUTH_REQUIRED=true,FAST_MODEL=gemini-2.5-flash,PRO_MODEL=gemini-2.5-pro,RATE_LIMIT_RPM=60" \
  --set-secrets="GEMINI_API_KEY=autoplanner-gemini-key:latest" \
  --project="PROJECT_ID"
```
