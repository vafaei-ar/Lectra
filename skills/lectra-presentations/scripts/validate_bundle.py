#!/usr/bin/env python3
"""Perform structural synchronization checks across a Lectra PPTX, script, and narration."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NARRATION_SLIDE_RE = re.compile(r"^\s*<!--\s*slide\s*:\s*(\d+)\s*-->\s*$", re.I | re.M)
SCRIPT_SLIDE_RE = re.compile(r"^#{1,6}\s+Slide\s+(\d+)\s*:\s*.+$", re.I | re.M)

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def pptx_slide_count(path: Path) -> int:
    try:
        with zipfile.ZipFile(path) as zf:
            presentation = ET.fromstring(zf.read("ppt/presentation.xml"))
            rels = ET.fromstring(zf.read("ppt/_rels/presentation.xml.rels"))
            rel_targets = {
                rel.attrib["Id"]: rel.attrib.get("Target", "")
                for rel in rels.findall(f"{{{REL_NS}}}Relationship")
            }
            sld_ids = presentation.findall(f".//{{{P_NS}}}sldId")
            ordered = []
            for sld in sld_ids:
                rid = sld.attrib.get(f"{{{R_NS}}}id")
                if rid and "slides/slide" in rel_targets.get(rid, ""):
                    ordered.append(rel_targets[rid])
            if ordered:
                return len(ordered)
            return len(sld_ids)
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise ValueError(f"Could not read PPTX structure: {exc}") from exc


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Usage: validate_bundle.py <presentation.pptx> <presentation-script.md> <presentation-narration.md>",
            file=sys.stderr,
        )
        return 2

    pptx, script_path, narration_path = map(Path, sys.argv[1:])
    for path in (pptx, script_path, narration_path):
        if not path.is_file():
            print(f"ERROR: file not found: {path}", file=sys.stderr)
            return 2

    errors: list[str] = []
    warnings: list[str] = []
    try:
        slide_count = pptx_slide_count(pptx)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    script_text = script_path.read_text(encoding="utf-8")
    narration_text = narration_path.read_text(encoding="utf-8")
    script_slides = [int(x) for x in SCRIPT_SLIDE_RE.findall(script_text)]
    narration_slides = [int(x) for x in NARRATION_SLIDE_RE.findall(narration_text)]

    if not script_slides:
        errors.append("Presenter script contains no '# Slide N: Title' sections.")
    if not narration_slides:
        errors.append("Narration contains no slide directives.")

    for label, values in (("Presenter script", script_slides), ("Narration", narration_slides)):
        invalid = sorted({n for n in values if n < 1 or n > slide_count})
        if invalid:
            errors.append(f"{label} references slide(s) outside the {slide_count}-slide PPTX: {invalid}.")
        if len(values) != len(set(values)):
            errors.append(f"{label} contains duplicate slide references.")
        if any(b <= a for a, b in zip(values, values[1:])):
            errors.append(f"{label} slide references must be strictly increasing.")

    script_set = set(script_slides)
    narration_set = set(narration_slides)
    missing_script = sorted(narration_set - script_set)
    if missing_script:
        errors.append(f"Narration references slide(s) with no presenter-script section: {missing_script}.")

    script_without_narration = sorted(script_set - narration_set)
    if script_without_narration:
        warnings.append(
            "Presenter script has slide section(s) without narration: "
            f"{script_without_narration}. Confirm these are intentionally silent/backup slides."
        )

    for item in warnings:
        print(f"WARNING: {item}")
    for item in errors:
        print(f"ERROR: {item}", file=sys.stderr)

    print(
        f"INFO: PPTX slides={slide_count}; script slide sections={len(script_slides)}; "
        f"narrated slides={len(narration_slides)}."
    )
    if errors:
        print(f"FAILED: {len(errors)} structural error(s), {len(warnings)} warning(s).", file=sys.stderr)
        return 1
    print(f"OK: bundle structure is synchronized with {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
