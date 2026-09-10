# Lectra Voice Service

Local narration parsing, voice profiles, speech synthesis, and Telegram delivery for Lectra.

Chatterbox is the default TTS backend after the initial real-voice bake-off. Qwen3-TTS remains optional.

## Production-style local install

```bash
python -m venv .venv-chatterbox
source .venv-chatterbox/bin/activate
python -m pip install -U pip
pip install -e '.[chatterbox,telegram]'
```

FFmpeg is required. For NVIDIA systems, install a PyTorch build compatible with the machine's NVIDIA driver before installing model packages if necessary.

## Run the service

```bash
export LECTRA_DATA_DIR="$HOME/.local/share/lectra"
export LECTRA_DEVICE=cuda
uvicorn lectra_voice.service:app --host 127.0.0.1 --port 8000
```

The service keeps the TTS backend warm after first use and serializes GPU rendering jobs.

## Run the Telegram bot

```bash
export TELEGRAM_BOT_TOKEN='your-token'
export LECTRA_VOICE_SERVICE_URL='http://127.0.0.1:8000'
lectra-bot
```

The bot uses long polling. It does not require a public server.

See `../docs/telegram-bot.md` for enrollment, storage, and user workflow details.

## CLI

```bash
lectra-voice backends
lectra-voice parse ../examples/example-narration.md
lectra-voice generate ../examples/example-narration.md \
  --reference-audio /path/to/reference.wav \
  --output presentation.mp3
```

Only parsed speech segments are sent to TTS. YAML frontmatter, comments, headings, slide numbers, tables, lists, and code blocks remain non-spoken.
