from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audio import AudioRenderError, render_segments
from .models import SpeechSegment
from .parser import NarrationParseError, parse_narration
from .tts import DEFAULT_BACKEND, backend_availability, create_backend


def _load_markdown(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"Could not read {path}: {exc}") from exc


def _parse_command(args: argparse.Namespace) -> int:
    try:
        parsed = parse_narration(_load_markdown(args.input))
    except NarrationParseError as exc:
        print(f"Invalid narration: {exc}", file=sys.stderr)
        return 2

    payload = parsed.model_dump(mode="json")
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        speech = [segment for segment in parsed.segments if isinstance(segment, SpeechSegment)]
        print(f"Title: {parsed.metadata.get('title')}")
        print(f"Speech segments: {len(speech)}")
        print(f"Total segments: {len(parsed.segments)}")
        print(f"Warnings: {len(parsed.warnings)}")
        for warning in parsed.warnings:
            print(f"  - {warning}")
    return 0


def _backends_command(_: argparse.Namespace) -> int:
    availability = backend_availability()
    for name, installed in availability.items():
        state = "installed" if installed else "not installed"
        default = " (default)" if name == DEFAULT_BACKEND else ""
        print(f"{name}: {state}{default}")
    return 0


def _backend_kwargs(args: argparse.Namespace) -> dict[str, object]:
    if args.backend == "qwen3":
        return {
            "model_id": args.qwen_model,
            "device": args.device,
            "flash_attention": args.qwen_flash_attention,
            "x_vector_only": args.qwen_x_vector_only,
        }
    if args.backend == "chatterbox":
        return {"device": args.device}
    raise ValueError(args.backend)


def _generate_command(args: argparse.Namespace) -> int:
    try:
        parsed = parse_narration(_load_markdown(args.input))
    except NarrationParseError as exc:
        print(f"Invalid narration: {exc}", file=sys.stderr)
        return 2

    language = str(parsed.metadata.get("language", "en-US"))
    reference_text = args.reference_text
    if args.reference_text_file:
        reference_text = _load_markdown(args.reference_text_file).strip()

    if args.dry_run:
        speech = [segment for segment in parsed.segments if isinstance(segment, SpeechSegment)]
        print(f"Narration valid: {parsed.metadata.get('title')}")
        print(f"Backend: {args.backend}")
        print(f"Language: {language}")
        print(f"Speech segments: {len(speech)}")
        print(f"Reference audio: {args.reference_audio}")
        print(f"Output: {args.output}")
        if args.backend == "qwen3" and not reference_text and not args.qwen_x_vector_only:
            print("Qwen3 requirement not met: reference transcript is missing.", file=sys.stderr)
            return 2
        return 0

    backend = None
    try:
        backend = create_backend(args.backend, **_backend_kwargs(args))
        summary = render_segments(
            segments=parsed.segments,
            backend=backend,
            reference_audio=args.reference_audio,
            reference_text=reference_text,
            language=language,
            output_path=args.output,
        )
    except (AudioRenderError, RuntimeError, ValueError) as exc:
        print(f"Generation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if backend is not None:
            backend.close()

    print(json.dumps(summary, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lectra-voice",
        description="Parse and locally synthesize Lectra presentation narration.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_parser = subparsers.add_parser("parse", help="Validate and inspect narration Markdown.")
    parse_parser.add_argument("input", type=Path)
    parse_parser.add_argument("--json", action="store_true", help="Print parsed segments as JSON.")
    parse_parser.set_defaults(func=_parse_command)

    backends_parser = subparsers.add_parser("backends", help="Show locally installed TTS backends.")
    backends_parser.set_defaults(func=_backends_command)

    generate_parser = subparsers.add_parser("generate", help="Generate WAV or MP3 from narration Markdown.")
    generate_parser.add_argument("input", type=Path)
    generate_parser.add_argument(
        "--backend",
        choices=["chatterbox", "qwen3"],
        default=DEFAULT_BACKEND,
        help=f"TTS backend. Default: {DEFAULT_BACKEND}.",
    )
    generate_parser.add_argument("--reference-audio", type=Path, required=True)
    reference_group = generate_parser.add_mutually_exclusive_group()
    reference_group.add_argument("--reference-text", help="Transcript of the reference audio.")
    reference_group.add_argument("--reference-text-file", type=Path, help="UTF-8 file containing the reference transcript.")
    generate_parser.add_argument("--output", type=Path, required=True)
    generate_parser.add_argument("--device", default="auto", help="auto, cpu, cuda, cuda:0, or mps where supported.")
    generate_parser.add_argument("--dry-run", action="store_true", help="Validate inputs without loading a TTS model.")

    generate_parser.add_argument(
        "--qwen-model",
        default="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        help="Qwen3-TTS Base model ID or local model directory.",
    )
    generate_parser.add_argument(
        "--qwen-flash-attention",
        action="store_true",
        help="Load Qwen3-TTS with FlashAttention 2. Requires a compatible installation.",
    )
    generate_parser.add_argument(
        "--qwen-x-vector-only",
        action="store_true",
        help="Allow Qwen3 speaker-embedding-only cloning without a reference transcript. Quality may be lower.",
    )
    generate_parser.set_defaults(func=_generate_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
