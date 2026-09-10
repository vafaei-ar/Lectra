# Narration format 1.0

Generate `presentation-narration.md` according to the repository's Lectra narration schema.

## Required front matter

```yaml
---
lectra_schema: "1.0"
title: Presentation title
language: en-US
style: academic-presentation
default_pace: normal
default_tone: explanatory
---
```

`lectra_schema` and `title` are required. Include `target_duration_minutes` when known; when provided it must be a positive number.

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

Do not include model-specific commands. The local service maps Lectra controls to the selected TTS backend.

## Example

```markdown
---
lectra_schema: "1.0"
title: Example
language: en-US
style: scientific-presentation
default_pace: normal
default_tone: explanatory
---

<!-- slide: 1 -->

Good afternoon everyone.

Today I want to focus on one question: does this model generalize beyond the system where it was developed?

<!-- pause: medium -->
<!-- tone: serious -->

This matters because internal performance alone cannot answer that question.
```
