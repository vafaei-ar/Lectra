from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Pace = Literal["slow", "normal", "fast"]
Tone = Literal["explanatory", "serious", "enthusiastic", "reflective"]


class SpeechSegment(BaseModel):
    type: Literal["speech"] = "speech"
    slide: int | None = None
    text: str = Field(min_length=1)
    pace: Pace = "normal"
    tone: Tone = "explanatory"


class PauseSegment(BaseModel):
    type: Literal["pause"] = "pause"
    slide: int | None = None
    duration_ms: int = Field(gt=0)


NarrationSegment = SpeechSegment | PauseSegment


class ParsedNarration(BaseModel):
    metadata: dict[str, object]
    segments: list[NarrationSegment]
    warnings: list[str] = []


class ParseRequest(BaseModel):
    markdown: str = Field(min_length=1)
