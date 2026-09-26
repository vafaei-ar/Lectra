# Lectra presentation workflow

## A. Source inspection

Classify the input. Adjust the workflow to the material rather than forcing every task into a manuscript template.

- Journal article/manuscript: identify question, design, methods needed to interpret results, key findings, limitations, and discussion message.
- Teaching material: identify learning objectives, prerequisite knowledge, conceptual sequence, worked examples, and recap points.
- Proposal/grant: identify significance, gap, hypothesis, aims, approach, feasibility, and expected impact.
- Dataset/spreadsheet: determine what analysis is required before any result is presented. Do not manufacture analyses or charts.
- Mixed documents: establish which sources are authoritative and resolve contradictions before presentation generation.
- Existing PPTX: determine whether the user wants revision, redesign, shortening, expansion, or narration while preserving an existing structure.

## B. Constraint resolution

Prefer inference over unnecessary questions. Ask when a missing answer would materially alter structure or depth.

High-value constraints:

- audience;
- presentation purpose;
- duration;
- venue/context;
- required template or branding;
- specific findings or sections to emphasize/de-emphasize;
- backup slides.

When these are not specified, default to:

- a 20-minute academic talk slot;
- a mixed audience of the user's colleagues and students;
- roughly 18-19 minutes of planned spoken content plus pauses/transitions;
- an engaging, story-driven scientific presentation rather than a source-by-source summary.

Explicit user instructions always override these defaults.

## C. Story construction

Construct the story before slide layout. Each slide should have one main communicative purpose and should either answer a question already raised, sharpen the central tension, provide evidence, change the interpretation, or set up what comes next.

Default narrative shape:

1. **Hook:** open with a concrete question, observation, tension, surprising result, or consequence that gives the audience a reason to care.
2. **Why it matters:** establish the real scientific, clinical, technical, or educational stakes.
3. **What we did / how to think about it:** introduce only the methods or concepts needed to follow the evidence.
4. **Progressive evidence:** reveal findings or examples in a sequence that builds understanding rather than dumping results all at once.
5. **Interpretation:** explain what the evidence changes, what it does not prove, and why the audience should update its view.
6. **Resolution:** return to the opening question or tension and land a memorable take-home message.

Use callbacks to earlier slides, contrast, anticipation, and concise recaps. Prefer causal/logical transitions such as "That raises the next question..." or "If that is true, we should see..." over mechanical transitions such as "Next, I will show...".

For research talks, problem/gap -> question -> approach -> evidence -> interpretation -> implications remains a useful backbone, but make it feel like discovery rather than a manuscript recitation.

For teaching, prioritize concept dependencies, intuition, examples, and payoff. Create curiosity before giving the answer when appropriate.

Never invent anecdotes, patient stories, quotations, or dramatic details. Storytelling means structuring truthful material for attention and understanding, not fictionalizing it.

## D. Slide planning

For each proposed slide, record:

- working title;
- communicative purpose;
- audience question being answered or raised;
- evidence or visual needed;
- approximate speaking time;
- relationship to the previous and next slide.

Do not create slides only to mirror source section headings. Prefer titles that state the point or question of the slide rather than generic labels such as "Methods" or "Results" when the content supports a more informative title.

For the default 20-minute slot, keep the slide count subordinate to the story and timing. Do not inflate the deck to hit an arbitrary slide count.

## E. Rendering

Generate the PPTX first or in parallel with the script as supported by the environment, but do not finalize narration until slide structure is stable.

Reuse user-supplied figures when appropriate. Create new charts from actual supplied data when needed. Do not fabricate illustrative quantitative charts that could be mistaken for results.

## F. Script and narration

Create the human presenter script with slide headings, purpose, timing, spoken script, presenter notes, transitions, and source pointers when useful.

Create the narration file separately from the presenter script. Strip all human-only notes and source metadata. Keep only natural spoken paragraphs plus Lectra schema directives.

For the default mixed colleagues-and-students audience, explain enough context and terminology for students to stay oriented while retaining the methodological precision, caveats, and quantitative detail colleagues need. Use natural spoken language, varied sentence length, strategic pauses, and explicit transitions to maintain attention.

## G. QA

Review the three outputs as one synchronized presentation before delivery. Confirm that the talk is not only correct but also engaging: the opening creates interest, each section advances the story, transitions are meaningful, and the ending resolves the opening question or tension.
