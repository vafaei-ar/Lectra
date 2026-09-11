from __future__ import annotations

import argparse
import getpass
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from . import __version__


DEFAULT_SERVICE_URL = "http://127.0.0.1:8000"
UNIT_NAME = "lectra.service"
CONFIG_KEYS = (
    "TELEGRAM_BOT_TOKEN",
    "LECTRA_DATA_DIR",
    "LECTRA_DEVICE",
    "LECTRA_VOICE_SERVICE_URL",
)


@dataclass
class ManagedService:
    process: subprocess.Popen[bytes] | None
    reused_existing: bool


def _xdg_config_home() -> Path:
    value = os.getenv("XDG_CONFIG_HOME")
    return Path(value).expanduser() if value else Path.home() / ".config"


def _config_dir() -> Path:
    return _xdg_config_home() / "lectra"


def _env_file() -> Path:
    return _config_dir() / "lectra.env"


def _systemd_user_dir() -> Path:
    return _xdg_config_home() / "systemd" / "user"


def _unit_file() -> Path:
    return _systemd_user_dir() / UNIT_NAME


def _health_url(service_url: str) -> str:
    return service_url.rstrip("/") + "/health"


def _health_payload(service_url: str, timeout: float = 0.75) -> dict[str, object] | None:
    try:
        with urllib.request.urlopen(_health_url(service_url), timeout=timeout) as response:
            if not 200 <= response.status < 300:
                return None
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, UnicodeDecodeError):
        return None


def _service_is_healthy(service_url: str, timeout: float = 0.75) -> bool:
    return _health_payload(service_url, timeout=timeout) is not None


def _service_is_compatible(service_url: str) -> bool:
    payload = _health_payload(service_url)
    if payload is None:
        return False
    progress = bool(payload.get("render_job_progress") or payload.get("progress_reporting"))
    return (
        payload.get("service") == "lectra-voice"
        and str(payload.get("version") or "") == __version__
        and progress
    )


def _local_bind(service_url: str) -> tuple[str, int]:
    parsed = urlparse(service_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError(
            "Automatic service startup requires a local HTTP URL such as "
            "http://127.0.0.1:8000. Set LECTRA_VOICE_SERVICE_URL to use a different "
            "already-running service."
        )
    return parsed.hostname, parsed.port or 8000


def _start_service(service_url: str, *, reuse_existing: bool = True) -> ManagedService:
    existing = _health_payload(service_url)
    if existing is not None:
        if not _service_is_compatible(service_url):
            version = existing.get("version", "unknown")
            raise RuntimeError(
                f"An incompatible Lectra voice service is already running at {service_url} "
                f"(version {version}). Stop that old/manual service before starting this build."
            )
        if not reuse_existing:
            raise RuntimeError(
                f"A Lectra voice service is already running outside the managed service at "
                f"{service_url}. Stop that manual process once, then run `lectra start` again."
            )
        return ManagedService(process=None, reused_existing=True)

    host, port = _local_bind(service_url)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "lectra_voice.service:app",
            "--host",
            host,
            "--port",
            str(port),
            "--log-level",
            os.getenv("LECTRA_SERVICE_LOG_LEVEL", "warning"),
        ],
        env=os.environ.copy(),
    )
    return ManagedService(process=process, reused_existing=False)


def _wait_until_healthy(
    managed: ManagedService,
    service_url: str,
    timeout_seconds: float = 30.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _service_is_compatible(service_url):
            return
        if managed.process is not None and managed.process.poll() is not None:
            raise RuntimeError(
                f"Lectra voice service exited during startup with code {managed.process.returncode}."
            )
        time.sleep(0.25)
    raise RuntimeError(
        f"Lectra voice service did not become compatible and healthy within "
        f"{timeout_seconds:.0f} seconds."
    )


def _stop_service(managed: ManagedService) -> None:
    process = managed.process
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3.0)


def _read_env_file(path: Path | None = None) -> dict[str, str]:
    path = path or _env_file()
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if key not in CONFIG_KEYS:
            continue
        try:
            parsed = shlex.split(raw_value, posix=True)
        except ValueError:
            continue
        if len(parsed) == 1:
            values[key] = parsed[0]
        elif raw_value == "":
            values[key] = ""
    return values


def _quote_env_value(value: str) -> str:
    if any(char in value for char in ("\n", "\r", "\x00")):
        raise RuntimeError("Lectra configuration values cannot contain newlines or NUL bytes.")
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("$", "\\$")
        .replace("`", "\\`")
    )
    return f'"{escaped}"'


def _save_configuration(*, token: str | None = None) -> Path:
    path = _env_file()
    existing = _read_env_file(path)

    resolved_token = token or existing.get("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    if not resolved_token:
        if not sys.stdin.isatty():
            raise RuntimeError(
                "No Telegram bot token is configured. Run `lectra configure` from a terminal first."
            )
        resolved_token = getpass.getpass("Telegram bot token (input hidden): ").strip()
    if not resolved_token:
        raise RuntimeError("Telegram bot token cannot be empty.")

    values = {
        "TELEGRAM_BOT_TOKEN": resolved_token,
        "LECTRA_DATA_DIR": os.getenv(
            "LECTRA_DATA_DIR", existing.get("LECTRA_DATA_DIR", "~/.local/share/lectra")
        ),
        "LECTRA_DEVICE": os.getenv("LECTRA_DEVICE", existing.get("LECTRA_DEVICE", "cuda")),
        "LECTRA_VOICE_SERVICE_URL": os.getenv(
            "LECTRA_VOICE_SERVICE_URL",
            existing.get("LECTRA_VOICE_SERVICE_URL", DEFAULT_SERVICE_URL),
        ),
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    temp = path.with_suffix(".tmp")
    temp.write_text(
        "\n".join(f"{key}={_quote_env_value(values[key])}" for key in CONFIG_KEYS) + "\n",
        encoding="utf-8",
    )
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def _systemd_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _unit_text() -> str:
    env_path = Path(os.path.abspath(_env_file()))
    if any(char.isspace() for char in str(env_path)):
        raise RuntimeError(
            "Lectra's systemd EnvironmentFile path cannot contain whitespace. "
            "Use the default XDG config location or an XDG_CONFIG_HOME without spaces."
        )
    # Preserve the venv interpreter path. Resolving this symlink can jump to the
    # base Python interpreter and lose the venv site-packages under systemd.
    python = Path(os.path.abspath(sys.executable))
    return f"""[Unit]
Description=Lectra local presentation voice service and Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile={env_path}
Environment=PYTHONUNBUFFERED=1
Environment=LECTRA_SYSTEMD_MANAGED=1
ExecStart={_systemd_quote(str(python))} -m lectra_voice.launcher foreground
Restart=on-failure
RestartSec=3
KillMode=control-group
TimeoutStopSec=20

[Install]
WantedBy=default.target
"""


def _require_command(name: str) -> str:
    command = shutil.which(name)
    if not command:
        raise RuntimeError(f"Required command is not available: {name}")
    return command


def _systemctl(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    systemctl = _require_command("systemctl")
    try:
        return subprocess.run(
            [systemctl, "--user", *args],
            check=check,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(
            "systemctl --user failed"
            + (f": {detail}" if detail else ". Make sure your user systemd session is available.")
        ) from exc


def _install_unit() -> Path:
    unit_path = _unit_file()
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(_unit_text(), encoding="utf-8")
    try:
        unit_path.chmod(0o644)
    except OSError:
        pass
    _systemctl("daemon-reload")
    return unit_path


def _systemd_state() -> str:
    result = _systemctl("is-active", UNIT_NAME, check=False)
    state = (result.stdout or "").strip()
    return state or "inactive"


def _systemd_enabled() -> str:
    result = _systemctl("is-enabled", UNIT_NAME, check=False)
    state = (result.stdout or "").strip()
    return state or "disabled"


def _configured_service_url() -> str:
    values = _read_env_file()
    return values.get("LECTRA_VOICE_SERVICE_URL", DEFAULT_SERVICE_URL)


def _wait_background_healthy(timeout_seconds: float = 20.0) -> None:
    service_url = _configured_service_url()
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _systemd_state() == "active" and _service_is_compatible(service_url):
            return
        time.sleep(0.25)
    _systemctl("stop", UNIT_NAME, check=False)
    raise RuntimeError(
        "Lectra did not become healthy. Run `lectra status` and `lectra logs` for details."
    )


def _preflight_background_start() -> None:
    service_url = _configured_service_url()
    if _systemd_state() != "active" and _health_payload(service_url) is not None:
        raise RuntimeError(
            f"A voice service is already running manually at {service_url}. Stop that old manual "
            "process once, then run `lectra start` again. The managed service will be terminal-independent thereafter."
        )


def _start_background(*, enable: bool = False, restart: bool = False) -> None:
    _save_configuration()
    _install_unit()
    _preflight_background_start()

    if enable:
        _systemctl("enable", UNIT_NAME)

    if restart:
        _systemctl("restart", UNIT_NAME)
    elif _systemd_state() == "active":
        print("Lectra is already running.")
        _print_status()
        return
    else:
        _systemctl("start", UNIT_NAME)

    _wait_background_healthy()
    print("Lectra is running in the background.")
    print("You can close this terminal.")
    print("Use `lectra status`, `lectra logs`, `lectra restart`, or `lectra stop` anytime.")


def _stop_background() -> None:
    if _systemd_state() in {"inactive", "unknown"}:
        print("Lectra is already stopped.")
        return
    _systemctl("stop", UNIT_NAME)
    print("Lectra stopped.")


def _print_status() -> None:
    state = _systemd_state()
    enabled = _systemd_enabled()
    print(f"Lectra: {state}")
    print(f"Autostart: {enabled}")
    service_url = _configured_service_url()
    payload = _health_payload(service_url)
    if payload is None:
        print("Voice service: unavailable")
    else:
        compatibility = "compatible" if _service_is_compatible(service_url) else "INCOMPATIBLE"
        print(
            f"Voice service: healthy, version {payload.get('version', 'unknown')} "
            f"({compatibility})"
        )
        print(
            "Progress API: "
            + ("available" if payload.get("render_job_progress") or payload.get("progress_reporting") else "unavailable")
        )
    print(f"Service URL: {service_url}")


def _show_logs(*, follow: bool, lines: int) -> None:
    journalctl = _require_command("journalctl")
    command = [journalctl, "--user", "-u", UNIT_NAME, "-n", str(lines)]
    if not follow:
        command.append("--no-pager")
    else:
        command.append("--follow")
    subprocess.run(command, check=False)


def _configure() -> None:
    if not sys.stdin.isatty():
        raise RuntimeError("`lectra configure` requires an interactive terminal.")
    token = getpass.getpass("New Telegram bot token (input hidden): ").strip()
    if not token:
        raise RuntimeError("Telegram bot token cannot be empty.")
    path = _save_configuration(token=token)
    print(f"Lectra configuration saved privately in {path}.")
    print("If Lectra is already running, run `lectra restart` to use the new token.")


def _run_foreground() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required by the Lectra worker.")

    logging.basicConfig(
        level=os.getenv("LECTRA_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Telegram Bot API URLs contain the bot token. Never emit routine request URLs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    service_url = os.getenv("LECTRA_VOICE_SERVICE_URL", DEFAULT_SERVICE_URL).rstrip("/")
    managed_mode = os.getenv("LECTRA_SYSTEMD_MANAGED") == "1"
    managed = _start_service(service_url, reuse_existing=not managed_mode)
    try:
        _wait_until_healthy(managed, service_url)
        logging.getLogger(__name__).info(
            "Lectra voice service ready at %s; starting Telegram bot", service_url
        )
        from .telegram_bot import build_application

        build_application(token).run_polling(allowed_updates=None)
    finally:
        _stop_service(managed)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lectra",
        description="Manage the local Lectra background service.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("start", help="Start Lectra in the background")
    subparsers.add_parser("stop", help="Stop Lectra")
    subparsers.add_parser("restart", help="Restart Lectra")
    subparsers.add_parser("status", help="Show service and API status")
    subparsers.add_parser("configure", help="Set or replace the Telegram bot token securely")
    subparsers.add_parser("enable", help="Enable autostart at user login and start Lectra")
    subparsers.add_parser("disable", help="Disable autostart without stopping Lectra")
    logs = subparsers.add_parser("logs", help="Show Lectra service logs")
    logs.add_argument("-f", "--follow", action="store_true", help="Follow new log messages")
    logs.add_argument("-n", "--lines", type=int, default=100, help="Number of recent lines")
    subparsers.add_parser("foreground", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    command = args.command or "status"
    try:
        if command == "start":
            _start_background()
        elif command == "stop":
            _stop_background()
        elif command == "restart":
            _start_background(restart=True)
        elif command == "status":
            _print_status()
        elif command == "configure":
            _configure()
        elif command == "enable":
            _start_background(enable=True)
        elif command == "disable":
            _systemctl("disable", UNIT_NAME, check=False)
            print("Lectra autostart disabled. The currently running service, if any, was not stopped.")
        elif command == "logs":
            _show_logs(follow=bool(args.follow), lines=max(int(args.lines), 1))
        elif command == "foreground":
            _run_foreground()
        else:
            raise RuntimeError(f"Unknown command: {command}")
    except KeyboardInterrupt:
        # Ctrl+C while viewing followed logs or running foreground debug mode must
        # not stop a separately managed Lectra service.
        return
    except RuntimeError as exc:
        raise SystemExit(f"Lectra error: {exc}") from exc


if __name__ == "__main__":
    main()
