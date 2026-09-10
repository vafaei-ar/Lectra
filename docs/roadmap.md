# Lectra roadmap

## Milestone 0: foundation - complete

- Freeze narration schema 1.0.
- Create presentation Skill scaffold and output contracts.
- Build deterministic narration parser.
- Add local service health and parse endpoints.
- Test that metadata never leaks into speech.

## Milestone 1: local TTS CLI and bake-off - in progress

- Add a common local TTS adapter interface.
- Implement Qwen3-TTS Base voice cloning.
- Implement Chatterbox voice cloning.
- Add CLI parse, backend inspection, dry-run, and generation commands.
- Render sequential WAV without holding an entire talk in memory.
- Insert explicit pause directives as silence.
- Convert final WAV to MP3 through local FFmpeg.
- Use the same reference script and 3-minute academic narration for both models.
- Run both models on a GPU machine and score speaker similarity, presentation-like prosody, text fidelity, medical terminology, long-form stability, and controllability.

CosyVoice remains a possible third comparator if Qwen3-TTS and Chatterbox do not produce a clear winner.

## Milestone 2: rendering reliability

- Honor pace directives without changing speaker pitch.
- Add content-addressed chunk caching.
- Add per-slide and per-segment regeneration.
- Persist generation manifests and backend settings.
- Add optional loudness normalization.

## Milestone 3: voice profiles

Add local enrollment, listing, selection, and deletion of voice profiles. Keep voice samples outside Git and require voice ownership/permission confirmation. Prefer a fixed Lectra presentation-style reference script so the matching transcript is already available to backends that need it.

## Milestone 4: Telegram bot

Add Telegram handlers for setup, voice enrollment, narration upload, generation, settings, and audio delivery. Use Telegram numeric user IDs for local profile isolation.

## Milestone 5: end-to-end presentation workflow

Test three distinct use cases:

1. scientific article to 15-minute conference talk;
2. educational content to 45-minute lecture;
3. CSV plus report to results presentation.

Validate source grounding, PPTX/script/narration synchronization, timing, and final audio quality.

## Later reliability work

- ASR-based verification of generated speech;
- pronunciation overrides for names and medical terminology;
- additional local TTS adapters;
- optional local network deployment to a separate GPU workstation.
