from __future__ import annotations

from types import SimpleNamespace

import pytest

from lectra_voice import launcher


def test_local_bind_accepts_default_loopback():
    assert launcher._local_bind("http://127.0.0.1:8000") == ("127.0.0.1", 8000)
    assert launcher._local_bind("http://localhost:8123") == ("localhost", 8123)


def test_local_bind_rejects_remote_autostart():
    with pytest.raises(RuntimeError, match="local HTTP URL"):
        launcher._local_bind("https://example.com:8000")


def test_start_service_reuses_healthy_existing_service(monkeypatch):
    monkeypatch.setattr(launcher, "_service_is_healthy", lambda _: True)
    managed = launcher._start_service("http://127.0.0.1:8000")
    assert managed.process is None
    assert managed.reused_existing is True


def test_stop_service_terminates_managed_process():
    class FakeProcess:
        def __init__(self):
            self.terminated = False
            self.killed = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout):
            return 0

        def kill(self):
            self.killed = True

    process = FakeProcess()
    launcher._stop_service(launcher.ManagedService(process=process, reused_existing=False))
    assert process.terminated is True
    assert process.killed is False
