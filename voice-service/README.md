# Lectra Voice Service

Local narration parsing, voice profiles, speech synthesis, and Telegram delivery for Lectra.

Chatterbox is the default TTS backend after the initial real-voice bake-off. Qwen3-TTS remains optional.

## Install

Use the Chatterbox environment selected during the bake-off:

```bash
python -m venv .venv-chatterbox
source .venv-chatterbox/bin/activate
python -m pip install -U pip
python -m pip install -e '.[chatterbox,telegram]'
```

FFmpeg is required. For NVIDIA systems, install a PyTorch build compatible with the machine's NVIDIA driver before installing model packages if necessary.

## Normal operation: background service

Lectra is managed as a **user-level systemd service**. No sudo is required and no terminal needs to stay open.

On the first run, configure the Telegram token securely:

```bash
lectra configure
```

The token prompt is hidden. Lectra stores its local service configuration in a private file under `~/.config/lectra/` (or `$XDG_CONFIG_HOME/lectra/`) with mode `0600`.

Then manage Lectra with:

```bash
lectra start
lectra status
lectra restart
lectra stop
lectra logs
```

`lectra start` installs or refreshes the user systemd unit, starts the local voice service and Telegram bot, verifies the voice-service API, and returns control to the shell. Closing the terminal does not stop Lectra.

For live logs without affecting the service:

```bash
lectra logs --follow
```

Pressing `Ctrl+C` while following logs only exits the log viewer. It does **not** stop Lectra.

Optional autostart at user login:

```bash
lectra enable
```

Disable autostart without stopping an already-running service:

```bash
lectra disable
```

Defaults:

- data: `~/.local/share/lectra`
- device: `cuda`
- local service: `http://127.0.0.1:8000`

`LECTRA_DATA_DIR`, `LECTRA_DEVICE`, and `LECTRA_VOICE_SERVICE_URL` can override those defaults before configuration/startup.

## Development and tests

When testing inside a virtual environment, invoke both pip and pytest through that environment's Python. This avoids accidentally using a Conda/base `pytest` executable when both environments are active.

```bash
python -m pip install -e '.[chatterbox,telegram,dev]'
python -m pytest -q
```

To confirm the active interpreter when troubleshooting:

```bash
which python
python -c 'import sys; print(sys.executable)'
python -c 'import soundfile; print(soundfile.__file__)'
```

## Manual foreground mode for debugging only

Normal users should use `lectra start`. The foreground worker is retained for debugging and for the systemd unit itself:

```bash
lectra foreground
```

The HTTP service and Telegram bot can also still be started separately when debugging a specific component.

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
