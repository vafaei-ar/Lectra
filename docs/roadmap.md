# Lectra roadmap

## Milestone 0: foundation - complete

- Freeze narration schema 1.0.
- Create presentation Skill scaffold and output contracts.
- Build deterministic narration parser.
- Add local service health and parse endpoints.
- Test that metadata never leaks into speech.

## Milestone 1: local TTS CLI and bake-off - complete

- Implement Qwen3-TTS Base and Chatterbox adapters.
- Add CLI parsing, dry-run, generation, WAV rendering, pauses, and MP3 conversion.
- Run both models with the same real voice reference and narration.
- Select Chatterbox as the default because it was substantially more stable across presentation segments.
- Keep Qwen3-TTS as an optional backend because its individual-sentence speaker match was strong but identity drift remained noticeable.

## Milestone 2: voice profiles and Telegram MVP - in progress

- Store voice profiles locally by numeric Telegram user ID.
- Require voice ownership/permission confirmation.
- Normalize Telegram voice/audio samples to local 24 kHz mono WAV.
- Support enrollment, listing, default selection, and deletion.
- Accept and validate `presentation-narration.md` uploads.
- Send generation jobs to the local FastAPI service.
- Return generated MP3 through Telegram.
- Use polling so no public webhook is required.

## Milestone 3: rendering reliability

- Honor pace directives without changing speaker pitch.
- Add content-addressed chunk caching.
- Add per-slide and per-segment regeneration.
- Persist generation manifests and backend settings.
- Add optional loudness normalization.
- Add automatic retry for failed segments.

## Milestone 4: speech QA

- Add local ASR verification of generated speech.
- Flag mismatches in numbers, percentages, names, abbreviations, and clinical terminology.
- Add pronunciation overrides.

## Milestone 5: end-to-end presentation workflow

Test three distinct use cases:

1. scientific article to 15-minute conference talk;
2. educational content to 45-minute lecture;
3. CSV plus report to results presentation.

Validate source grounding, PPTX/script/narration synchronization, timing, and final audio quality.
