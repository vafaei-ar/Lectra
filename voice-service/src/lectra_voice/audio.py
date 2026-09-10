from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from .models import PauseSegment, SpeechSegment
from .tts.base import SynthesisRequest, TTSBackend


class AudioRenderError(RuntimeError):
    pass


def _ensure_reference_audio(path: Path) -> None:
    if not path.is_file():
        raise AudioRenderError(f"Reference audio does not exist: {path}")


def _write_mp3_from_wav(wav_path: Path, output_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioRenderError(
            "MP3 output requires ffmpeg on PATH. Use a .wav output or install ffmpeg."
        )
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(wav_path),
        "-codec:a",
        "libmp3lame",
        "-ac",
        "1",
        "-b:a",
        "96k",
        str(output_path),
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise AudioRenderError("ffmpeg failed while creating MP3 output.") from exc


def render_segments(
    *,
    segments: list[SpeechSegment | PauseSegment],
    backend: TTSBackend,
    reference_audio: Path,
    reference_text: str | None,
    language: str,
    output_path: Path,
) -> dict[str, object]:
    """Render parsed narration sequentially without holding the full talk in RAM."""

    _ensure_reference_audio(reference_audio)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    speech_count = sum(isinstance(segment, SpeechSegment) for segment in segments)
    if speech_count == 0:
        raise AudioRenderError("There are no speech segments to render.")

    with tempfile.TemporaryDirectory(prefix="lectra-") as temp_dir:
        wav_path = (
            output_path
            if output_path.suffix.lower() == ".wav"
            else Path(temp_dir) / "presentation.wav"
        )

        writer: sf.SoundFile | None = None
        sample_rate: int | None = None
        rendered_speech = 0
        total_frames = 0

        try:
            for segment in segments:
                if isinstance(segment, SpeechSegment):
                    chunk = backend.synthesize(
                        SynthesisRequest(
                            text=segment.text,
                            reference_audio=reference_audio,
                            reference_text=reference_text,
                            language=language,
                            pace=segment.pace,
                            tone=segment.tone,
                        )
                    )
                    audio = chunk.mono_float32()
                    if sample_rate is None:
                        sample_rate = chunk.sample_rate
                        writer = sf.SoundFile(
                            str(wav_path),
                            mode="w",
                            samplerate=sample_rate,
                            channels=1,
                            subtype="PCM_16",
                        )
                    elif chunk.sample_rate != sample_rate:
                        raise AudioRenderError(
                            f"Backend changed sample rate from {sample_rate} to "
                            f"{chunk.sample_rate}; mixed sample rates are not supported."
                        )
                    assert writer is not None
                    writer.write(audio)
                    total_frames += len(audio)
                    rendered_speech += 1
                else:
                    if sample_rate is None or writer is None:
                        continue
                    silence_frames = round(sample_rate * segment.duration_ms / 1000)
                    writer.write(np.zeros(silence_frames, dtype=np.float32))
                    total_frames += silence_frames
        finally:
            if writer is not None:
                writer.close()

        if sample_rate is None:
            raise AudioRenderError("Backend did not produce audio.")

        if output_path.suffix.lower() == ".mp3":
            _write_mp3_from_wav(wav_path, output_path)
        elif output_path.suffix.lower() != ".wav":
            raise AudioRenderError("Output must end in .wav or .mp3.")

    return {
        "backend": backend.name,
        "output": str(output_path),
        "sample_rate": sample_rate,
        "speech_segments": rendered_speech,
        "duration_seconds": total_frames / sample_rate,
    }
