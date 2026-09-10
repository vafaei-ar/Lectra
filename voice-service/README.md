# Lectra Voice Service

Local narration parsing and speech-synthesis service for Lectra.

The service is intentionally independent of ChatGPT, Claude, and paid TTS APIs. It consumes the versioned `presentation-narration.md` format and will support interchangeable local TTS backends.

## Bootstrap API

Current endpoints:

- `GET /health`: service status and supported narration schema versions;
- `POST /v1/parse`: parse narration Markdown into explicit speech and pause segments.

The bootstrap release does **not** synthesize audio yet. TTS adapters are the next milestone.

## Development

```bash
python -m pip install -e '.[dev]'
pytest
uvicorn lectra_voice.service:app --reload
```
