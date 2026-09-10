# Lectra

Lectra turns source material into an editable presentation, a presenter script, and a clean narration file, then converts that narration to presentation-style speech using a local voice-cloning service.

Lectra is designed around two independent components joined by one versioned file contract:

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

Lectra is in bootstrap development. Version 0.1 focuses on:

- narration schema 1.0;
- deterministic narration parsing;
- Skill workflow and output contracts;
- a local FastAPI service skeleton;
- tests that prevent metadata from leaking into speech.

See `docs/architecture.md` and `docs/roadmap.md`.
