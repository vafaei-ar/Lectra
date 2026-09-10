from __future__ import annotations

import importlib.util

from .base import AudioChunk, BackendCapabilities, SynthesisRequest, TTSBackend


DEFAULT_BACKEND = "chatterbox"


def backend_availability() -> dict[str, bool]:
    return {
        "chatterbox": importlib.util.find_spec("chatterbox") is not None,
        "qwen3": importlib.util.find_spec("qwen_tts") is not None,
    }


def create_backend(name: str, **kwargs: object) -> TTSBackend:
    if name == "chatterbox":
        from .chatterbox import ChatterboxTTSBackend

        return ChatterboxTTSBackend(**kwargs)
    if name == "qwen3":
        from .qwen3 import Qwen3TTSBackend

        return Qwen3TTSBackend(**kwargs)
    raise ValueError(f"Unknown TTS backend: {name}")


__all__ = [
    "AudioChunk",
    "BackendCapabilities",
    "DEFAULT_BACKEND",
    "SynthesisRequest",
    "TTSBackend",
    "backend_availability",
    "create_backend",
]
