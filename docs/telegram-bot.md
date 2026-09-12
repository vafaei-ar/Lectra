# Telegram bot MVP

Lectra's Telegram bot is the user-facing client for the local Lectra Voice Service. It uses Telegram long polling, so the Lectra machine does not need a public URL or webhook.

## Privacy boundary

Telegram transports the enrollment recording, narration file, ordinary text messages, and returned MP3. Lectra does not send the voice sample or narration to a separate cloud TTS/LLM service.

- Lectra's persistent voice-profile copy is stored under `LECTRA_DATA_DIR` on the local Lectra machine.
- Users are isolated by immutable numeric Telegram user ID.
- The bot requires explicit ownership/permission confirmation before saving a voice profile.
- `/deletevoice` removes Lectra's local voice-profile copy. It does not delete the original Telegram message containing the recording.
- Bot tokens are stored only in Lectra's private local configuration and are never committed to the repository.
- Routine `httpx` and `httpcore` INFO transport logs are suppressed because Telegram Bot API URLs contain the bot token.
- If a bot token appears in a terminal log, chat, screenshot, issue, or other shared material, revoke it with BotFather and reconfigure Lectra before continuing.
- The FastAPI service binds to `127.0.0.1` by default.

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

## Configure once

```bash
lectra configure
```

Paste the Telegram bot token into the hidden prompt. Lectra stores it in its local configuration with restrictive permissions.

Optional environment overrides can be set before configuration/startup:

```bash
export LECTRA_DATA_DIR="$HOME/.local/share/lectra"
export LECTRA_DEVICE='cuda'
export LECTRA_VOICE_SERVICE_URL='http://127.0.0.1:8000'
```

## Run as a background service

Normal operation uses a user-level systemd service. No sudo and no open terminal are required.

```bash
lectra start
lectra status
lectra restart
lectra stop
lectra logs
```

After `lectra start` reports success, the terminal may be closed. Lectra continues running.

Use:

```bash
lectra logs --follow
```

to watch live logs. `Ctrl+C` exits only the log viewer; it does not stop Lectra.

Optional autostart at user login:

```bash
lectra enable
```

Disable autostart without stopping an already-running service:

```bash
lectra disable
```

## User flows

### Presentation narration

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

### Plain-text read-aloud

Send any ordinary non-command text message. Lectra immediately synthesizes it with the default voice profile, shows chunk-level progress, and returns an MP3. Bot commands such as `/health` are not spoken. If `/setupvoice` is awaiting a recording, typed text is treated as part of setup and does not trigger TTS.

Useful commands:

- `/voices`
- `/defaultvoice <name>`
- `/deletevoice [name]`
- `/settings`
- `/health`

`/setupvoice <name>` can create more than one local voice profile.

## Reliable Telegram audio delivery

Presentation MP3s can be tens of megabytes, so Lectra does not rely on python-telegram-bot's ordinary media timeout defaults.

- Media uploads use a 600-second write timeout plus explicit read/connect/pool timeouts.
- A transient Telegram `NetworkError` or timeout triggers one automatic upload retry.
- The retry creates a fresh in-memory upload stream rather than reusing a partially consumed stream.
- If both upload attempts fail, Lectra keeps the completed local render job and shows **Retry upload** and **Dismiss** buttons.
- **Retry upload** fetches the already-generated MP3 from the local render job and retries only the Telegram transfer. Chatterbox is not run again.
- The cached render job is process-local in the current v0.3 implementation, so an upload-only retry must happen before the Lectra service is restarted. A service restart requires generation again.

This distinction is intentional: a Telegram transfer failure should not be reported as a TTS failure.

## API compatibility

The canonical progress API is `/v1/render/jobs`. During the v0.3 transition the service also accepts the earlier `/v1/jobs` paths used by the first Telegram progress build. Plain-text synthesis uses `/v1/text/jobs`. The service advertises progress and plain-text capabilities through `/health`, and the managed launcher checks service version/capability before use.

## Error handling

The bot registers a global error handler so unexpected Telegram-handler errors are reported to the user instead of only appearing in the terminal. Known generation errors are reported directly in the generation status message.

Transient Telegram polling `NetworkError` failures are logged as concise warnings because python-telegram-bot retries polling automatically. Audio-upload network errors follow the retry path described above.

Error text sent to Telegram is sanitized for bot-token-shaped secrets. Routine HTTP transport request logs are disabled at INFO level.

## Telegram limits used by the MVP

Lectra caps incoming enrollment audio at 20 MB and outgoing audio at 50 MB. Narration Markdown is limited to 2 MB, and ordinary Telegram text is limited by Telegram's message-size constraint.

Lectra encodes final speech MP3s as 96 kbps mono. At that bitrate a 45-minute presentation is roughly 32 MB, leaving useful headroom under the 50 MB output cap.
