from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Callable

from .audio import render_segments
from .models import PauseSegment, SpeechSegment
from .parser import parse_narration
from .plain_text import speech_segments_from_text
from .profiles import VoiceStore
from .tts import DEFAULT_BACKEND, TTSBackend, create_backend

ProgressCallback = Callable[[int, int, str], None]


class RenderingCoordinator:
    """Serialize GPU rendering and keep local TTS backends warm between jobs."""

    def __init__(self, store: VoiceStore | None = None) -> None:
        self.store = store or VoiceStore()
        self._backends: dict[tuple[str, str], TTSBackend] = {}
        self._lock = Lock()

    def _backend(self, name: str, device: str) -> TTSBackend:
        key = (name, device)
        backend = self._backends.get(key)
        if backend is None:
            backend = create_backend(name, device=device)
            self._backends[key] = backend
        return backend

    def _render_prepared_for_user(
        self,
        *,
        user_id: int,
        segments: list[SpeechSegment | PauseSegment],
        title: str,
        language: str,
        output_path: Path,
        voice_id: str | None,
        backend_name: str,
        device: str,
        progress_callback: ProgressCallback | None,
    ) -> dict[str, object]:
        voice = self.store.get_voice(user_id, voice_id)
        speech_count = sum(isinstance(segment, SpeechSegment) for segment in segments)

        if progress_callback:
            progress_callback(0, speech_count, "waiting_for_gpu")
        with self._lock:
            if progress_callback:
                progress_callback(0, speech_count, "loading_model")
            backend = self._backend(backend_name, device)
            summary = render_segments(
                segments=segments,
                backend=backend,
                reference_audio=voice.reference_audio,
                reference_text=voice.reference_text,
                language=language,
                output_path=output_path,
                progress_callback=progress_callback,
            )

        summary["title"] = title
        summary["voice_id"] = voice.voice_id
        return summary

    def render_for_user(
        self,
        *,
        user_id: int,
        markdown: str,
        output_path: Path,
        voice_id: str | None = None,
        backend_name: str = DEFAULT_BACKEND,
        device: str = "auto",
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, object]:
        parsed = parse_narration(markdown)
        return self._render_prepared_for_user(
            user_id=user_id,
            segments=parsed.segments,
            title=str(parsed.metadata.get("title") or "presentation"),
            language=str(parsed.metadata.get("language", "en-US")),
            output_path=output_path,
            voice_id=voice_id,
            backend_name=backend_name,
            device=device,
            progress_callback=progress_callback,
        )

    def render_text_for_user(
        self,
        *,
        user_id: int,
        text: str,
        output_path: Path,
        voice_id: str | None = None,
        backend_name: str = DEFAULT_BACKEND,
        device: str = "auto",
        language: str = "en-US",
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, object]:
        segments = speech_segments_from_text(text)
        return self._render_prepared_for_user(
            user_id=user_id,
            segments=segments,
            title="Text message",
            language=language,
            output_path=output_path,
            voice_id=voice_id,
            backend_name=backend_name,
            device=device,
            progress_callback=progress_callback,
        )

    def close(self) -> None:
        for backend in self._backends.values():
            backend.close()
        self._backends.clear()
