from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class BackendCapabilities:
    voice_cloning: bool = True
    pace_control: bool = False
    tone_control: bool = False
    multilingual: bool = False
    requires_reference_text: bool = False


@dataclass(frozen=True)
class SynthesisRequest:
    text: str
    reference_audio: Path
    reference_text: str | None = None
    language: str = "en-US"
    pace: str = "normal"
    tone: str = "explanatory"


@dataclass
class AudioChunk:
    samples: np.ndarray
    sample_rate: int
    metadata: dict[str, object] = field(default_factory=dict)

    def mono_float32(self) -> np.ndarray:
        audio = np.asarray(self.samples)
        audio = np.squeeze(audio)
        if audio.ndim != 1:
            raise ValueError(f"Expected mono audio, got shape {audio.shape}.")
        return audio.astype(np.float32, copy=False)


class TTSBackend(ABC):
    name: str
    capabilities: BackendCapabilities

    @abstractmethod
    def synthesize(self, request: SynthesisRequest) -> AudioChunk:
        """Synthesize exactly one spoken segment."""

    def close(self) -> None:
        """Release backend resources when needed."""
