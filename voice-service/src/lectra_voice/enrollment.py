from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


REFERENCE_VOICE_SCRIPT = """Hello everyone. Thank you for joining me today.

In this presentation, I will walk through the main idea and explain why it is important. I will start with some background, then go through the key points, and finally discuss what we can learn from them.

As we move through the presentation, I will highlight a few things that I think are especially important.

At the end, I will briefly summarize the main points and leave some time for questions.

Let's get started."""


class AudioPreparationError(RuntimeError):
    pass


def normalize_reference_audio(source: Path, destination: Path) -> Path:
    source = Path(source)
    destination = Path(destination)
    if not source.is_file():
        raise AudioPreparationError(f"Input audio does not exist: {source}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioPreparationError("ffmpeg is required to prepare voice samples.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "24000",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise AudioPreparationError("ffmpeg could not convert the voice sample to WAV.") from exc

    if not destination.is_file() or destination.stat().st_size == 0:
        raise AudioPreparationError("Voice sample conversion produced no output.")
    return destination
