import time
from pathlib import Path

from lectra_voice.jobs import RenderJobManager


class FakeStore:
    def get_voice(self, user_id: int, voice_id: str | None = None):
        return object()


class FakeRenderer:
    def __init__(self):
        self.store = FakeStore()

    def render_text_for_user(self, *, text: str, output_path: Path, progress_callback, **kwargs):
        progress_callback(0, 2, "waiting_for_gpu")
        progress_callback(0, 2, "loading_model")
        progress_callback(1, 2, "synthesizing")
        progress_callback(2, 2, "synthesizing")
        progress_callback(2, 2, "encoding")
        output_path.write_bytes(b"text-audio")
        return {
            "title": "Text message",
            "backend": "fake",
            "voice_id": "default",
            "duration_seconds": 1.0,
        }


def test_plain_text_job_completes_and_returns_audio():
    manager = RenderJobManager(FakeRenderer())  # type: ignore[arg-type]
    submitted = manager.submit_text(
        user_id=1,
        text="First short sentence. Second short sentence.",
        voice_id="default",
        output_format="mp3",
    )
    job_id = str(submitted["job_id"])

    for _ in range(100):
        snapshot = manager.snapshot(job_id)
        if snapshot["state"] == "completed":
            break
        time.sleep(0.01)
    else:
        raise AssertionError("plain-text job did not finish")

    payload, summary, output_format = manager.audio(job_id)
    assert payload == b"text-audio"
    assert summary["title"] == "Text message"
    assert output_format == "mp3"
