# Lectra quality control

Perform these checks before returning a completed bundle.

## Source fidelity

Confirm that quantitative values, study populations, methods, and conclusions match the supplied sources. Distinguish source findings from interpretation.

## Narrative quality

Confirm that the presentation has a clear purpose and progression. Remove slides that merely repeat source sections without advancing the presentation.

When the user has not specified a different style, confirm the talk follows Lectra's default story-driven academic mode:

- the opening creates curiosity through a real question, tension, observation, consequence, or surprising evidence;
- the audience understands why the topic matters before receiving too much detail;
- evidence is revealed in an order that builds understanding;
- transitions explain why the next slide follows from the previous one;
- callbacks reconnect later findings to earlier questions;
- the ending resolves the opening question or tension and leaves a clear take-home message;
- no fictional anecdotes, quotations, patient stories, or unsupported dramatic details were invented for engagement.

For the default mixed audience of colleagues and students, confirm that students can follow the conceptual logic and terminology while colleagues still receive appropriate methodological detail, numbers, caveats, and limitations.

## Visual/script separation

Confirm that slides summarize and visualize while the script explains. Avoid using the same full sentences in both surfaces without a reason.

## Synchronization

When the host exposes bundled Skill files, run `scripts/validate_bundle.py` with `python3` using the actual Skill path supplied or discoverable in that session. Never guess a mount path. If the script is unavailable, perform the same structural checks directly with the host's available tools. This does not replace semantic review.

For every final slide:

- confirm a corresponding script section exists when narration is expected;
- confirm narration is associated with the correct slide;
- remove script/narration for deleted slides;
- confirm transitions refer to what actually comes next.

Narration slide directives intentionally move forward only because the narration is a linear presentation timeline. Gaps are allowed so silent title, transition, appendix, or backup slides can remain in the deck.

## Narration hygiene

When the host exposes bundled Skill files, run `scripts/validate_narration.py` with `python3` using the actual Skill path supplied or discoverable in that session. Never guess a mount path. If the script is unavailable, apply the narration schema and hygiene checks directly. Treat detected validation errors as blocking. Review warnings manually. In particular, remove accidental URLs, Markdown structures, and literal slide-number language that is not intended to be spoken.

## Timing

Estimate spoken duration from word count and presentation context. Do not pad content solely to hit a target duration. Prefer approximately 120-150 spoken words per minute for ordinary English academic presentation planning unless user-specific pacing is known. When `target_duration_minutes` is provided, confirm it is a positive number and compare it with the estimated duration and planned pauses.

When no duration is supplied, use the Lectra default of a **20-minute talk slot**. Plan roughly **18-19 minutes of spoken content plus natural pauses/transitions**, rather than filling every second of the slot. If the user explicitly asks for 20 full minutes of narration, follow that instead.

## Final artifact check

Verify the actual generated files exist, open correctly, and use the requested filenames. Return all requested artifacts together.
