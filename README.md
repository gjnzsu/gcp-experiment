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
set GOOGLE_CLOUD_PROJECT=your-project-id
set GOOGLE_CLOUD_LOCATION=global
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

The HTTP contract is kept separate from the Google model client so a future experiment can add a Model Garden endpoint adapter without changing clients.
