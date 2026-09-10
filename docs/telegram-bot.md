# Telegram bot MVP

Lectra's Telegram bot is a thin local client for the Lectra Voice Service. It uses long polling, so the local machine does not need a public URL or webhook.

## Privacy boundary

- Voice recordings are stored only under `LECTRA_DATA_DIR` on the local Lectra machine.
- Users are isolated by immutable numeric Telegram user ID.
- The bot requires an explicit ownership/permission confirmation before saving a voice profile.
- `/deletevoice` removes the local voice profile.
- Bot tokens are read only from `TELEGRAM_BOT_TOKEN`; never commit tokens or voice recordings.
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
pip install -e '.[chatterbox,telegram]'
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
uvicorn lectra_voice.service:app --host 127.0.0.1 --port 8000
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
7. The bot calls the local voice service and returns `presentation.mp3` through Telegram's audio player.

Useful commands:

- `/voices`
- `/defaultvoice <name>`
- `/deletevoice [name]`
- `/settings`
- `/health`

`/setupvoice <name>` can be used to create more than one local voice profile.

## Telegram limits used by the MVP

The Bot API currently allows bot downloads up to 20 MB and audio uploads up to 50 MB. Lectra additionally limits narration Markdown to 2 MB because normal narration files should be far smaller.
