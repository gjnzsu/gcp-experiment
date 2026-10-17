import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
import os

app = FastAPI(title="GCP Experiment API", version="0.1.0")

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "gemini-2.5-flash")

client = None


def get_client():
    global client
    if client is None and PROJECT:
        client = genai.Client(
            vertexai=True,
            project=PROJECT,
            location=LOCATION,
            http_options=HttpOptions(api_version="v1"),
        )
    return client


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None


class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1)


class Classification(BaseModel):
    category: str
    priority: str
    summary: str
    requires_human_review: bool


CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": [
                "payment_issue",
                "account_access",
                "fraud_alert",
                "general_question",
            ],
        },
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "summary": {"type": "string"},
        "requires_human_review": {"type": "boolean"},
    },
    "required": [
        "category",
        "priority",
        "summary",
        "requires_human_review",
    ],
}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/v1/generate")
def generate(request: GenerateRequest):
    model_client = get_client()
    if model_client is None:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_CLOUD_PROJECT is not configured",
        )

    model = request.model or DEFAULT_MODEL
    try:
        if model.endswith("-maas"):
            chat = model_client.chats.create(model=model)
            response = chat.send_message(request.prompt)
        else:
            response = model_client.models.generate_content(
                model=model,
                contents=request.prompt,
            )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Model request failed") from exc

    return {"text": response.text, "model": model}


@app.post("/v1/generate/stream")
def generate_stream(request: GenerateRequest):
    model_client = get_client()
    if model_client is None:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_CLOUD_PROJECT is not configured",
        )

    model = request.model or DEFAULT_MODEL
    if model.endswith("-maas"):
        raise HTTPException(
            status_code=400,
            detail="The streaming POC currently supports Gemini models only",
        )

    def chunks():
        try:
            for chunk in model_client.models.generate_content_stream(
                model=model,
                contents=request.prompt,
            ):
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"

    return StreamingResponse(
        chunks(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/v1/classify", response_model=Classification)
def classify(request: ClassifyRequest):
    model_client = get_client()
    if model_client is None:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_CLOUD_PROJECT is not configured",
        )

    prompt = f"""Classify this customer service case.

Rules:
- payment_issue: failed, declined, or duplicated payment
- fraud_alert: suspected unauthorized activity
- account_access: login or account lock problems
- general_question: anything else
- Use high priority when money may be lost or fraud is suspected.
- Set requires_human_review=true for fraud_alert or high priority.

Customer case:
{request.text}
"""

    try:
        response = model_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CLASSIFICATION_SCHEMA,
            ),
        )
        return Classification.model_validate(json.loads(response.text))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Model returned an invalid classification",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Model request failed") from exc
