from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from . import __version__
from .jobs import (
    RenderJobError,
    RenderJobManager,
    RenderJobNotFoundError,
    RenderJobNotReadyError,
)
from .models import ParseRequest, ParsedNarration
from .parser import NarrationParseError, parse_narration
from .profiles import VoiceProfileError, VoiceStore
from .rendering import RenderingCoordinator
from .tts import DEFAULT_BACKEND, backend_availability


class RenderRequest(BaseModel):
    telegram_user_id: int = Field(gt=0)
    markdown: str = Field(min_length=1)
    voice_id: str | None = None
    backend: Literal["chatterbox", "qwen3"] = DEFAULT_BACKEND
    device: str = "auto"
    output_format: Literal["mp3", "wav"] = "mp3"


_store = VoiceStore()
_renderer = RenderingCoordinator(_store)
_jobs = RenderJobManager(_renderer)

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
        "default_tts_backend": DEFAULT_BACKEND,
        "tts_backends": backend_availability(),
        # Keep both names during v0.3 so older/newer bot builds agree on the
        # progress capability while the API contract settles.
        "render_job_progress": True,
        "progress_reporting": True,
    }


@app.post("/v1/parse", response_model=ParsedNarration)
def parse(request: ParseRequest) -> ParsedNarration:
    try:
        return parse_narration(request.markdown)
    except NarrationParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return cleaned[:80] or "presentation"


def _audio_response(payload: bytes, summary: dict[str, object], output_format: str) -> Response:
    suffix = ".mp3" if output_format == "mp3" else ".wav"
    title = _safe_filename(str(summary.get("title", "presentation")))
    media_type = "audio/mpeg" if suffix == ".mp3" else "audio/wav"
    headers = {
        "Content-Disposition": f'attachment; filename="{title}{suffix}"',
        "X-Lectra-Backend": str(summary.get("backend", DEFAULT_BACKEND)),
        "X-Lectra-Voice": str(summary.get("voice_id", "default")),
        "X-Lectra-Duration": str(summary.get("duration_seconds", "")),
    }
    return Response(content=payload, media_type=media_type, headers=headers)


@app.post("/v1/render")
def render(request: RenderRequest) -> Response:
    suffix = ".mp3" if request.output_format == "mp3" else ".wav"
    try:
        with tempfile.TemporaryDirectory(prefix="lectra-api-") as temp_dir:
            output_path = Path(temp_dir) / f"presentation{suffix}"
            summary = _renderer.render_for_user(
                user_id=request.telegram_user_id,
                markdown=request.markdown,
                output_path=output_path,
                voice_id=request.voice_id,
                backend_name=request.backend,
                device=request.device,
            )
            payload = output_path.read_bytes()
    except NarrationParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except VoiceProfileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _audio_response(payload, summary, request.output_format)


# /v1/render/jobs is the canonical route. /v1/jobs is retained as a v0.3
# compatibility alias because an early Telegram build used the shorter path.
@app.post("/v1/jobs", status_code=202, include_in_schema=False)
@app.post("/v1/render/jobs", status_code=202)
def create_render_job(request: RenderRequest) -> dict[str, object]:
    try:
        return _jobs.submit(
            user_id=request.telegram_user_id,
            markdown=request.markdown,
            voice_id=request.voice_id,
            backend_name=request.backend,
            device=request.device,
            output_format=request.output_format,
        )
    except NarrationParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except VoiceProfileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/v1/jobs/{job_id}", include_in_schema=False)
@app.get("/v1/render/jobs/{job_id}")
def render_job_status(job_id: str) -> dict[str, object]:
    try:
        return _jobs.snapshot(job_id)
    except RenderJobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/jobs/{job_id}/audio", include_in_schema=False)
@app.get("/v1/render/jobs/{job_id}/audio")
def render_job_audio(job_id: str) -> Response:
    try:
        payload, summary, output_format = _jobs.audio(job_id)
    except RenderJobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RenderJobNotReadyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RenderJobError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _audio_response(payload, summary, output_format)
