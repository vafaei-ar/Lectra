import pytest

pytest.importorskip("telegram")

from telegram.error import NetworkError

from lectra_voice.telegram_bot import (
    _is_transient_telegram_error,
    _progress_text,
    _redact_secrets,
)


def test_progress_text_shows_segment_progress():
    text = _progress_text(
        "Test talk",
        {
            "stage": "synthesizing",
            "completed_segments": 3,
            "total_segments": 6,
            "percent": 50,
            "elapsed_seconds": 65,
        },
    )
    assert "Generating speech" in text
    assert "50%" in text
    assert "Segments: 3/6" in text
    assert "Elapsed: 1:05" in text


def test_redact_secrets_hides_telegram_bot_token():
    token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
    redacted = _redact_secrets(f"https://api.telegram.org/bot{token}/getUpdates")
    assert token not in redacted
    assert "<redacted-bot-token>" in redacted


def test_network_error_is_treated_as_transient():
    assert _is_transient_telegram_error(NetworkError("Bad Gateway")) is True
    assert _is_transient_telegram_error(RuntimeError("render failed")) is False
