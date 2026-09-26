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

When the user does not specify otherwise, use these defaults without asking:

- **Format/context:** a 20-minute academic talk slot.
- **Audience:** a mixed academic audience of the user's colleagues and students.
- **Timing target:** aim for about 18-19 minutes of spoken content plus natural pauses/transitions so the 20-minute slot is not overrun.
- **Narrative style:** strongly story-driven, engaging, and presentation-like while remaining scientifically precise.

User-supplied constraints always override these defaults. If the source context clearly makes a default inappropriate, infer a better choice or ask only the minimum necessary question.

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

Default to a story-shaped arc rather than a source-summary arc. Open with a concrete hook, question, tension, or surprising observation; establish why it matters; reveal the approach and evidence progressively; interpret what changed in our understanding; and end with a clear resolution or take-home message. Use transitions and callbacks so slides feel connected rather than independent.

Do not invent personal anecdotes, patient stories, quotations, drama, or facts merely to make the talk more entertaining. Engagement must come from structure, pacing, contrast, questions, evidence, and explanation.

Wait for approval or revision unless the user already instructed you to generate immediately.

Read `references/workflow.md` for the detailed authoring sequence when that bundled file is available.

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

Read `references/output-contract.md` before producing the final bundle when that bundled file is available.

## 5. Write natural presenter speech

Write speech as someone explaining the presentation to an audience, not as someone reading a slide or audiobook. Use transitions, selective emphasis, references to visible material when useful, and appropriate pacing. Avoid narrating citations, axis labels, table cells, slide numbers, filenames, URLs, presenter notes, or metadata.

Default to an engaging scientific storytelling voice for the mixed colleagues-and-students audience. Keep the language accessible enough that students can follow the logic, but retain enough methodological and quantitative depth to satisfy colleagues. Use questions, contrast, anticipation, callbacks, and concise recaps to maintain attention. Let each section answer a question raised earlier and naturally set up the next one.

Preserve exact numbers, uncertainty, limitations, and scientific meaning. Never simplify in a way that changes the claim.

## 6. Produce narration schema 1.0

Follow `references/narration-format.md` when that bundled file is available.

Use only the defined v1 controls unless the user explicitly requests an experimental extension. The narration file must remain independent of any specific TTS provider or model.

After creating the file, use the bundled `scripts/validate_narration.py` with `python3` **only if the host exposes the Skill files in the current session**. Never guess or hard-code a Skill mount path. Use the actual Skill path supplied by the host or discovered from the current session's Skill/file tools. Do not `cd` into a read-only Skill directory.

If the bundled validator is not accessible, do not treat that as a presentation failure and do not invent a path. Perform the equivalent validation directly with the host's available tools using the fallback rules below, and state in the final QA note that the bundled validator was unavailable in that session.

Minimum narration fallback contract:

```markdown
---
lectra_schema: "1.0"
title: Presentation title
language: en-US
style: story-driven-academic-presentation
target_duration_minutes: 20
default_pace: normal
default_tone: explanatory
---

<!-- slide: 1 -->

Natural spoken prose.
```

When the user supplies a different duration or presentation style, use that instead of the fallback values.

Allowed v1 directives are `slide`, `pause` (`short|medium|long`), `pace` (`slow|normal|fast`), and `tone` (`explanatory|serious|enthusiastic|reflective`). Only ordinary prose is spoken. YAML front matter, comments/directives, headings, lists, tables, code blocks, URLs, and presenter-only metadata must not become speech. Slide directives must be positive and strictly increasing; gaps are allowed.

Fix validation errors before returning the presentation bundle. Review timing and warnings when available.

## 7. Perform final synchronization QA

After the PPTX, presenter script, and narration all exist, use `scripts/validate_bundle.py` with `python3` when the host exposes the bundled Skill files. Again, resolve the actual Skill path from the host; never assume one.

If the script is unavailable, perform the structural checks directly: compare PPTX slide count with slide numbers in the presenter script and narration, reject references to nonexistent slides, reject duplicate/backward narration slide markers, and confirm every narrated slide has a corresponding presenter-script section. Then verify all three outputs together. Confirm:

- slide order and topics match across PPTX, script, and narration;
- no narration remains for removed slides;
- important numbers agree with the source and slide;
- the narration fits the requested duration approximately;
- when defaults apply, the complete talk fits the 20-minute slot without feeling rushed or padded;
- the narration contains no metadata intended to be spoken accidentally;
- the talk has a clear hook, progression, transitions, callbacks, and ending rather than reading like a sequence of source sections;
- scientific claims remain grounded in the supplied material.

Read `references/quality-control.md` for the final checks when that bundled file is available.
