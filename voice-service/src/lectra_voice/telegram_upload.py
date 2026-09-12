from __future__ import annotations

import asyncio
import io
import logging
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import NetworkError

LOGGER = logging.getLogger(__name__)

TELEGRAM_UPLOAD_WRITE_TIMEOUT = 600.0
TELEGRAM_UPLOAD_READ_TIMEOUT = 120.0
TELEGRAM_UPLOAD_CONNECT_TIMEOUT = 30.0
TELEGRAM_UPLOAD_POOL_TIMEOUT = 30.0
TELEGRAM_UPLOAD_ATTEMPTS = 2


def upload_retry_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("Retry upload", callback_data="upload:retry"),
            InlineKeyboardButton("Dismiss", callback_data="upload:dismiss"),
        ]]
    )


def remember_pending_upload(
    context: Any,
    *,
    job_id: str,
    title: str,
    filename: str,
    caption: str,
    done_text: str,
) -> None:
    context.user_data["pending_upload"] = {
        "job_id": job_id,
        "title": title,
        "filename": filename,
        "caption": caption,
        "done_text": done_text,
    }


def clear_pending_upload(context: Any) -> None:
    context.user_data.pop("pending_upload", None)


async def send_audio_with_retry(
    *,
    message: Any,
    audio_bytes: bytes,
    filename: str,
    title: str,
    caption: str,
    status_message: Any | None = None,
    status_prefix: str = "Uploading MP3 to Telegram",
) -> None:
    """Upload audio with generous media timeouts and one transient-network retry."""

    last_error: Exception | None = None
    for attempt in range(1, TELEGRAM_UPLOAD_ATTEMPTS + 1):
        payload = io.BytesIO(audio_bytes)
        payload.name = filename
        try:
            await message.reply_audio(
                audio=payload,
                title=title,
                performer="Lectra",
                caption=caption,
                read_timeout=TELEGRAM_UPLOAD_READ_TIMEOUT,
                write_timeout=TELEGRAM_UPLOAD_WRITE_TIMEOUT,
                connect_timeout=TELEGRAM_UPLOAD_CONNECT_TIMEOUT,
                pool_timeout=TELEGRAM_UPLOAD_POOL_TIMEOUT,
            )
            return
        except NetworkError as exc:
            last_error = exc
            LOGGER.warning(
                "Telegram audio upload attempt %d/%d failed: %s",
                attempt,
                TELEGRAM_UPLOAD_ATTEMPTS,
                exc,
            )
            if attempt >= TELEGRAM_UPLOAD_ATTEMPTS:
                break
            if status_message is not None:
                try:
                    await status_message.edit_text(
                        f"{status_prefix}\nTelegram timed out. Retrying upload "
                        f"({attempt + 1}/{TELEGRAM_UPLOAD_ATTEMPTS})..."
                    )
                except Exception:
                    LOGGER.debug("Could not update Telegram upload-retry status", exc_info=True)
            await asyncio.sleep(2.0)

    assert last_error is not None
    raise last_error
