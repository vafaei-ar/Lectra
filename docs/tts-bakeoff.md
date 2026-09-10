# Local TTS bake-off

Lectra's first voice milestone compares local voice-cloning backends using the same reference recording and narration. The goal is not real-time speed. The goal is speaker similarity, presentation-like delivery, text fidelity, medical pronunciation, and long-form stability.

## Why the reference script is fixed

Qwen3-TTS Base produces its strongest voice-cloning path from reference audio plus the matching transcript. Lectra therefore provides `examples/reference-voice-script.txt`. Record that script verbatim in a quiet room using a natural presentation voice. The same WAV file can then be used by both Qwen3-TTS and Chatterbox, while Qwen receives the already-known transcript.

Do not commit personal voice recordings to Git.

## Test material

- Reference transcript: `examples/reference-voice-script.txt`
- Standardized narration: `examples/tts-bakeoff-narration.md`

The narration intentionally includes numbers, abbreviations, clinical terminology, slide boundaries, pauses, and tone changes.

## Base installation

Use Python 3.11 or 3.12. Install Lectra's base voice service first:

```bash
cd voice-service
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e '.[dev]'
lectra-voice parse ../examples/tts-bakeoff-narration.md
```

The base installation does not install a TTS model.

## Qwen3-TTS environment

Use a dedicated environment because speech packages may pin different PyTorch stacks.

```bash
cd voice-service
python -m venv .venv-qwen
source .venv-qwen/bin/activate
python -m pip install -U pip
pip install -e '.[qwen3]'
```

Generate WAV:

```bash
lectra-voice generate ../examples/tts-bakeoff-narration.md \
  --backend qwen3 \
  --reference-audio /path/to/reference.wav \
  --reference-text-file ../examples/reference-voice-script.txt \
  --output qwen3.wav
```

The default is `Qwen/Qwen3-TTS-12Hz-1.7B-Base`. Use `--qwen-model Qwen/Qwen3-TTS-12Hz-0.6B-Base` if memory is limited. `--qwen-flash-attention` is optional and should only be used after FlashAttention 2 is installed correctly.

If a matching transcript is unavailable, `--qwen-x-vector-only` explicitly enables speaker-embedding-only cloning without a reference transcript. This is a fallback, not the preferred benchmark path.

## Chatterbox environment

Create a separate environment:

```bash
cd voice-service
python -m venv .venv-chatterbox
source .venv-chatterbox/bin/activate
python -m pip install -U pip
pip install -e '.[chatterbox]'
```

Generate WAV:

```bash
lectra-voice generate ../examples/tts-bakeoff-narration.md \
  --backend chatterbox \
  --reference-audio /path/to/reference.wav \
  --output chatterbox.wav
```

The initial adapter uses the original English Chatterbox model rather than Turbo because the original model exposes CFG and exaggeration controls. Lectra maps its tone directives conservatively to those controls. Pace directives are preserved in the parsed representation but are not yet modified by either backend.

## MP3

If `ffmpeg` is available on PATH, use an `.mp3` output path directly. Lectra renders a temporary WAV locally and converts it with FFmpeg.

## Dry run

Validate the full request without loading model weights:

```bash
lectra-voice generate ../examples/tts-bakeoff-narration.md \
  --backend qwen3 \
  --reference-audio /path/to/reference.wav \
  --reference-text-file ../examples/reference-voice-script.txt \
  --output qwen3.wav \
  --dry-run
```

## Initial scoring

Score each output from 1 to 5 for:

1. speaker similarity;
2. presentation-like prosody;
3. text fidelity;
4. medical terminology and numbers;
5. stability across the full narration;
6. natural pauses and transitions;
7. installation/runtime practicality.

Do not select the default backend from documentation claims alone. Select it after listening to the same narration generated from the same voice sample.
