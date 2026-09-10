---
name: lectra-presentations
description: Create or revise complete presentations from user-provided source material such as PDF, DOCX, PPTX, Markdown, CSV, TSV, XLSX, figures, journal articles, manuscripts, reports, teaching materials, proposals, and datasets. Use when the user wants Lectra to analyze presentation material, determine the necessary audience/purpose/duration constraints, propose a presentation plan, generate an editable PPTX, create a slide-by-slide human presenter script in Markdown, and create a separate machine-facing narration Markdown file for local voice synthesis. Also use when revising any of these synchronized presentation outputs.
---

# Lectra Presentations

Create presentations as a coordinated authoring workflow. Keep presentation reasoning inside the current ChatGPT or Claude session. Treat the local voice service as a downstream renderer that receives only `presentation-narration.md`.

## 1. Inspect the source material

Read all user-provided material needed for the task before designing slides. Identify the material type, main message, important quantitative results, usable figures/tables, conflicts or duplication across sources, and any analysis required before presentation authoring.

Never invent results, citations, figures, or source claims. Keep scientific and quantitative statements grounded in the supplied material unless the user explicitly requests external research.

## 2. Resolve presentation constraints

Infer constraints already supplied by the user or source context. Ask only questions whose answers could materially change the presentation. Typical high-value constraints are audience, purpose, duration, required format/template, emphasis, and whether backup slides are needed.

Do not ask the user to repeat information already available. If the user explicitly asks to proceed without discussion, make reasonable assumptions and state them briefly.

## 3. Plan before rendering

Before generating files, normally propose a concise presentation plan containing:

- audience and purpose;
- target duration;
- narrative arc;
- proposed slide count;
- slide-by-slide purpose;
- planned use of supplied figures/tables/data;
- major omissions or uncertainties that could affect the talk.

Wait for approval or revision unless the user already instructed you to generate immediately.

Read `references/workflow.md` for the detailed authoring sequence.

## 4. Generate the synchronized bundle

Create all three files unless the user explicitly requests a subset:

1. `presentation.pptx`
2. `presentation-script.md`
3. `presentation-narration.md`

Use the platform's available PPTX creation capability to create a real editable `.pptx`. Do not substitute a PDF, image deck, or Markdown slides.

Treat the three outputs as different surfaces:

- **PPTX**: what the audience sees.
- **Presenter script**: what helps the human presenter prepare and deliver the talk.
- **Narration file**: only the narrative and machine-readable speech controls needed by the local voice renderer.

Do not copy slide text verbatim into the spoken narrative unless that is genuinely the best presentation wording.

Read `references/output-contract.md` before producing the final bundle.

## 5. Write natural presenter speech

Write speech as someone explaining the presentation to an audience, not as someone reading a slide or audiobook. Use transitions, selective emphasis, references to visible material when useful, and appropriate pacing. Avoid narrating citations, axis labels, table cells, slide numbers, filenames, URLs, presenter notes, or metadata.

Match technical depth to the audience. Preserve exact numbers and scientific meaning.

## 6. Produce narration schema 1.0

Follow `references/narration-format.md` exactly for `presentation-narration.md`.

Use only the defined v1 controls unless the user explicitly requests an experimental extension. The narration file must remain independent of any specific TTS provider or model.

After creating the file, run:

```bash
python scripts/validate_narration.py presentation-narration.md
```

Fix validation errors before returning the presentation bundle.

## 7. Perform final synchronization QA

Verify all three outputs together. Confirm:

- slide order and topics match across PPTX, script, and narration;
- no narration remains for removed slides;
- important numbers agree with the source and slide;
- the narration fits the requested duration approximately;
- the narration contains no metadata intended to be spoken accidentally;
- scientific claims remain grounded in the supplied material.

Read `references/quality-control.md` for the final checks.
