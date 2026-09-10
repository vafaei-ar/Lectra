from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from .models import ParsedNarration, PauseSegment, SpeechSegment

DIRECTIVE_RE = re.compile(r"^\s*<!--\s*([a-zA-Z_]+)\s*:\s*(.*?)\s*-->\s*$")
LIST_RE = re.compile(r"^\s*(?:[-*+] |\d+[.)] )")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")

PAUSE_MS = {"short": 300, "medium": 700, "long": 1200}
PACES = {"slow", "normal", "fast"}
TONES = {"explanatory", "serious", "enthusiastic", "reflective"}


class NarrationParseError(ValueError):
    pass


@dataclass
class _State:
    slide: int | None
    pace: str
    tone: str


def _split_frontmatter(markdown: str) -> tuple[dict[str, object], str]:
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        raise NarrationParseError("Narration must start with YAML front matter.")

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise NarrationParseError("YAML front matter is not closed with '---'.")

    raw = "\n".join(lines[1:end])
    metadata = yaml.safe_load(raw) or {}
    if not isinstance(metadata, dict):
        raise NarrationParseError("YAML front matter must be a mapping.")
    if str(metadata.get("lectra_schema", "")) != "1.0":
        raise NarrationParseError("Unsupported or missing lectra_schema; expected '1.0'.")
    if not str(metadata.get("title", "")).strip():
        raise NarrationParseError("Narration front matter requires a non-empty title.")

    return metadata, "\n".join(lines[end + 1 :])


def _is_never_spoken_line(line: str, in_code: bool) -> bool:
    stripped = line.strip()
    if in_code or not stripped:
        return True
    if stripped.startswith("#"):
        return True
    if LIST_RE.match(line):
        return True
    if TABLE_SEPARATOR_RE.match(line):
        return True
    if stripped.count("|") >= 2:
        return True
    if stripped in {"---", "***", "___"}:
        return True
    return False


def parse_narration(markdown: str) -> ParsedNarration:
    metadata, body = _split_frontmatter(markdown)
    pace = str(metadata.get("default_pace", "normal"))
    tone = str(metadata.get("default_tone", "explanatory"))
    if pace not in PACES:
        raise NarrationParseError(f"Invalid default_pace: {pace}")
    if tone not in TONES:
        raise NarrationParseError(f"Invalid default_tone: {tone}")

    state = _State(slide=None, pace=pace, tone=tone)
    segments = []
    warnings: list[str] = []
    paragraph: list[str] = []
    in_code = False

    def flush_paragraph() -> None:
        if not paragraph:
            return
        text = " ".join(part.strip() for part in paragraph if part.strip()).strip()
        paragraph.clear()
        if text:
            segments.append(
                SpeechSegment(
                    slide=state.slide,
                    text=text,
                    pace=state.pace,
                    tone=state.tone,
                )
            )

    for line_number, line in enumerate(body.splitlines(), start=1):
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            in_code = not in_code
            warnings.append(f"Body line {line_number}: fenced code ignored.")
            continue
        if in_code:
            continue

        directive = DIRECTIVE_RE.match(line)
        if directive:
            flush_paragraph()
            name = directive.group(1).lower()
            value = directive.group(2).strip()
            if name == "slide":
                try:
                    slide = int(value)
                except ValueError as exc:
                    raise NarrationParseError(f"Invalid slide value at body line {line_number}: {value}") from exc
                if slide <= 0:
                    raise NarrationParseError(f"Slide must be positive at body line {line_number}.")
                if state.slide is not None and slide <= state.slide:
                    raise NarrationParseError("Slide directives must be strictly increasing.")
                state.slide = slide
            elif name == "pause":
                if value not in PAUSE_MS:
                    raise NarrationParseError(f"Invalid pause value at body line {line_number}: {value}")
                segments.append(PauseSegment(slide=state.slide, duration_ms=PAUSE_MS[value]))
            elif name == "pace":
                if value not in PACES:
                    raise NarrationParseError(f"Invalid pace value at body line {line_number}: {value}")
                state.pace = value
            elif name == "tone":
                if value not in TONES:
                    raise NarrationParseError(f"Invalid tone value at body line {line_number}: {value}")
                state.tone = value
            else:
                warnings.append(f"Body line {line_number}: unknown directive '{name}' ignored.")
            continue

        if stripped.startswith("<!--") and stripped.endswith("-->"):
            flush_paragraph()
            warnings.append(f"Body line {line_number}: unrecognized HTML comment ignored.")
            continue

        if not stripped:
            flush_paragraph()
            continue

        if _is_never_spoken_line(line, in_code=False):
            flush_paragraph()
            warnings.append(f"Body line {line_number}: Markdown metadata/structure ignored.")
            continue

        paragraph.append(stripped)

    flush_paragraph()

    if state.slide is None:
        raise NarrationParseError("Narration requires at least one slide directive.")
    if not any(isinstance(segment, SpeechSegment) for segment in segments):
        raise NarrationParseError("Narration contains no spoken prose.")

    return ParsedNarration(metadata=metadata, segments=segments, warnings=warnings)
