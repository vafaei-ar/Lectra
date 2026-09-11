import pytest

from lectra_voice.plain_text import MAX_TELEGRAM_TEXT_CHARS, PlainTextError, speech_segments_from_text


def test_plain_text_normalizes_whitespace_without_changing_words():
    segments = speech_segments_from_text("Hello   everyone.\nThis is a test.")
    assert [segment.text for segment in segments] == ["Hello everyone. This is a test."]


def test_plain_text_prefers_sentence_boundaries_for_chunks():
    text = "First sentence is short. Second sentence is also short. Third sentence is here."
    segments = speech_segments_from_text(text, max_chars=45)
    assert len(segments) >= 2
    assert all(len(segment.text) <= 45 for segment in segments)
    assert " ".join(segment.text for segment in segments) == text


def test_plain_text_rejects_empty_text():
    with pytest.raises(PlainTextError, match="empty"):
        speech_segments_from_text("   ")


def test_plain_text_rejects_over_telegram_limit():
    with pytest.raises(PlainTextError, match="exceeds Telegram"):
        speech_segments_from_text("x" * (MAX_TELEGRAM_TEXT_CHARS + 1))
