from pathlib import Path

from lectra_voice.cli import main


NARRATION = '''---
lectra_schema: "1.0"
title: Test talk
language: en-US
default_pace: normal
default_tone: explanatory
---

<!-- slide: 1 -->

Good afternoon everyone.
'''


def _files(tmp_path: Path) -> tuple[Path, Path]:
    narration = tmp_path / "narration.md"
    narration.write_text(NARRATION, encoding="utf-8")
    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"placeholder")
    return narration, ref


def test_default_backend_is_chatterbox(tmp_path: Path, capsys):
    narration, ref = _files(tmp_path)
    code = main([
        "generate",
        str(narration),
        "--reference-audio",
        str(ref),
        "--output",
        str(tmp_path / "out.wav"),
        "--dry-run",
    ])
    assert code == 0
    assert "Backend: chatterbox" in capsys.readouterr().out


def test_dry_run_chatterbox_does_not_import_model(tmp_path: Path):
    narration, ref = _files(tmp_path)
    code = main([
        "generate",
        str(narration),
        "--backend",
        "chatterbox",
        "--reference-audio",
        str(ref),
        "--output",
        str(tmp_path / "out.wav"),
        "--dry-run",
    ])
    assert code == 0


def test_qwen_dry_run_requires_reference_transcript(tmp_path: Path):
    narration, ref = _files(tmp_path)
    code = main([
        "generate",
        str(narration),
        "--backend",
        "qwen3",
        "--reference-audio",
        str(ref),
        "--output",
        str(tmp_path / "out.wav"),
        "--dry-run",
    ])
    assert code == 2


def test_qwen_dry_run_allows_x_vector_only(tmp_path: Path):
    narration, ref = _files(tmp_path)
    code = main([
        "generate",
        str(narration),
        "--backend",
        "qwen3",
        "--reference-audio",
        str(ref),
        "--output",
        str(tmp_path / "out.wav"),
        "--qwen-x-vector-only",
        "--dry-run",
    ])
    assert code == 0
