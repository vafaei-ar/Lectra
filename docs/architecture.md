# Lectra architecture

## System boundary

Lectra intentionally separates presentation reasoning from speech synthesis.

### Authoring component

The Lectra presentation Skill runs inside a user's ChatGPT or Claude environment. It receives source files such as journal articles, manuscript drafts, educational content, DOCX, PDF, CSV, TSV, XLSX, Markdown, existing PPTX, and figures. The model performs the reasoning required to understand the material and design the presentation.

The authoring component produces three synchronized files:

- `presentation.pptx`: editable visual presentation;
- `presentation-script.md`: human-facing slide-by-slide presenter script and notes;
- `presentation-narration.md`: machine-facing narration contract for voice synthesis.

### Voice component

The Lectra Voice Service runs locally. It must not reinterpret the source documents or rewrite the presentation. It:

1. validates and parses `presentation-narration.md`;
2. removes all non-spoken metadata deterministically;
3. converts Lectra directives into neutral speech controls;
4. sends only spoken text and translated controls to a local TTS adapter;
5. assembles generated audio into the final presentation audio;
6. exposes the workflow to a Telegram bot.

## Dependency direction

```text
presentation Skill
       |
       v
presentation-narration.md (schema 1.x)
       |
       v
narration parser
       |
       v
abstract TTS adapter
   /      |      \
Qwen   Chatterbox  CosyVoice
       |
       v
     audio
```

The Skill must never depend on a specific TTS model. The voice service must never depend on ChatGPT or Claude APIs.

## Repository layout

```text
Lectra/
├── docs/
├── schemas/
├── examples/
├── skills/
│   └── lectra-presentations/
└── voice-service/
```

## Versioning

The components have independent versions:

- repository/product version;
- presentation Skill version;
- narration schema version;
- voice service version.

A narration file declares `lectra_schema: "1.0"`. The voice service must reject unsupported major schema versions rather than guess how to parse them.

## Privacy model

Voice samples and synthesized audio are local service data. They must not be committed to Git. A future Telegram integration will map Telegram numeric user IDs to local voice profiles. Voice enrollment must require explicit confirmation that the user owns the voice or has permission to use it.
