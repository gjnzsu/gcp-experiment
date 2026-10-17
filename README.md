# GCP Experiment

Small backend service for experimenting with Google Cloud Vertex AI and Model Garden.

## Local setup

```bash
python -m venv .venv
.venv\\Scripts\\activate  # Windows
pip install -r requirements.txt
gcloud auth application-default login
```

Set environment variables:

```bash
set GOOGLE_CLOUD_PROJECT=gen-lang-client-0896070179
set GOOGLE_CLOUD_LOCATION=global
set GOOGLE_GENAI_USE_VERTEXAI=True
set LLM_MODEL=gemini-2.5-flash
```

Run the service:

```bash
uvicorn app.main:app --reload
```

Call it:

```bash
curl -X POST http://localhost:8000/v1/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\":\"Explain event-driven architecture in three sentences.\"}"
```

## API

- `GET /healthz`
- `POST /v1/generate`
- `POST /v1/generate/stream` — Gemini streaming response using SSE
- `POST /v1/classify` — Gemini 2.5 structured JSON output

The HTTP contract is kept separate from the Google model client so a future experiment can add a Model Garden endpoint adapter without changing clients.

## Model Garden MaaS experiment

After enabling the model's **API Service** in Model Garden, switch the model without changing the HTTP API:

```powershell
$env:LLM_MODEL="publishers/deepseek-ai/models/deepseek-v4.1-flash-maas"
```

MaaS model IDs ending in `-maas` use the Google Gen AI SDK chat interface. Google-hosted Gemini models continue to use `generate_content`.

## Vertex AI endpoint patterns

The models use the same Google Cloud platform and authentication, but the underlying endpoint contract depends on how the model is served:

| Model or operation | Typical path |
| --- | --- |
| Google Gemini publisher model | `/publishers/google/models/{MODEL_ID}:generateContent` |
| Model Garden managed model | May use a managed publisher or MaaS model service path |
| Self-deployed Vertex endpoint model | `/endpoints/{ENDPOINT_ID}:predict` |
| Embedding | `/publishers/google/models/{MODEL_ID}:predict` or the model's embedding API |
| Streaming | The same model resource with `:streamGenerateContent` where supported |
| Batch | A Vertex AI batch job resource path |

For this project:

```text
Gemini 2.5 Flash
  Google Gen AI SDK → models.generate_content()
  Vertex publisher model → generateContent

DeepSeek V4.1 Flash MaaS
  Google Gen AI SDK → chats.create().send_message()
  Managed open-model service → chat-compatible contract
```

The public backend contract remains `POST /v1/generate`; provider-specific endpoint paths and request formats stay inside the backend adapter.

## Milestone 1: Vertex AI backend foundations

This milestone establishes the first working backend patterns for the experiment.

### Validated flows

```text
PowerShell client
  → FastAPI backend
    → Google Gen AI SDK
      → Vertex AI / Agent Platform
        → Gemini publisher model or Model Garden MaaS model
```

- Gemini 2.5 Flash through the Google publisher model API.
- DeepSeek V4.1 Flash through Model Garden MaaS using the same Google Gen AI SDK.
- Local authentication through Application Default Credentials (ADC).
- Project IAM using `roles/aiplatform.user`; no service account is needed for local development.
- A stable backend contract independent of the provider-specific model API.
- Structured JSON output with an explicit schema and Pydantic validation.
- Gemini streaming output through Server-Sent Events (SSE).

### Current endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /healthz` | Service health check |
| `POST /v1/generate` | Normal text generation |
| `POST /v1/classify` | Gemini 2.5 structured classification |
| `POST /v1/generate/stream` | Gemini streaming response over SSE |

### Key design conclusions

- FastAPI is the backend server exposed to the PowerShell or frontend client.
- The Google Gen AI SDK is a client library inside the FastAPI process.
- Vertex AI / Agent Platform is the upstream managed model service.
- Gemini publisher models and MaaS models share the platform and authentication, but their underlying endpoint contracts can differ.
- `generateContent`, chat, streaming, and batch describe different API interfaces or execution modes; they are not interchangeable model types.
- Schema controls output shape. A knowledge base supplies factual or business context. Backend validation checks whether the model response is acceptable.
- Streaming keeps the client connection open while chunks are forwarded. Batch submits asynchronous work and reads results later.

### Checkpoint

Milestone 1 is complete. The repository is ready to be parked until a new use case is selected. Future experiments can build on this baseline by adding function calling, RAG, evaluation, audit logging, model comparison, or deployment to Cloud Run.

### Chat, streaming, and batch

- **Chat** describes the message or conversation interface. It can be single-turn or multi-turn.
- **Streaming** returns one request's output incrementally as it is generated. This POC uses Server-Sent Events (SSE).
- **Batch** submits many requests for asynchronous processing and reads the results later. It is useful for offline workloads, not interactive API responses.

Try the streaming endpoint with Gemini:

```powershell
$env:LLM_MODEL="gemini-2.5-flash"

curl.exe -N -X POST http://localhost:8000/v1/generate/stream `
  -H "Content-Type: application/json" `
  -d '{"prompt":"Explain event-driven architecture in five paragraphs."}'
```

### Structured output experiment

The classification endpoint uses Gemini 2.5 with an explicit JSON schema. The schema controls the response shape; it is not a knowledge base. The backend validates the returned JSON with Pydantic before returning it to the caller.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/v1/classify `
  -ContentType "application/json" `
  -Body '{"text":"My card payment failed twice at a restaurant."}'
```
