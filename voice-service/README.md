# Lectra Voice Service

Local narration parsing and speech synthesis for Lectra.

The service is independent of ChatGPT, Claude, and paid TTS APIs. It consumes the versioned `presentation-narration.md` format, removes non-spoken metadata deterministically, and supports interchangeable local TTS backends.

## Current capabilities

- parse and validate Lectra narration schema 1.0;
- CLI inspection with `lectra-voice parse`;
- local synthesis with Qwen3-TTS or Chatterbox when the corresponding optional dependency is installed;
- sequential WAV rendering with explicit silence insertion;
- MP3 conversion through local FFmpeg;
- FastAPI health and parse endpoints;
- lazy backend loading so the base service does not require PyTorch or model weights.

## Base development install

```bash
python -m pip install -e '.[dev]'
pytest
lectra-voice parse ../examples/example-narration.md
uvicorn lectra_voice.service:app --reload
```

## TTS environments

Do not install both model stacks into the same environment during the initial bake-off. Use separate environments:

```bash
pip install -e '.[qwen3]'
```

or:

```bash
pip install -e '.[chatterbox]'
```

See `../docs/tts-bakeoff.md` for the standardized test workflow.

## CLI

```bash
lectra-voice backends
lectra-voice parse ../examples/tts-bakeoff-narration.md
lectra-voice generate --help
```

The current adapters intentionally do not reinterpret narration. Only parsed speech segments are sent to the TTS backend. Metadata, headings, comments, slide numbers, lists, tables, and code blocks remain non-spoken.
