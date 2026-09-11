# Telegram bot MVP

Lectra's Telegram bot is a thin local client for the Lectra Voice Service. It uses long polling, so the local machine does not need a public URL or webhook.

## Privacy boundary

Telegram transports the enrollment recording, narration file, and returned MP3. Lectra does not send the voice sample or narration to a separate cloud TTS/LLM service.

- Lectra's persistent voice-profile copy is stored under `LECTRA_DATA_DIR` on the local Lectra machine.
- Users are isolated by immutable numeric Telegram user ID.
- The bot requires explicit ownership/permission confirmation before saving a voice profile.
- `/deletevoice` removes Lectra's local voice-profile copy. It does not delete the original Telegram message containing the recording.
- Bot tokens are read only from `TELEGRAM_BOT_TOKEN`; never commit tokens or voice recordings.
- Routine `httpx` and `httpcore` INFO transport logs are suppressed because Telegram Bot API URLs contain the bot token.
- If a bot token appears in a terminal log, chat, screenshot, issue, or other shared material, revoke it with BotFather and replace `TELEGRAM_BOT_TOKEN` before continuing.
- Run the FastAPI service on `127.0.0.1` unless you intentionally add authentication and network controls.

Default data location:

```text
~/.local/share/lectra/
└── users/
    └── <telegram_user_id>/
        ├── profile.json
        └── voices/
            └── default/
                ├── metadata.json
                └── reference.wav
```

## Install

Use the Chatterbox environment selected during the bake-off:

```bash
cd voice-service
source .venv-chatterbox/bin/activate
python -m pip install -e '.[chatterbox,telegram,dev]'
```

FFmpeg must be available on PATH.

## Configure

```bash
export TELEGRAM_BOT_TOKEN='your-bot-token'
export LECTRA_DATA_DIR="$HOME/.local/share/lectra"
export LECTRA_DEVICE='cuda'
export LECTRA_VOICE_SERVICE_URL='http://127.0.0.1:8000'
```

## Run

Terminal 1:

```bash
python -m uvicorn lectra_voice.service:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
lectra-bot
```

## User flow

1. `/setupvoice`
2. Confirm voice ownership/permission.
3. Read the neutral reference script and send the recording as a Telegram voice message or audio file.
4. Send `presentation-narration.md` as a document.
5. Review the parsed title, segment count, and estimated duration.
6. Tap **Generate audio**.
7. The bot starts a local render job and edits the Telegram status message as the job moves through **waiting for GPU**, **loading model**, **generating speech**, and **encoding MP3**.
8. During speech synthesis the bot reports completed/total speech segments, percentage, a progress bar, and elapsed time.
9. If generation fails, the Telegram message shows a sanitized error and restores the **Generate audio** button for retry.
10. When generation finishes, the bot returns `presentation.mp3` through Telegram's audio player.

Useful commands:

- `/voices`
- `/defaultvoice <name>`
- `/deletevoice [name]`
- `/settings`
- `/health`

`/setupvoice <name>` can be used to create more than one local voice profile.

## Error handling

The bot registers a global error handler so unexpected Telegram-handler errors are reported to the user instead of only appearing in the terminal. Known generation errors are reported directly in the generation status message.

Error text is sanitized before it is sent to Telegram. Strings matching Telegram bot-token syntax are replaced with `<redacted-bot-token>`.

The `/health` command reports whether the local service supports render-job progress reporting.

## Telegram limits used by the MVP

The Bot API currently allows bot downloads up to 20 MB and audio uploads up to 50 MB. Lectra additionally limits narration Markdown to 2 MB because normal narration files should be far smaller.

Lectra encodes final speech MP3s as 96 kbps mono. At that bitrate a 45-minute presentation is roughly 32 MB, leaving useful headroom under Telegram's 50 MB bot upload limit.
