#!/usr/bin/env python3
"""Validate a Lectra narration Markdown file without external dependencies."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED = {
    "slide": None,
    "pause": {"short", "medium", "long"},
    "pace": {"slow", "normal", "fast"},
    "tone": {"explanatory", "serious", "enthusiastic", "reflective"},
}
DIRECTIVE_RE = re.compile(r"^\s*<!--\s*([a-zA-Z_]+)\s*:\s*(.*?)\s*-->\s*$")
URL_RE = re.compile(r"https?://|www\.", re.I)
SLIDE_SPOKEN_RE = re.compile(r"\bslide\s+\d+\b", re.I)


def parse_frontmatter(lines: list[str]) -> tuple[dict[str, str], int, list[str]]:
    errors: list[str] = []
    if not lines or lines[0].strip() != "---":
        return {}, 0, ["Missing YAML front matter opening '---'."]

    metadata: dict[str, str] = {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
        raw = lines[i].strip()
        if not raw or raw.startswith("#"):
            continue
        if ":" not in raw:
            errors.append(f"Front matter line {i+1} is not key:value syntax.")
            continue
        key, value = raw.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"\'')

    if end is None:
        errors.append("Missing YAML front matter closing '---'.")
        return metadata, len(lines), errors
    return metadata, end + 1, errors


def validate(path: Path) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    metadata, body_start, errors = parse_frontmatter(lines)
    warnings: list[str] = []

    if metadata.get("lectra_schema") != "1.0":
        errors.append("lectra_schema must be exactly '1.0'.")
    if not metadata.get("title", "").strip():
        errors.append("title is required in front matter.")

    slide_numbers: list[int] = []
    spoken_lines: list[str] = []
    in_code = False

    for lineno, line in enumerate(lines[body_start:], start=body_start + 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            warnings.append(f"Line {lineno}: fenced code is never spoken and should not appear in narration output.")
            continue
        if in_code or not stripped:
            continue

        match = DIRECTIVE_RE.match(line)
        if match:
            name, value = match.group(1).lower(), match.group(2).strip()
            if name not in ALLOWED:
                warnings.append(f"Line {lineno}: unknown directive '{name}' will be ignored by the voice service.")
                continue
            if name == "slide":
                try:
                    number = int(value)
                    if number <= 0:
                        raise ValueError
                    slide_numbers.append(number)
                except ValueError:
                    errors.append(f"Line {lineno}: slide must be a positive integer.")
            elif value not in ALLOWED[name]:
                errors.append(f"Line {lineno}: invalid {name} value '{value}'.")
            continue

        if stripped.startswith("<!--") and stripped.endswith("-->"):
            warnings.append(f"Line {lineno}: unrecognized HTML comment will be ignored and never spoken.")
            continue
        if stripped.startswith("#"):
            warnings.append(f"Line {lineno}: Markdown heading will be ignored and should be removed.")
            continue
        if re.match(r"^\s*(?:[-*+] |\d+[.)] )", line):
            warnings.append(f"Line {lineno}: Markdown list item will be ignored and should be rewritten as speech.")
            continue
        if "|" in stripped and stripped.count("|") >= 2:
            warnings.append(f"Line {lineno}: probable Markdown table content should not appear in narration output.")
            continue

        spoken_lines.append(stripped)
        if URL_RE.search(stripped):
            warnings.append(f"Line {lineno}: URL appears in spoken prose.")
        if SLIDE_SPOKEN_RE.search(stripped):
            warnings.append(f"Line {lineno}: literal slide-number language appears in spoken prose; confirm it is intentional.")

    if not slide_numbers:
        errors.append("At least one <!-- slide: N --> directive is required.")
    if any(b <= a for a, b in zip(slide_numbers, slide_numbers[1:])):
        errors.append("Slide directives must be strictly increasing.")
    if not spoken_lines:
        errors.append("Narration contains no spoken prose.")

    return errors, warnings


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_narration.py <presentation-narration.md>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 2

    errors, warnings = validate(path)
    for item in warnings:
        print(f"WARNING: {item}")
    for item in errors:
        print(f"ERROR: {item}", file=sys.stderr)

    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s).", file=sys.stderr)
        return 1
    print(f"OK: narration schema 1.0 valid with {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
