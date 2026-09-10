from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from lectra_voice.models import SpeechSegment


@dataclass(frozen=True)
class TTSCapabilities:
    voice_cloning: bool
    pace_control: bool
    tone_control: bool
    multilingual: bool


class TTSBackend(ABC):
    """Provider-neutral interface for local TTS implementations."""

    name: str

    @abstractmethod
    def capabilities(self) -> TTSCapabilities:
        raise NotImplementedError

    @abstractmethod
    def synthesize(
        self,
        segment: SpeechSegment,
        *,
        voice_reference: Path,
        output_path: Path,
    ) -> Path:
        """Render one speech segment and return the created audio path."""
        raise NotImplementedError
