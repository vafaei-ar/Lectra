from __future__ import annotations

import asyncio
import io
import logging
import os
import re
import tempfile
from pathlib import Path

import httpx
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .enrollment import REFERENCE_VOICE_SCRIPT, AudioPreparationError, normalize_reference_audio
from .models import SpeechSegment
from .parser import NarrationParseError, parse_narration
from .profiles import VoiceProfileError, VoiceStore
from .tts import DEFAULT_BACKEND


LOGGER = logging.getLogger(__name__)
MAX_TELEGRAM_DOWNLOAD_BYTES = 20 * 1024 * 1024
MAX_NARRATION_BYTES = 2 * 1024 * 1024
MAX_TELEGRAM_AUDIO_BYTES = 50 * 1024 * 1024
PROGRESS_POLL_SECONDS = 2.0
TOKEN_RE = re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b")

STORE = VoiceStore()
SERVICE_URL = os.getenv("LECTRA_VOICE_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
DEVICE = os.getenv("LECTRA_DEVICE", "cuda")


def _user_id(update: Update) -> int:
    if update.effective_user is None:
        raise RuntimeError("Telegram update has no user.")
    return int(update.effective_user.id)


def _voice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("I confirm", callback_data="voice-consent:yes"),
            InlineKeyboardButton("Cancel", callback_data="voice-consent:no"),
        ]]
    )


def _generation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("Generate audio", callback_data="narration:generate"),
            InlineKeyboardButton("Cancel", callback_data="narration:cancel"),
        ]]
    )


def _redact_secrets(value: object, limit: int = 900) -> str:
    text = TOKEN_RE.sub("<redacted-bot-token>", str(value))
    return text[:limit]


def _response_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if detail:
            return _redact_secrets(detail)
    except ValueError:
        pass
    return _redact_secrets(response.text or f"HTTP {response.status_code}")


def _progress_bar(percent: int, width: int = 12) -> str:
    percent = max(0, min(int(percent), 100))
    filled = round(width * percent / 100)
    return "█" * filled + "░" * (width - filled)


def _format_elapsed(seconds: object) -> str:
    try:
        value = max(int(float(seconds)), 0)
    except (TypeError, ValueError):
        value = 0
    minutes, secs = divmod(value, 60)
    return f"{minutes}:{secs:02d}"


def _progress_text(title: str, status: dict[str, object]) -> str:
    stage = str(status.get("stage") or "queued")
    completed = int(status.get("completed_segments") or 0)
    total = int(status.get("total_segments") or 0)
    percent = int(status.get("percent") or 0)
    elapsed = _format_elapsed(status.get("elapsed_seconds"))
    labels = {
        "queued": "Queued",
        "waiting_for_gpu": "Waiting for GPU",
        "loading_model": f"Loading {DEFAULT_BACKEND}",
        "synthesizing": "Generating speech",
        "encoding": "Encoding MP3",
        "completed": "Generation complete",
        "failed": "Generation failed",
    }
    label = labels.get(stage, stage.replace("_", " ").title())
    lines = [f"Generating: {title}", label]
    if total:
        lines.extend([
            f"{_progress_bar(percent)} {percent}%",
            f"Segments: {completed}/{total}",
        ])
    lines.append(f"Elapsed: {elapsed}")
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None
    await update.message.reply_text(
        "Lectra turns a presentation narration Markdown file into presentation-style audio.\n\n"
        "1. Run /setupvoice once.\n"
        "2. Send a presentation-narration.md file.\n"
        "3. Tap Generate audio.\n\n"
        "Telegram transports your messages and files. Lectra stores the voice profile and runs "
        "TTS locally; it does not send the voice sample to a separate cloud TTS service."
    )


async def setup_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None
    voice_id = context.args[0] if context.args else "default"
    try:
        STORE.voice_dir(_user_id(update), voice_id)
    except VoiceProfileError as exc:
        await update.message.reply_text(str(exc))
        return
    context.user_data["pending_voice_id"] = voice_id
    context.user_data.pop("awaiting_voice_sample", None)
    await update.message.reply_text(
        "Before creating a voice profile, confirm that this recording is your own voice "
        "or that you have permission from the speaker to create this profile.",
        reply_markup=_voice_keyboard(),
    )


async def voice_consent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    decision = (query.data or "").split(":", 1)[-1]
    if decision != "yes":
        context.user_data.pop("pending_voice_id", None)
        context.user_data.pop("awaiting_voice_sample", None)
        await query.edit_message_text("Voice setup cancelled.")
        return
    context.user_data["awaiting_voice_sample"] = True
    await query.edit_message_text(
        "Consent confirmed. Now record yourself reading the text below in your normal "
        "presentation voice, then send the recording here as a Telegram voice message or audio file."
    )
    assert query.message is not None
    await query.message.reply_text(REFERENCE_VOICE_SCRIPT)


async def _download_telegram_file(file_id: str, destination: Path, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_file = await context.bot.get_file(file_id)
    await telegram_file.download_to_drive(custom_path=destination)


async def receive_voice_sample(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return
    if not context.user_data.get("awaiting_voice_sample"):
        await message.reply_text("Use /setupvoice before sending a voice sample.")
        return
    document_audio = message.document if message.document and (message.document.mime_type or "").startswith("audio/") else None
    attachment = message.voice or message.audio or document_audio
    if attachment is None:
        return
    file_size = getattr(attachment, "file_size", None)
    if file_size and file_size > MAX_TELEGRAM_DOWNLOAD_BYTES:
        await message.reply_text("That recording is too large for the Telegram Bot API. Please send a shorter sample.")
        return
    voice_id = str(context.user_data.get("pending_voice_id") or "default")
    suffix = ".ogg" if message.voice else Path(getattr(attachment, "file_name", "sample.mp3") or "sample.mp3").suffix
    if not suffix:
        suffix = ".audio"
    await message.reply_chat_action(ChatAction.TYPING)
    try:
        with tempfile.TemporaryDirectory(prefix="lectra-enroll-") as temp_dir:
            source = Path(temp_dir) / f"source{suffix}"
            prepared = Path(temp_dir) / "reference.wav"
            await _download_telegram_file(attachment.file_id, source, context)
            await asyncio.to_thread(normalize_reference_audio, source, prepared)
            await asyncio.to_thread(
                STORE.save_voice,
                user_id=_user_id(update),
                source_wav=prepared,
                voice_id=voice_id,
                consent_confirmed=True,
                reference_text=REFERENCE_VOICE_SCRIPT,
                backend=DEFAULT_BACKEND,
            )
    except (AudioPreparationError, VoiceProfileError, OSError) as exc:
        LOGGER.exception("Voice enrollment failed")
        await message.reply_text(f"Voice setup failed: {_redact_secrets(exc)}")
        return
    context.user_data.pop("pending_voice_id", None)
    context.user_data.pop("awaiting_voice_sample", None)
    await message.reply_text(f"Voice profile '{voice_id}' is ready. Send a presentation-narration.md file when you are ready.")


async def list_voices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None
    user_id = _user_id(update)
    voices = STORE.list_voices(user_id)
    if not voices:
        await update.message.reply_text("No voice profile yet. Use /setupvoice.")
        return
    default = STORE.default_voice_id(user_id)
    lines = ["Your Lectra voice profiles:"]
    for voice in voices:
        marker = " (default)" if voice.voice_id == default else ""
        lines.append(f"- {voice.voice_id}{marker}")
    await update.message.reply_text("\n".join(lines))


async def set_default_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None
    if not context.args:
        await update.message.reply_text("Usage: /defaultvoice <voice-name>")
        return
    try:
        STORE.set_default_voice(_user_id(update), context.args[0])
    except VoiceProfileError as exc:
        await update.message.reply_text(str(exc))
        return
    await update.message.reply_text(f"Default voice set to '{context.args[0]}'.")


async def delete_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None
    user_id = _user_id(update)
    voice_id = context.args[0] if context.args else STORE.default_voice_id(user_id)
    if not voice_id:
        await update.message.reply_text("No voice profile to delete.")
        return
    try:
        deleted = STORE.delete_voice(user_id, voice_id)
    except VoiceProfileError as exc:
        await update.message.reply_text(str(exc))
        return
    if deleted:
        await update.message.reply_text(
            f"Voice profile '{voice_id}' deleted from Lectra's local storage. "
            "This does not delete the original Telegram message that carried the recording."
        )
    else:
        await update.message.reply_text(f"Voice profile '{voice_id}' was not found.")


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None
    default_voice = STORE.default_voice_id(_user_id(update)) or "not configured"
    await update.message.reply_text(
        f"Default TTS: {DEFAULT_BACKEND}\nDefault voice: {default_voice}\nDevice: {DEVICE}\nLocal service: {SERVICE_URL}"
    )


def _estimate_minutes(parsed) -> float:
    words = sum(len(segment.text.split()) for segment in parsed.segments if isinstance(segment, SpeechSegment))
    return max(words / 145.0, 0.1)


async def receive_narration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or message.document is None:
        return
    document = message.document
    filename = document.file_name or ""
    if not filename.lower().endswith(".md"):
        await message.reply_text("Please send a Lectra presentation-narration.md file.")
        return
    if document.file_size and document.file_size > MAX_NARRATION_BYTES:
        await message.reply_text("That Markdown file is unexpectedly large. Lectra limits narration files to 2 MB.")
        return
    try:
        STORE.get_voice(_user_id(update))
    except VoiceProfileError:
        await message.reply_text("Set up a voice first with /setupvoice.")
        return
    try:
        with tempfile.TemporaryDirectory(prefix="lectra-md-") as temp_dir:
            path = Path(temp_dir) / "narration.md"
            await _download_telegram_file(document.file_id, path, context)
            markdown = path.read_text(encoding="utf-8")
        parsed = parse_narration(markdown)
    except UnicodeDecodeError:
        await message.reply_text("The narration file must be UTF-8 Markdown.")
        return
    except (NarrationParseError, OSError) as exc:
        await message.reply_text(f"Narration validation failed: {_redact_secrets(exc)}")
        return
    title = str(parsed.metadata.get("title") or "Presentation")
    minutes = _estimate_minutes(parsed)
    context.user_data["pending_narration"] = markdown
    context.user_data["pending_title"] = title
    context.user_data["pending_minutes"] = minutes
    await message.reply_text(
        f"Ready to generate: {title}\nSpeech segments: {sum(isinstance(s, SpeechSegment) for s in parsed.segments)}\nEstimated speech time: about {minutes:.1f} minutes",
        reply_markup=_generation_keyboard(),
    )


async def narration_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    action = (query.data or "").split(":", 1)[-1]
    if action == "cancel":
        context.user_data.pop("pending_narration", None)
        context.user_data.pop("pending_title", None)
        context.user_data.pop("pending_minutes", None)
        await query.edit_message_text("Generation cancelled.")
        return
    markdown = context.user_data.get("pending_narration")
    if not isinstance(markdown, str):
        await query.edit_message_text("No pending narration. Send the Markdown file again.")
        return
    user_id = _user_id(update)
    voice_id = STORE.default_voice_id(user_id)
    if not voice_id:
        await query.edit_message_text("No default voice profile. Use /setupvoice first.")
        return
    title = str(context.user_data.get("pending_title") or "Presentation")
    payload = {
        "telegram_user_id": user_id,
        "markdown": markdown,
        "voice_id": voice_id,
        "backend": DEFAULT_BACKEND,
        "device": DEVICE,
        "output_format": "mp3",
    }
    try:
        await query.edit_message_text(f"Starting audio generation: {title}")
        timeout = httpx.Timeout(120.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{SERVICE_URL}/v1/render/jobs", json=payload)
            if response.status_code != 202:
                raise RuntimeError(f"voice service returned HTTP {response.status_code}: {_response_error(response)}")
            job = response.json()
            job_id = str(job.get("job_id") or "")
            if not job_id:
                raise RuntimeError("voice service did not return a render job ID")
            last_text = ""
            while True:
                status_response = await client.get(f"{SERVICE_URL}/v1/render/jobs/{job_id}")
                if status_response.status_code != 200:
                    raise RuntimeError(
                        f"could not read generation status: HTTP {status_response.status_code}: {_response_error(status_response)}"
                    )
                status = status_response.json()
                state = str(status.get("state") or "")
                progress_text = _progress_text(title, status)
                if progress_text != last_text:
                    await query.edit_message_text(progress_text)
                    last_text = progress_text
                if state == "failed":
                    raise RuntimeError(str(status.get("error") or "audio generation failed"))
                if state == "completed":
                    break
                await asyncio.sleep(PROGRESS_POLL_SECONDS)
            await query.edit_message_text(f"Generation complete: {title}\nUploading MP3 to Telegram...")
            audio_response = await client.get(f"{SERVICE_URL}/v1/render/jobs/{job_id}/audio")
            if audio_response.status_code != 200:
                raise RuntimeError(
                    f"could not retrieve generated audio: HTTP {audio_response.status_code}: {_response_error(audio_response)}"
                )
            if len(audio_response.content) > MAX_TELEGRAM_AUDIO_BYTES:
                raise RuntimeError("generated MP3 exceeds Telegram's 50 MB bot upload limit")
        audio = io.BytesIO(audio_response.content)
        audio.name = "presentation.mp3"
        if query.message is None:
            raise RuntimeError("Telegram callback message is unavailable for audio delivery")
        await query.message.reply_audio(
            audio=audio,
            title=title,
            performer="Lectra",
            caption=f"Generated locally with {DEFAULT_BACKEND}.",
        )
        await query.edit_message_text(f"Done: {title}")
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        safe_error = _redact_secrets(exc)
        LOGGER.exception("Narration generation failed")
        await query.edit_message_text(
            f"Generation failed: {title}\n\n{safe_error}\n\nYou can retry generation.",
            reply_markup=_generation_keyboard(),
        )
        return
    context.user_data.pop("pending_narration", None)
    context.user_data.pop("pending_title", None)
    context.user_data.pop("pending_minutes", None)


async def service_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICE_URL}/health")
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        await update.message.reply_text(f"Lectra voice service is unavailable: {_redact_secrets(exc)}")
        return
    await update.message.reply_text(
        f"Service: {payload.get('status', 'unknown')}\nVersion: {payload.get('version', 'unknown')}\nDefault TTS: {payload.get('default_tts_backend', 'unknown')}\nProgress reporting: {'yes' if payload.get('render_job_progress') else 'no'}"
    )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    safe_error = _redact_secrets(error or "unknown error")
    if isinstance(error, BaseException):
        LOGGER.error("Unhandled Telegram bot error: %s", safe_error, exc_info=(type(error), error, error.__traceback__))
    else:
        LOGGER.error("Unhandled Telegram bot error: %s", safe_error)
    if isinstance(update, Update) and update.effective_message is not None:
        try:
            await update.effective_message.reply_text(f"Lectra encountered an unexpected error:\n{safe_error}")
        except Exception:
            LOGGER.exception("Could not send Telegram error message")


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([
        BotCommand("start", "How to use Lectra"),
        BotCommand("setupvoice", "Create or replace a voice profile"),
        BotCommand("voices", "List local voice profiles"),
        BotCommand("defaultvoice", "Select a default voice profile"),
        BotCommand("deletevoice", "Delete a local voice profile"),
        BotCommand("settings", "Show Lectra settings"),
        BotCommand("health", "Check the local voice service"),
    ])


def build_application(token: str) -> Application:
    application = Application.builder().token(token).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setupvoice", setup_voice))
    application.add_handler(CommandHandler("voices", list_voices))
    application.add_handler(CommandHandler("defaultvoice", set_default_voice))
    application.add_handler(CommandHandler("deletevoice", delete_voice))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("health", service_health))
    application.add_handler(CallbackQueryHandler(voice_consent, pattern=r"^voice-consent:"))
    application.add_handler(CallbackQueryHandler(narration_action, pattern=r"^narration:"))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.Document.AUDIO, receive_voice_sample))
    application.add_handler(MessageHandler(filters.Document.ALL, receive_narration))
    application.add_error_handler(on_error)
    return application


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LECTRA_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required.")
    build_application(token).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
