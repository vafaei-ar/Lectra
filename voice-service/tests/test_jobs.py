import time
from pathlib import Path

from lectra_voice.jobs import RenderJobManager


VALID_NARRATION = """---
lectra_schema: "1.0"
title: Progress test
language: en-US
---

<!-- slide: 1 -->

First sentence.

Second sentence.
"""


class FakeStore:
    def get_voice(self, user_id: int, voice_id: str | None = None):
        return object()


class FakeRenderer:
    def __init__(self, fail: bool = False):
        self.store = FakeStore()
        self.fail = fail

    def render_for_user(self, *, output_path: Path, progress_callback, **kwargs):
        progress_callback(0, 2, "waiting_for_gpu")
        progress_callback(0, 2, "loading_model")
        if self.fail:
            raise RuntimeError("synthetic failure")
        progress_callback(1, 2, "synthesizing")
        progress_callback(2, 2, "synthesizing")
        progress_callback(2, 2, "encoding")
        output_path.write_bytes(b"audio")
        return {
            "title": "Progress test",
            "backend": "fake",
            "voice_id": "default",
            "duration_seconds": 1.0,
        }


def _wait(manager: RenderJobManager, job_id: str) -> dict[str, object]:
    for _ in range(100):
        snapshot = manager.snapshot(job_id)
        if snapshot["state"] in {"completed", "failed"}:
            return snapshot
        time.sleep(0.01)
    raise AssertionError("render job did not finish")


def test_render_job_reports_completion_and_audio():
    manager = RenderJobManager(FakeRenderer())  # type: ignore[arg-type]
    submitted = manager.submit(
        user_id=1,
        markdown=VALID_NARRATION,
        voice_id="default",
        output_format="mp3",
    )
    finished = _wait(manager, str(submitted["job_id"]))

    assert finished["state"] == "completed"
    assert finished["stage"] == "completed"
    assert finished["completed_segments"] == 2
    assert finished["total_segments"] == 2
    assert finished["percent"] == 100

    payload, summary, output_format = manager.audio(str(submitted["job_id"]))
    assert payload == b"audio"
    assert summary["backend"] == "fake"
    assert output_format == "mp3"


def test_render_job_surfaces_backend_error():
    manager = RenderJobManager(FakeRenderer(fail=True))  # type: ignore[arg-type]
    submitted = manager.submit(
        user_id=1,
        markdown=VALID_NARRATION,
        voice_id="default",
    )
    finished = _wait(manager, str(submitted["job_id"]))

    assert finished["state"] == "failed"
    assert finished["stage"] == "failed"
    assert "synthetic failure" in str(finished["error"])
