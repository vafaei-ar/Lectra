from __future__ import annotations

from fastapi import FastAPI, HTTPException

from . import __version__
from .models import ParseRequest, ParsedNarration
from .parser import NarrationParseError, parse_narration
from .tts import backend_availability

app = FastAPI(
    title="Lectra Voice Service",
    version=__version__,
    description="Local parsing and voice-rendering service for Lectra presentations.",
)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "lectra-voice",
        "version": __version__,
        "supported_narration_schemas": ["1.0"],
        "tts_backends": backend_availability(),
    }


@app.post("/v1/parse", response_model=ParsedNarration)
def parse(request: ParseRequest) -> ParsedNarration:
    try:
        return parse_narration(request.markdown)
    except NarrationParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
