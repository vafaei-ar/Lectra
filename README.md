# Lectra

Lectra turns source material into an editable presentation, a presenter script, and a clean narration file, then converts that narration to presentation-style speech using a local voice-cloning service.

Lectra has two independent components joined by one versioned file contract:

1. **Lectra Presentations Skill**: runs inside ChatGPT or Claude. It inspects user-provided material, asks only necessary questions, proposes a presentation plan, and generates `presentation.pptx`, `presentation-script.md`, and `presentation-narration.md`.
2. **Lectra Voice Service**: runs locally on a laptop or GPU workstation. It parses `presentation-narration.md`, applies presentation controls, synthesizes speech with a local TTS backend, and later exposes that capability through a Telegram bot.

No paid LLM or TTS API is required. ChatGPT/Claude subscriptions handle authoring; voice synthesis is local.

## Core design rule

`presentation-narration.md` is the only contract between the authoring Skill and the local voice system. Metadata must never be sent to TTS as speech.

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
                              v
                       presentation.mp3
```

## Current status

Milestone 0 is complete. The repository now contains narration schema 1.0, the presentation Skill scaffold, deterministic narration parsing, and metadata-leak tests.

Milestone 1 is in progress. The local voice service now has a CLI and optional Qwen3-TTS and Chatterbox adapters for a controlled local bake-off. The actual acoustic comparison must run on a machine with the model weights, GPU/CPU runtime, and a real reference voice recording.

See:

- `docs/architecture.md`
- `docs/narration-schema.md`
- `docs/tts-bakeoff.md`
- `docs/roadmap.md`
