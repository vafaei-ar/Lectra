from __future__ import annotations

import importlib.util

from .base import AudioChunk, BackendCapabilities, SynthesisRequest, TTSBackend


def backend_availability() -> dict[str, bool]:
    return {
        "qwen3": importlib.util.find_spec("qwen_tts") is not None,
        "chatterbox": importlib.util.find_spec("chatterbox") is not None,
    }


def create_backend(name: str, **kwargs: object) -> TTSBackend:
    if name == "qwen3":
        from .qwen3 import Qwen3TTSBackend

        return Qwen3TTSBackend(**kwargs)
    if name == "chatterbox":
        from .chatterbox import ChatterboxTTSBackend

        return ChatterboxTTSBackend(**kwargs)
    raise ValueError(f"Unknown TTS backend: {name}")


__all__ = [
    "AudioChunk",
    "BackendCapabilities",
    "SynthesisRequest",
    "TTSBackend",
    "backend_availability",
    "create_backend",
]
