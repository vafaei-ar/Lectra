# Narration format 1.0

Generate `presentation-narration.md` according to the repository's Lectra narration schema.

## Required front matter

```yaml
---
lectra_schema: "1.0"
title: Presentation title
language: en-US
style: story-driven-academic-presentation
target_duration_minutes: 20
default_pace: normal
default_tone: explanatory
---
```

`lectra_schema` and `title` are required. Include `target_duration_minutes` whenever a duration is known. When the user does not specify a duration, use Lectra's default 20-minute talk slot and set `target_duration_minutes: 20`. Any provided duration must be a positive number.

The default `style` is `story-driven-academic-presentation`. It describes the authoring intent only; the narration contract remains independent of any specific TTS backend.

## Allowed directives

Use standalone comments only:

```markdown
<!-- slide: 1 -->
<!-- pause: short -->
<!-- pause: medium -->
<!-- pause: long -->
<!-- pace: slow -->
<!-- pace: normal -->
<!-- pace: fast -->
<!-- tone: explanatory -->
<!-- tone: serious -->
<!-- tone: enthusiastic -->
<!-- tone: reflective -->
```

Pace and tone persist until changed. Pause inserts silence. Slide sets the current slide. Slide directives must be strictly increasing because narration follows a linear presentation timeline. Gaps are allowed when some deck slides intentionally have no narration.

## Narrative rules

Write ordinary prose paragraphs as the only spoken material. Do not use Markdown headings, bullet lists, tables, code blocks, URLs, citation lists, presenter notes, or raw slide labels in narration output.

Unless the user requests another style, write the spoken narrative as an engaging academic story for a mixed audience of colleagues and students. Open with a meaningful hook or question, create a clear reason to care, reveal evidence progressively, use natural transitions and callbacks, and close by resolving the opening question or tension. Preserve exact scientific meaning and do not invent anecdotes or unsupported details.

For the default 20-minute talk slot, plan approximately 18-19 minutes of spoken content plus natural pauses/transitions so the final delivery does not overrun.

Do not include model-specific commands. The local service maps Lectra controls to the selected TTS backend.

## Example

```markdown
---
lectra_schema: "1.0"
title: Example
language: en-US
style: story-driven-academic-presentation
target_duration_minutes: 20
default_pace: normal
default_tone: explanatory
---

<!-- slide: 1 -->

Good afternoon everyone.

I want to start with a simple question: if a model looks excellent in the hospital where it was developed, how much should we trust it somewhere else?

<!-- pause: medium -->

That question matters because internal performance can look reassuring even when the model has learned something highly local.

<!-- tone: serious -->

So the real test is not whether the model can fit one system. It is whether the signal survives when the context changes.
```
