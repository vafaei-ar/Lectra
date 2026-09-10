# Local TTS bake-off

Lectra's first voice milestone compared local voice-cloning backends using the same reference recording and narration. The goal was speaker similarity, presentation-like delivery, text fidelity, medical pronunciation, and long-form stability rather than real-time speed.

## Result

The initial real-voice bake-off selected **Chatterbox as Lectra's default backend**.

Observed behavior:

- **Qwen3-TTS 1.7B Base** matched the reference speaker more closely on individual sentences, but the perceived voice changed more from segment to segment.
- Enabling Qwen's non-streaming voice-clone mode improved the result, but did not remove the segment-to-segment voice drift enough for long-form presentation use.
- **Chatterbox** was slightly less exact as a voice clone, but remained substantially more stable across sentences and was acceptable in speaker similarity.

For Lectra's primary use case, stable identity across a 20-45 minute presentation is more important than maximizing similarity on an isolated sentence. Chatterbox is therefore the production default. Qwen3-TTS remains an optional experimental/fallback backend.

## Why the reference script is fixed

Lectra provides `examples/reference-voice-script.txt`. Record that script verbatim in a quiet room using a natural presentation voice. The recording is intentionally neutral and avoids domain-specific terminology. Do not commit personal voice recordings to Git.

Qwen3-TTS Base can use the matching transcript for its ICL cloning path. Chatterbox uses the same reference WAV directly.

## Test material

- Reference transcript: `examples/reference-voice-script.txt`
- Standardized narration: `examples/tts-bakeoff-narration.md`

## Base installation

```bash
cd voice-service
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e '.[dev]'
lectra-voice parse ../examples/tts-bakeoff-narration.md
```

## Chatterbox production environment

Use Chatterbox for the normal Lectra voice service:

```bash
cd voice-service
python -m venv .venv-chatterbox
source .venv-chatterbox/bin/activate
python -m pip install -U pip
pip install -e '.[chatterbox]'
```

Generate with the default backend:

```bash
lectra-voice generate ../examples/tts-bakeoff-narration.md \
  --reference-audio /path/to/reference.wav \
  --output chatterbox.wav
```

You can still specify `--backend chatterbox` explicitly.

## Qwen3-TTS optional environment

Keep Qwen in a separate environment when needed:

```bash
cd voice-service
python -m venv .venv-qwen
source .venv-qwen/bin/activate
python -m pip install -U pip
pip install -e '.[qwen3]'
```

Generate:

```bash
lectra-voice generate ../examples/tts-bakeoff-narration.md \
  --backend qwen3 \
  --reference-audio /path/to/reference.wav \
  --reference-text-file ../examples/reference-voice-script.txt \
  --output qwen3.wav
```

The Qwen adapter forces offline `non_streaming_mode=True` because simulated-streaming voice cloning showed rate drift during testing.

## MP3

If `ffmpeg` is available on PATH, use an `.mp3` output path directly. Lectra renders locally and converts the final output with FFmpeg.

## Decision criteria

The comparison prioritized:

1. stable speaker identity across a full presentation;
2. natural presentation prosody;
3. speaker similarity;
4. text and pronunciation fidelity;
5. runtime practicality.

Future model changes should be evaluated using the same reference recording and narration rather than documentation claims alone.
