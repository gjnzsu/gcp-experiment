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

### Structured output experiment

The classification endpoint uses Gemini 2.5 with an explicit JSON schema. The schema controls the response shape; it is not a knowledge base. The backend validates the returned JSON with Pydantic before returning it to the caller.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/v1/classify `
  -ContentType "application/json" `
  -Body '{"text":"My card payment failed twice at a restaurant."}'
```
