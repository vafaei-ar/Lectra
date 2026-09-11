from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse


DEFAULT_SERVICE_URL = "http://127.0.0.1:8000"


@dataclass
class ManagedService:
    process: subprocess.Popen[bytes] | None
    reused_existing: bool


def _health_url(service_url: str) -> str:
    return service_url.rstrip("/") + "/health"


def _service_is_healthy(service_url: str, timeout: float = 0.75) -> bool:
    try:
        with urllib.request.urlopen(_health_url(service_url), timeout=timeout) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _local_bind(service_url: str) -> tuple[str, int]:
    parsed = urlparse(service_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError(
            "Automatic service startup requires a local HTTP URL such as "
            "http://127.0.0.1:8000. Set LECTRA_VOICE_SERVICE_URL to use a different "
            "already-running service."
        )
    return parsed.hostname, parsed.port or 8000


def _start_service(service_url: str) -> ManagedService:
    if _service_is_healthy(service_url):
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
        if _service_is_healthy(service_url):
            return
        if managed.process is not None and managed.process.poll() is not None:
            raise RuntimeError(
                f"Lectra voice service exited during startup with code {managed.process.returncode}."
            )
        time.sleep(0.25)
    raise RuntimeError(
        f"Lectra voice service did not become healthy within {timeout_seconds:.0f} seconds."
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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lectra",
        description="Start the local Lectra voice service and Telegram bot together.",
    )
    parser.add_argument(
        "--service-url",
        default=os.getenv("LECTRA_VOICE_SERVICE_URL", DEFAULT_SERVICE_URL),
        help="Local voice-service URL (default: %(default)s)",
    )
    parser.add_argument(
        "--device",
        default=os.getenv("LECTRA_DEVICE", "cuda"),
        help="TTS device (default: %(default)s)",
    )
    parser.add_argument(
        "--data-dir",
        default=os.getenv("LECTRA_DATA_DIR", "~/.local/share/lectra"),
        help="Lectra data directory (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is required. Set it once in your shell environment, then run `lectra`."
        )

    os.environ["LECTRA_VOICE_SERVICE_URL"] = args.service_url.rstrip("/")
    os.environ["LECTRA_DEVICE"] = args.device
    os.environ["LECTRA_DATA_DIR"] = os.path.expanduser(args.data_dir)

    print("Starting Lectra...")
    managed = _start_service(os.environ["LECTRA_VOICE_SERVICE_URL"])
    try:
        _wait_until_healthy(managed, os.environ["LECTRA_VOICE_SERVICE_URL"])
        if managed.reused_existing:
            print("Voice service: ready (using existing local service)")
        else:
            print("Voice service: ready")
        print(f"Device: {args.device}")
        print("Telegram bot: starting")
        print("Press Ctrl+C to stop Lectra.\n")

        # Import only after launcher configuration has populated environment variables;
        # telegram_bot creates its local VoiceStore and settings at import time.
        from .telegram_bot import build_application

        build_application(token).run_polling(allowed_updates=None)
    finally:
        if managed.process is not None:
            print("\nStopping Lectra voice service...")
        _stop_service(managed)
