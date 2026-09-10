# Lectra narration schema 1.0

`presentation-narration.md` is a machine-facing Markdown document. It is not the human presenter script.

The primary safety rule is simple: **only ordinary prose paragraphs are spoken**. Everything else is control information and must be removed before TTS.

## Front matter

Every narration file starts with YAML front matter.

```yaml
---
lectra_schema: "1.0"
title: Example presentation
language: en-US
target_duration_minutes: 20
style: academic-presentation
default_pace: normal
default_tone: explanatory
---
```

Required fields:

- `lectra_schema`: exactly `"1.0"` for this version;
- `title`: non-empty presentation title.

Optional fields:

- `language`: BCP-47-style language/locale string;
- `target_duration_minutes`: positive number;
- `style`: free text describing the intended presentation context;
- `default_pace`: `slow`, `normal`, or `fast`;
- `default_tone`: `explanatory`, `serious`, `enthusiastic`, or `reflective`.

## Directives

Directives are standalone HTML comments. They are never spoken.

### Slide boundary

```markdown
<!-- slide: 3 -->
```

Changes the active slide for subsequent speech. Slide numbers must be positive integers and should increase monotonically.

### Pause

```markdown
<!-- pause: short -->
<!-- pause: medium -->
<!-- pause: long -->
```

The reference parser maps these to 300, 700, and 1200 milliseconds. TTS adapters may implement pauses directly or the audio assembler may insert silence.

### Pace

```markdown
<!-- pace: slow -->
<!-- pace: normal -->
<!-- pace: fast -->
```

Changes the desired pace for subsequent spoken paragraphs until another pace directive appears.

### Tone

```markdown
<!-- tone: explanatory -->
<!-- tone: serious -->
<!-- tone: enthusiastic -->
<!-- tone: reflective -->
```

Changes the desired tone for subsequent spoken paragraphs until another tone directive appears.

## Spoken content

Ordinary Markdown paragraphs are spoken exactly as narrative content. The Skill should write them as natural presentation speech, not as slide text read aloud.

The Skill should avoid URLs, raw citations, presenter instructions, headings, bullet lists, tables, code blocks, and phrases such as `Slide 3` unless the presenter genuinely intends to say them.

## Never-spoken constructs

The parser treats the following as non-spoken:

- YAML front matter;
- all HTML comments, including unknown comments;
- Markdown headings;
- fenced code blocks;
- Markdown tables;
- list items;
- thematic separators.

Unknown HTML comments generate parser warnings but remain non-spoken.

## State semantics

`slide`, `pace`, and `tone` update parser state. `pause` inserts a pause segment. Pace and tone persist until changed. A slide boundary does not reset pace or tone.

## Compatibility

Schema 1.x should remain backward compatible. New incompatible syntax requires schema 2.0.
