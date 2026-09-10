from pathlib import Path

import numpy as np
import soundfile as sf

from lectra_voice import audio as audio_module
from lectra_voice.audio import render_segments
from lectra_voice.models import PauseSegment, SpeechSegment
from lectra_voice.tts.base import AudioChunk, BackendCapabilities, SynthesisRequest, TTSBackend


class FakeBackend(TTSBackend):
    name = "fake"
    capabilities = BackendCapabilities()

    def synthesize(self, request: SynthesisRequest) -> AudioChunk:
        return AudioChunk(np.ones(800, dtype=np.float32) * 0.1, 8000)


def test_render_segments_inserts_pause(tmp_path: Path):
    ref = tmp_path / "ref.wav"
    sf.write(ref, np.zeros(800, dtype=np.float32), 8000)
    out = tmp_path / "out.wav"

    summary = render_segments(
        segments=[
            SpeechSegment(slide=1, text="First."),
            PauseSegment(slide=1, duration_ms=700),
            SpeechSegment(slide=1, text="Second."),
        ],
        backend=FakeBackend(),
        reference_audio=ref,
        reference_text=None,
        language="en-US",
        output_path=out,
    )

    audio, sample_rate = sf.read(out)
    assert sample_rate == 8000
    assert len(audio) == 800 + 5600 + 800
    assert summary["speech_segments"] == 2
    assert summary["duration_seconds"] == 0.9


def test_leading_pause_is_discarded_until_sample_rate_known(tmp_path: Path):
    ref = tmp_path / "ref.wav"
    sf.write(ref, np.zeros(800, dtype=np.float32), 8000)
    out = tmp_path / "out.wav"

    render_segments(
        segments=[
            PauseSegment(slide=1, duration_ms=1200),
            SpeechSegment(slide=1, text="Start."),
        ],
        backend=FakeBackend(),
        reference_audio=ref,
        reference_text=None,
        language="en-US",
        output_path=out,
    )

    audio, _ = sf.read(out)
    assert len(audio) == 800


def test_mp3_uses_telegram_friendly_speech_bitrate(tmp_path: Path, monkeypatch):
    calls: list[list[str]] = []
    monkeypatch.setattr(audio_module.shutil, "which", lambda _: "/usr/bin/ffmpeg")
    monkeypatch.setattr(
        audio_module.subprocess,
        "run",
        lambda command, check: calls.append(command),
    )

    audio_module._write_mp3_from_wav(tmp_path / "in.wav", tmp_path / "out.mp3")

    command = calls[0]
    assert "-ac" in command and command[command.index("-ac") + 1] == "1"
    assert "-b:a" in command and command[command.index("-b:a") + 1] == "96k"
