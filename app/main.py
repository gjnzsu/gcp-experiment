from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai.types import HttpOptions
import os

app = FastAPI(title="GCP Experiment API", version="0.1.0")

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "gemini-2.5-flash")

client = genai.Client(
    vertexai=True,
    project=PROJECT,
    location=LOCATION,
    http_options=HttpOptions(api_version="v1"),
)


class GenerateRequest(BaseModel):
    prompt: str
    model: str | None = None


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/v1/generate")
def generate(request: GenerateRequest):
    model = request.model or DEFAULT_MODEL
    try:
        response = client.models.generate_content(
            model=model,
            contents=request.prompt,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Model request failed") from exc

    return {"text": response.text, "model": model}
