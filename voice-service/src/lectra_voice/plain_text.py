from __future__ import annotations

import re

from .models import SpeechSegment

MAX_TELEGRAM_TEXT_CHARS = 4096
DEFAULT_CHUNK_CHARS = 420
_SENTENCE_BREAK_RE = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE_RE = re.compile(r"\s+")


class PlainTextError(ValueError):
    pass


def _split_long_piece(text: str, max_chars: int) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        if len(word) > max_chars:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_len = 0
            for start in range(0, len(word), max_chars):
                chunks.append(word[start : start + max_chars])
            continue

        added = len(word) if not current else len(word) + 1
        if current and current_len + added > max_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += added

    if current:
        chunks.append(" ".join(current))
    return chunks


def speech_segments_from_text(
    text: str,
    *,
    max_chars: int = DEFAULT_CHUNK_CHARS,
) -> list[SpeechSegment]:
    """Convert a Telegram text message into stable TTS-sized speech segments.

    Whitespace is normalized for speech, while wording and punctuation are retained.
    Sentence boundaries are preferred; exceptionally long sentences fall back to
    word-boundary chunking.
    """

    if max_chars < 40:
        raise PlainTextError("Plain-text chunk size must be at least 40 characters.")

    stripped = text.strip()
    if not stripped:
        raise PlainTextError("Text message is empty.")
    if len(stripped) > MAX_TELEGRAM_TEXT_CHARS:
        raise PlainTextError(
            f"Text message exceeds Telegram's {MAX_TELEGRAM_TEXT_CHARS}-character limit."
        )

    normalized = _WHITESPACE_RE.sub(" ", stripped)
    sentences = [part.strip() for part in _SENTENCE_BREAK_RE.split(normalized) if part.strip()]
    if not sentences:
        sentences = [normalized]

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        pieces = [sentence] if len(sentence) <= max_chars else _split_long_piece(sentence, max_chars)
        for piece in pieces:
            candidate = piece if not current else f"{current} {piece}"
            if current and len(candidate) > max_chars:
                chunks.append(current)
                current = piece
            else:
                current = candidate
    if current:
        chunks.append(current)

    return [SpeechSegment(text=chunk, pace="normal", tone="explanatory") for chunk in chunks]
