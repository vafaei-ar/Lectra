# Lectra quality control

Perform these checks before returning a completed bundle.

## Source fidelity

Confirm that quantitative values, study populations, methods, and conclusions match the supplied sources. Distinguish source findings from interpretation.

## Narrative quality

Confirm that the presentation has a clear purpose and progression. Remove slides that merely repeat source sections without advancing the presentation.

## Visual/script separation

Confirm that slides summarize and visualize while the script explains. Avoid using the same full sentences in both surfaces without a reason.

## Synchronization

For every final slide:

- confirm a corresponding script section exists when narration is expected;
- confirm narration is associated with the correct slide;
- remove script/narration for deleted slides;
- confirm transitions refer to what actually comes next.

## Narration hygiene

Run `scripts/validate_narration.py`. Treat validation errors as blocking. Review warnings manually. In particular, remove accidental URLs, Markdown structures, and literal slide-number language that is not intended to be spoken.

## Timing

Estimate spoken duration from word count and presentation context. Do not pad content solely to hit a target duration. Prefer approximately 120-150 spoken words per minute for ordinary English academic presentation planning unless user-specific pacing is known.

## Final artifact check

Verify the actual generated files exist, open correctly, and use the requested filenames. Return all requested artifacts together.
