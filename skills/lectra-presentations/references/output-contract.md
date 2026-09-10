# Lectra output contract

## Required files

Unless the user requests otherwise, return:

- `presentation.pptx`
- `presentation-script.md`
- `presentation-narration.md`

## PPTX

The PPTX is audience-facing. Keep it editable. Use an appropriate visual hierarchy, readable typography, and figures/tables that support the slide's purpose. Avoid paragraphs of script text on slides.

## Human presenter script

Use one section per slide. A useful default structure is:

```markdown
# Slide 7: External Validation

**Purpose:** Establish generalizability.

**Target duration:** 55 seconds

## Script

Natural spoken script...

## Presenter notes

- Human-only delivery or visual notes.

## Transition

Short transition into the next slide.

## Sources

Pointers to supplied source material when useful.
```

This file may contain metadata, citations, timing, reminders, and non-spoken presenter notes.

## Machine narration

`presentation-narration.md` is not a shortened copy of the presenter script. It is the exact synthetic-presenter narrative plus Lectra speech-control metadata.

Do not include sources, citations for visual reference, speaker reminders, slide titles, URLs, or other content that should not be spoken.

## Synchronization

The script and narration may differ in metadata but must communicate the same substantive presentation. Every narration section must correspond to the correct slide in the final PPTX.
