from __future__ import annotations

import os
import stat

import pytest

from lectra_voice import launcher


def test_local_bind_accepts_default_loopback():
    assert launcher._local_bind("http://127.0.0.1:8000") == ("127.0.0.1", 8000)
    assert launcher._local_bind("http://localhost:8123") == ("localhost", 8123)


def test_local_bind_rejects_remote_autostart():
    with pytest.raises(RuntimeError, match="local HTTP URL"):
        launcher._local_bind("https://example.com:8000")


def test_start_service_reuses_compatible_existing_service(monkeypatch):
    monkeypatch.setattr(
        launcher,
        "_health_payload",
        lambda _: {
            "service": "lectra-voice",
            "version": launcher.__version__,
            "render_job_progress": True,
        },
    )
    monkeypatch.setattr(launcher, "_service_is_compatible", lambda _: True)
    managed = launcher._start_service("http://127.0.0.1:8000")
    assert managed.process is None
    assert managed.reused_existing is True


def test_start_service_rejects_incompatible_existing_service(monkeypatch):
    monkeypatch.setattr(
        launcher,
        "_health_payload",
        lambda _: {
            "service": "lectra-voice",
            "version": "0.2.0",
            "render_job_progress": False,
        },
    )
    monkeypatch.setattr(launcher, "_service_is_compatible", lambda _: False)
    with pytest.raises(RuntimeError, match="incompatible Lectra voice service"):
        launcher._start_service("http://127.0.0.1:8000")


def test_managed_start_refuses_to_reuse_manual_service(monkeypatch):
    monkeypatch.setattr(
        launcher,
        "_health_payload",
        lambda _: {
            "service": "lectra-voice",
            "version": launcher.__version__,
            "render_job_progress": True,
        },
    )
    monkeypatch.setattr(launcher, "_service_is_compatible", lambda _: True)
    with pytest.raises(RuntimeError, match="outside the managed service"):
        launcher._start_service("http://127.0.0.1:8000", reuse_existing=False)


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


def test_configuration_file_is_private(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    path = launcher._save_configuration(token="123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")

    assert path == tmp_path / "lectra" / "lectra.env"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    values = launcher._read_env_file(path)
    assert values["TELEGRAM_BOT_TOKEN"] == "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
    assert values["LECTRA_DEVICE"] == "cuda"
    assert values["LECTRA_VOICE_SERVICE_URL"] == "http://127.0.0.1:8000"


def test_systemd_unit_runs_foreground_worker_without_embedding_token(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    text = launcher._unit_text()
    env_path = os.path.abspath(tmp_path / "lectra" / "lectra.env")

    assert "lectra_voice.launcher foreground" in text
    assert "Restart=on-failure" in text
    assert "KillMode=control-group" in text
    assert "LECTRA_SYSTEMD_MANAGED=1" in text
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in text
    assert f"EnvironmentFile={env_path}" in text
    assert 'EnvironmentFile="' not in text


def test_systemd_unit_preserves_venv_python_path(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    fake_venv_python = "/tmp/lectra-test/.venv-chatterbox/bin/python"
    monkeypatch.setattr(launcher.sys, "executable", fake_venv_python)

    text = launcher._unit_text()

    assert f'ExecStart="{os.path.abspath(fake_venv_python)}" -m lectra_voice.launcher foreground' in text


def test_systemd_unit_rejects_whitespace_in_environment_file_path(tmp_path, monkeypatch):
    spaced = tmp_path / "config with spaces"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(spaced))

    with pytest.raises(RuntimeError, match="EnvironmentFile path cannot contain whitespace"):
        launcher._unit_text()


def test_no_subcommand_defaults_to_status():
    args = launcher._parse_args([])
    assert args.command is None
