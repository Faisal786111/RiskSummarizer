"""FastAPI application: POST /summarize returns a structured risk summary."""
import logging

from fastapi import FastAPI, HTTPException

from app.fetcher import FetchError, fetch_text
from app.llm import LLMError, analyse
from app.schemas import SummarizeRequest, SummarizeResponse

logging.basicConfig(level=logging.INFO)

MIN_CHARS = 50

app = FastAPI(
    title="Risk Summarizer API",
    description="Summarises text or web pages with Gemini and returns a structured risk assessment.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


# Plain `def` so FastAPI runs these blocking network calls in a worker thread.
@app.post("/summarize", response_model=SummarizeResponse)
def summarize(request: SummarizeRequest):
    if request.url and request.url.strip():
        source = "url"
        try:
            text = fetch_text(request.url)
        except FetchError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    else:
        source = "text"
        text = (request.text or "").strip()

    if len(text) < MIN_CHARS:
        raise HTTPException(
            status_code=422,
            detail=f"Not enough text to analyse (need at least {MIN_CHARS} characters).",
        )

    try:
        result = analyse(text)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return SummarizeResponse(source=source, characters_analysed=len(text), result=result)
