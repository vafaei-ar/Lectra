import asyncio

import pytest

pytest.importorskip("telegram")

from telegram.error import NetworkError

from lectra_voice.telegram_upload import (
    TELEGRAM_UPLOAD_ATTEMPTS,
    TELEGRAM_UPLOAD_WRITE_TIMEOUT,
    clear_pending_upload,
    remember_pending_upload,
    send_audio_with_retry,
    upload_retry_keyboard,
)


class _FakeMessage:
    def __init__(self):
        self.calls = []

    async def reply_audio(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            raise NetworkError("Timed out")
        return object()


class _FakeStatus:
    def __init__(self):
        self.updates = []

    async def edit_text(self, text, **kwargs):
        self.updates.append((text, kwargs))


class _FakeContext:
    def __init__(self):
        self.user_data = {}


def test_audio_upload_uses_long_timeout_and_retries_transient_failure():
    message = _FakeMessage()
    status = _FakeStatus()

    asyncio.run(
        send_audio_with_retry(
            message=message,
            audio_bytes=b"fake-mp3",
            filename="presentation.mp3",
            title="Test",
            caption="Test caption",
            status_message=status,
        )
    )

    assert TELEGRAM_UPLOAD_ATTEMPTS == 2
    assert len(message.calls) == 2
    assert message.calls[0]["write_timeout"] == TELEGRAM_UPLOAD_WRITE_TIMEOUT
    assert TELEGRAM_UPLOAD_WRITE_TIMEOUT >= 600
    assert any("Retrying upload" in text for text, _ in status.updates)


def test_pending_upload_can_be_retained_and_cleared_without_rerendering():
    context = _FakeContext()
    remember_pending_upload(
        context,
        job_id="abc123",
        title="Test presentation",
        filename="presentation.mp3",
        caption="Generated locally.",
        done_text="Done: Test presentation",
    )
    assert context.user_data["pending_upload"]["job_id"] == "abc123"
    clear_pending_upload(context)
    assert "pending_upload" not in context.user_data


def test_retry_keyboard_has_upload_only_action():
    keyboard = upload_retry_keyboard()
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert "upload:retry" in callbacks
    assert "upload:dismiss" in callbacks
