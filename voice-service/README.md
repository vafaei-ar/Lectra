# Lectra Voice Service

Local narration parsing, voice profiles, speech synthesis, and Telegram delivery for Lectra.

Chatterbox is the default TTS backend after the initial real-voice bake-off. Qwen3-TTS remains optional.

## Production-style local install

```bash
python -m venv .venv-chatterbox
source .venv-chatterbox/bin/activate
python -m pip install -U pip
python -m pip install -e '.[chatterbox,telegram]'
```

FFmpeg is required. For NVIDIA systems, install a PyTorch build compatible with the machine's NVIDIA driver before installing model packages if necessary.

## Simplest run: one terminal, one command

Set the Telegram bot token in your shell environment, then run Lectra:

```bash
export TELEGRAM_BOT_TOKEN='your-token'
lectra
```

`lectra` starts the local FastAPI voice service automatically, waits until it is healthy, then starts the Telegram bot in the same terminal. Press `Ctrl+C` once to stop both. If a healthy local service is already running, Lectra reuses it instead of starting a duplicate.

Defaults:

- data: `~/.local/share/lectra`
- device: `cuda`
- local service: `http://127.0.0.1:8000`

Optional overrides remain available through `LECTRA_DATA_DIR`, `LECTRA_DEVICE`, and `LECTRA_VOICE_SERVICE_URL`, or through `lectra --help`.

## Development and tests

When testing inside a virtual environment, invoke both pip and pytest through that environment's Python. This avoids accidentally using a Conda/base `pytest` executable when both environments are active.

```bash
python -m pip install -e '.[telegram,dev]'
python -m pytest -q
```

To confirm the active interpreter when troubleshooting:

```bash
which python
python -c 'import sys; print(sys.executable)'
python -c 'import soundfile; print(soundfile.__file__)'
```

## Manual two-process mode for debugging

The normal user flow should use `lectra`. The commands below are retained only when debugging the HTTP service and Telegram bot separately.

Terminal 1:

```bash
export LECTRA_DATA_DIR="$HOME/.local/share/lectra"
export LECTRA_DEVICE=cuda
python -m uvicorn lectra_voice.service:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
export TELEGRAM_BOT_TOKEN='your-token'
export LECTRA_VOICE_SERVICE_URL='http://127.0.0.1:8000'
lectra-bot
```

The bot uses long polling. It does not require a public server.

See `../docs/telegram-bot.md` for enrollment, storage, progress reporting, error reporting, and user workflow details.

## CLI

```bash
lectra-voice backends
lectra-voice parse ../examples/example-narration.md
lectra-voice generate ../examples/example-narration.md \
  --reference-audio /path/to/reference.wav \
  --output presentation.mp3
```

Only parsed speech segments are sent to TTS. YAML frontmatter, comments, headings, slide numbers, tables, lists, and code blocks remain non-spoken.
