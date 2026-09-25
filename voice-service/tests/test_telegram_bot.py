import pytest

pytest.importorskip("telegram")

from telegram.error import NetworkError

from lectra_voice.telegram_bot import (
    _is_transient_telegram_error,
    _progress_text,
    _redact_secrets,
    _voice_alias,
    _voice_selection_keyboard,
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


def test_voice_selection_keyboard_offers_two_us_presets_and_personal_setup():
    keyboard = _voice_selection_keyboard()
    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
    ]
    assert "voice-select:us-woman" in callbacks
    assert "voice-select:us-man" in callbacks
    assert "voice-select:setup" in callbacks


def test_voice_aliases_map_simple_gender_names():
    assert _voice_alias("woman") == "us-woman"
    assert _voice_alias("female") == "us-woman"
    assert _voice_alias("man") == "us-man"
    assert _voice_alias("male") == "us-man"
    assert _voice_alias("my-custom-voice") == "my-custom-voice"
