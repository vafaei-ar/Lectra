from __future__ import annotations

import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock, Thread
from typing import Literal
from uuid import uuid4

from .models import SpeechSegment
from .parser import parse_narration
from .plain_text import speech_segments_from_text
from .rendering import RenderingCoordinator
from .tts import DEFAULT_BACKEND

JobState = Literal["queued", "running", "completed", "failed"]


class RenderJobError(RuntimeError):
    pass


class RenderJobNotFoundError(RenderJobError):
    pass


class RenderJobNotReadyError(RenderJobError):
    pass


@dataclass
class _RenderJob:
    job_id: str
    title: str
    output_format: str
    created_at: float
    state: JobState = "queued"
    stage: str = "queued"
    completed_segments: int = 0
    total_segments: int = 0
    error: str | None = None
    audio: bytes | None = None
    summary: dict[str, object] | None = None


class RenderJobManager:
    """Run local rendering jobs in worker threads and expose progress snapshots."""

    def __init__(self, renderer: RenderingCoordinator) -> None:
        self.renderer = renderer
        self._jobs: dict[str, _RenderJob] = {}
        self._lock = Lock()

    def _queue_job(
        self,
        *,
        user_id: int,
        title: str,
        total_segments: int,
        voice_id: str | None,
        backend_name: str,
        device: str,
        output_format: str,
        markdown: str | None = None,
        text: str | None = None,
    ) -> dict[str, object]:
        job = _RenderJob(
            job_id=uuid4().hex,
            title=title,
            output_format=output_format,
            created_at=time.time(),
            total_segments=total_segments,
        )
        with self._lock:
            self._jobs[job.job_id] = job

        worker = Thread(
            target=self._run,
            kwargs={
                "job_id": job.job_id,
                "user_id": user_id,
                "markdown": markdown,
                "text": text,
                "voice_id": voice_id,
                "backend_name": backend_name,
                "device": device,
                "output_format": output_format,
            },
            daemon=True,
            name=f"lectra-render-{job.job_id[:8]}",
        )
        worker.start()
        return self.snapshot(job.job_id)

    def submit(
        self,
        *,
        user_id: int,
        markdown: str,
        voice_id: str | None = None,
        backend_name: str = DEFAULT_BACKEND,
        device: str = "auto",
        output_format: str = "mp3",
    ) -> dict[str, object]:
        parsed = parse_narration(markdown)
        self.renderer.store.get_voice(user_id, voice_id)
        title = str(parsed.metadata.get("title") or "Presentation")
        total_segments = sum(isinstance(segment, SpeechSegment) for segment in parsed.segments)
        return self._queue_job(
            user_id=user_id,
            title=title,
            total_segments=total_segments,
            voice_id=voice_id,
            backend_name=backend_name,
            device=device,
            output_format=output_format,
            markdown=markdown,
        )

    def submit_text(
        self,
        *,
        user_id: int,
        text: str,
        voice_id: str | None = None,
        backend_name: str = DEFAULT_BACKEND,
        device: str = "auto",
        output_format: str = "mp3",
    ) -> dict[str, object]:
        segments = speech_segments_from_text(text)
        self.renderer.store.get_voice(user_id, voice_id)
        return self._queue_job(
            user_id=user_id,
            title="Text message",
            total_segments=len(segments),
            voice_id=voice_id,
            backend_name=backend_name,
            device=device,
            output_format=output_format,
            text=text,
        )

    def _run(
        self,
        *,
        job_id: str,
        user_id: int,
        markdown: str | None,
        text: str | None,
        voice_id: str | None,
        backend_name: str,
        device: str,
        output_format: str,
    ) -> None:
        def progress(completed: int, total: int, stage: str) -> None:
            with self._lock:
                job = self._jobs[job_id]
                job.completed_segments = completed
                job.total_segments = total
                job.stage = stage
                job.state = "queued" if stage == "waiting_for_gpu" else "running"

        suffix = ".mp3" if output_format == "mp3" else ".wav"
        try:
            with tempfile.TemporaryDirectory(prefix="lectra-job-") as temp_dir:
                output_path = Path(temp_dir) / f"presentation{suffix}"
                if text is not None:
                    summary = self.renderer.render_text_for_user(
                        user_id=user_id,
                        text=text,
                        output_path=output_path,
                        voice_id=voice_id,
                        backend_name=backend_name,
                        device=device,
                        progress_callback=progress,
                    )
                elif markdown is not None:
                    summary = self.renderer.render_for_user(
                        user_id=user_id,
                        markdown=markdown,
                        output_path=output_path,
                        voice_id=voice_id,
                        backend_name=backend_name,
                        device=device,
                        progress_callback=progress,
                    )
                else:
                    raise RenderJobError("Render job has no input.")
                payload = output_path.read_bytes()
            with self._lock:
                job = self._jobs[job_id]
                job.audio = payload
                job.summary = summary
                job.completed_segments = job.total_segments
                job.stage = "completed"
                job.state = "completed"
        except Exception as exc:
            with self._lock:
                job = self._jobs[job_id]
                job.error = f"{type(exc).__name__}: {exc}"
                job.stage = "failed"
                job.state = "failed"

    def snapshot(self, job_id: str) -> dict[str, object]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise RenderJobNotFoundError(f"Render job '{job_id}' was not found.")
            total = max(job.total_segments, 0)
            completed = max(min(job.completed_segments, total), 0) if total else 0
            percent = round((completed / total) * 100) if total else 0
            if job.stage in {"encoding", "completed"} and total:
                percent = 100
            summary = dict(job.summary) if job.summary else None
            return {
                "job_id": job.job_id,
                "title": job.title,
                "state": job.state,
                "stage": job.stage,
                "completed_segments": completed,
                "total_segments": total,
                "percent": percent,
                "elapsed_seconds": max(time.time() - job.created_at, 0.0),
                "error": job.error,
                "summary": summary,
            }

    def audio(self, job_id: str) -> tuple[bytes, dict[str, object], str]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise RenderJobNotFoundError(f"Render job '{job_id}' was not found.")
            if job.state == "failed":
                raise RenderJobError(job.error or "Render job failed.")
            if job.state != "completed" or job.audio is None:
                raise RenderJobNotReadyError("Render job is not complete yet.")
            return job.audio, dict(job.summary or {}), job.output_format
