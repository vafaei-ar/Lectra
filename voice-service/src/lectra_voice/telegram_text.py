from __future__ import annotations

import asyncio
import logging
import os
import re

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from .plain_text import MAX_TELEGRAM_TEXT_CHARS
from .profiles import VoiceProfileError, VoiceStore
from .telegram_upload import (
    clear_pending_upload,
    remember_pending_upload,
    send_audio_with_retry,
    upload_retry_keyboard,
)
from .tts import DEFAULT_BACKEND

LOGGER = logging.getLogger(__name__)
SERVICE_URL = os.getenv("LECTRA_VOICE_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
DEVICE = os.getenv("LECTRA_DEVICE", "cuda")
PROGRESS_POLL_SECONDS = 2.0
MAX_TELEGRAM_AUDIO_BYTES = 50 * 1024 * 1024
TOKEN_RE = re.compile(r"(?<!\d)\d{6,}:[A-Za-z0-9_-]{20,}")
STORE = VoiceStore()


def _redact(value: object, limit: int = 900) -> str:
    return TOKEN_RE.sub("<redacted-bot-token>", str(value))[:limit]


def _response_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict) and payload.get("detail"):
            return _redact(payload["detail"])
    except ValueError:
        pass
    return _redact(response.text or f"HTTP {response.status_code}")


def _progress_bar(percent: int, width: int = 12) -> str:
    percent = max(0, min(int(percent), 100))
    filled = round(width * percent / 100)
    return "█" * filled + "░" * (width - filled)


def _elapsed(seconds: object) -> str:
    try:
        value = max(int(float(seconds)), 0)
    except (TypeError, ValueError):
        value = 0
    minutes, secs = divmod(value, 60)
    return f"{minutes}:{secs:02d}"


def _progress_text(status: dict[str, object]) -> str:
    stage = str(status.get("stage") or "queued")
    completed = int(status.get("completed_segments") or 0)
    total = int(status.get("total_segments") or 0)
    percent = int(status.get("percent") or 0)
    labels = {
        "queued": "Queued",
        "waiting_for_gpu": "Waiting for GPU",
        "loading_model": f"Loading {DEFAULT_BACKEND}",
        "synthesizing": "Reading text",
        "encoding": "Encoding MP3",
        "completed": "Audio ready",
        "failed": "Generation failed",
    }
    label = labels.get(stage, stage.replace("_", " ").title())
    lines = ["Reading your text", label]
    if total:
        lines.extend([
            f"{_progress_bar(percent)} {percent}%",
            f"Chunks: {completed}/{total}",
        ])
    lines.append(f"Elapsed: {_elapsed(status.get('elapsed_seconds'))}")
    return "\n".join(lines)


async def _poll_job(job_id: str, status_message) -> httpx.Response:
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        while True:
            response = await client.get(f"{SERVICE_URL}/v1/jobs/{job_id}")
            if response.status_code != 200:
                raise RuntimeError(
                    f"voice service returned HTTP {response.status_code}: {_response_error(response)}"
                )
            status = response.json()
            await status_message.edit_text(_progress_text(status))
            stage = str(status.get("stage") or "")
            if stage == "completed":
                audio_response = await client.get(f"{SERVICE_URL}/v1/jobs/{job_id}/audio")
                if audio_response.status_code != 200:
                    raise RuntimeError(
                        f"audio retrieval returned HTTP {audio_response.status_code}: "
                        f"{_response_error(audio_response)}"
                    )
                return audio_response
            if stage == "failed":
                raise RuntimeError(_redact(status.get("error") or "unknown rendering error"))
            await asyncio.sleep(PROGRESS_POLL_SECONDS)


async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or message.text is None:
        return

    if context.user_data.get("awaiting_voice_sample"):
        await message.reply_text(
            "Voice setup is waiting for a recording. Please send the requested voice/audio sample, "
            "or start over with /setupvoice later."
        )
        return

    text = message.text.strip()
    if not text:
        return
    if len(text) > MAX_TELEGRAM_TEXT_CHARS:
        await message.reply_text(
            f"Text is too long. Send at most {MAX_TELEGRAM_TEXT_CHARS} characters per message."
        )
        return

    user_id = int(update.effective_user.id) if update.effective_user is not None else 0
    try:
        voice = STORE.get_voice(user_id)
    except VoiceProfileError:
        await message.reply_text("Set up a voice first with /setupvoice.")
        return

    status_message = await message.reply_text(
        f"Reading your text\nQueued\n{_progress_bar(0)} 0%\nElapsed: 0:00"
    )
    payload = {
        "telegram_user_id": user_id,
        "text": text,
        "voice_id": voice.voice_id,
        "backend": DEFAULT_BACKEND,
        "device": DEVICE,
        "output_format": "mp3",
    }

    try:
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{SERVICE_URL}/v1/text/jobs", json=payload)
        if response.status_code != 202:
            raise RuntimeError(
                f"voice service returned HTTP {response.status_code}: {_response_error(response)}"
            )
        job_id = str(response.json()["job_id"])
        audio_response = await _poll_job(job_id, status_message)
        if len(audio_response.content) > MAX_TELEGRAM_AUDIO_BYTES:
            raise RuntimeError("generated MP3 exceeds Telegram's 50 MB bot upload limit")
    except (httpx.HTTPError, RuntimeError, KeyError, ValueError) as exc:
        LOGGER.exception("Plain-text TTS failed")
        await status_message.edit_text(
            "Could not read this text.\n\n"
            f"{_redact(exc)}\n\n"
            "Send the text again to retry."
        )
        return

    remember_pending_upload(
        context,
        job_id=job_id,
        title="Text message",
        filename="text-message.mp3",
        caption=f"Read locally with {DEFAULT_BACKEND}.",
        done_text="Done: text read aloud.",
    )
    await status_message.edit_text("Reading your text\nUploading MP3 to Telegram")
    try:
        await send_audio_with_retry(
            message=message,
            audio_bytes=audio_response.content,
            filename="text-message.mp3",
            title="Text message",
            caption=f"Read locally with {DEFAULT_BACKEND}.",
            status_message=status_message,
            status_prefix="Reading your text\nUploading MP3 to Telegram",
        )
    except Exception as exc:
        LOGGER.exception("Telegram text-audio upload failed")
        await status_message.edit_text(
            "Audio generation succeeded, but Telegram upload failed:\n"
            f"{_redact(exc)}\n\n"
            "The generated audio is still available locally. Retry the upload without regenerating it.",
            reply_markup=upload_retry_keyboard(),
        )
        return

    clear_pending_upload(context)
    await status_message.edit_text("Done: text read aloud.")
