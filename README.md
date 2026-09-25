# Lectra

Lectra turns source material into an editable presentation, a presenter script, and a clean narration file, then converts that narration to presentation-style speech using a local voice-cloning service.

Lectra has two independent components joined by one versioned file contract:

1. **Lectra Presentations Skill**: runs inside ChatGPT or Claude. It inspects user-provided material, asks only necessary questions, proposes a presentation plan, and generates `presentation.pptx`, `presentation-script.md`, and `presentation-narration.md`.
2. **Lectra Voice Service**: runs locally on a laptop or GPU workstation. It parses `presentation-narration.md`, manages local voice profiles, synthesizes speech with Chatterbox by default, and exposes the workflow through a Telegram bot.

No paid LLM or TTS API is required. ChatGPT/Claude subscriptions handle authoring; voice synthesis is local.

## Core design rule

`presentation-narration.md` is the contract between the authoring Skill and the local voice system. Metadata must never be sent to TTS as speech.

```text
source files
    |
    v
ChatGPT / Claude + Lectra Skill
    |
    +--> presentation.pptx
    +--> presentation-script.md
    +--> presentation-narration.md
                              |
                              v
                       Lectra Voice Service
                              |
                              +--> local voice profile
                              +--> Chatterbox TTS
                              |
                              v
                         Telegram bot
                              |
                              v
                       presentation.mp3
```

## Current status

- Narration schema 1.0 and deterministic parser: complete.
- Presentation Skill scaffold: complete.
- Local Qwen3-TTS/Chatterbox bake-off: complete.
- Default TTS: **Chatterbox**, selected for substantially better voice stability across presentation segments.
- Local voice profiles + Telegram MVP: in development on `telegram-voice-profiles-v0.3`.

See:

- `docs/architecture.md`
- `docs/narration-schema.md`
- `docs/tts-bakeoff.md`
- `docs/telegram-bot.md`
- `docs/roadmap.md`
