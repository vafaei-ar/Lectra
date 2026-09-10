# Lectra roadmap

## Milestone 0: foundation

- Freeze narration schema 1.0.
- Create presentation Skill scaffold and output contracts.
- Build deterministic narration parser.
- Add local service health and parse endpoints.
- Test that metadata never leaks into speech.

## Milestone 1: local TTS bake-off

Implement a common adapter interface and benchmark at least:

- Qwen3-TTS;
- Chatterbox;
- CosyVoice.

Use the same voice sample and 3-5 minute academic narration. Prioritize speaker similarity, presentation-like prosody, text fidelity, medical terminology, long-form stability, and controllability over real-time speed.

## Milestone 2: CLI synthesis

Add a local command that accepts `presentation-narration.md`, a voice profile, and an output path. Support chunk generation, silence insertion, audio normalization, concatenation, and caching.

## Milestone 3: voice profiles

Add local enrollment, listing, selection, and deletion of voice profiles. Keep voice samples outside Git and require voice ownership/permission confirmation.

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
- per-slide regeneration;
- content-addressed audio caching;
- additional local TTS adapters;
- optional local network deployment to a separate GPU workstation.
