from __future__ import annotations

import io
import json
import os
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

from .tts import DEFAULT_BACKEND


MAX_PRESET_DOWNLOAD_BYTES = 20 * 1024 * 1024
MAX_PRESET_ARCHIVE_BYTES = 100 * 1024 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 45.0


@dataclass(frozen=True)
class SystemVoiceSpec:
    voice_id: str
    display_name: str
    gender: str
    accent: str
    source_speaker: str
    reference_url: str
    fallback_urls: tuple[str, ...]
    archive_member: str
    source_homepage: str
    license_name: str = "CMU ARCTIC License"


SYSTEM_VOICES: dict[str, SystemVoiceSpec] = {
    "us-woman": SystemVoiceSpec(
        voice_id="us-woman",
        display_name="US Woman",
        gender="female",
        accent="US English",
        source_speaker="CMU ARCTIC SLT",
        reference_url=(
            "http://festvox.org/cmu_arctic/cmu_arctic/"
            "cmu_us_slt_arctic/wav/arctic_a0001.wav"
        ),
        fallback_urls=(
            "https://festvox.org/cmu_arctic/cmu_arctic/"
            "cmu_us_slt_arctic/wav/arctic_a0001.wav",
            "http://festvox.org/cmu_arctic/cmu_arctic/packed/"
            "cmu_us_slt_arctic-0.95-release.zip",
            "http://www.speech.cs.cmu.edu/cmu_arctic/packed/"
            "cmu_us_slt_arctic-0.95-release.zip",
        ),
        archive_member="cmu_us_slt_arctic/wav/arctic_a0001.wav",
        source_homepage="https://www.festvox.org/cmu_arctic/",
    ),
    "us-man": SystemVoiceSpec(
        voice_id="us-man",
        display_name="US Man",
        gender="male",
        accent="US English",
        source_speaker="CMU ARCTIC BDL",
        reference_url=(
            "http://festvox.org/cmu_arctic/cmu_arctic/"
            "cmu_us_bdl_arctic/wav/arctic_a0001.wav"
        ),
        fallback_urls=(
            "https://festvox.org/cmu_arctic/cmu_arctic/"
            "cmu_us_bdl_arctic/wav/arctic_a0001.wav",
            "http://festvox.org/cmu_arctic/cmu_arctic/packed/"
            "cmu_us_bdl_arctic-0.95-release.zip",
            "http://www.speech.cs.cmu.edu/cmu_arctic/packed/"
            "cmu_us_bdl_arctic-0.95-release.zip",
        ),
        archive_member="cmu_us_bdl_arctic/wav/arctic_a0001.wav",
        source_homepage="https://www.festvox.org/cmu_arctic/",
    ),
}


class SystemVoiceError(RuntimeError):
    pass


def system_voice_specs() -> list[SystemVoiceSpec]:
    return [SYSTEM_VOICES["us-woman"], SYSTEM_VOICES["us-man"]]


def is_system_voice_id(voice_id: str | None) -> bool:
    return bool(voice_id and voice_id in SYSTEM_VOICES)


def system_voice_label(voice_id: str | None) -> str | None:
    spec = SYSTEM_VOICES.get(str(voice_id or ""))
    return spec.display_name if spec else None


def _looks_like_wav(payload: bytes) -> bool:
    return (
        len(payload) >= 44
        and payload[:4] == b"RIFF"
        and payload[8:12] == b"WAVE"
    )


def _read_url(url: str, *, max_bytes: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Lectra/0.3 preset-voice downloader",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise SystemVoiceError("download exceeded the configured safety size limit")
    return payload


def _payload_from_candidate(spec: SystemVoiceSpec, url: str) -> bytes:
    if url.lower().endswith(".zip"):
        archive = _read_url(url, max_bytes=MAX_PRESET_ARCHIVE_BYTES)
        try:
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                payload = bundle.read(spec.archive_member)
        except (zipfile.BadZipFile, KeyError) as exc:
            raise SystemVoiceError(
                f"archive did not contain {spec.archive_member}"
            ) from exc
        if len(payload) > MAX_PRESET_DOWNLOAD_BYTES:
            raise SystemVoiceError("reference WAV exceeded the safety size limit")
        return payload

    return _read_url(url, max_bytes=MAX_PRESET_DOWNLOAD_BYTES)


def _error_detail(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code} {exc.reason}"
    if isinstance(exc, urllib.error.URLError):
        return str(exc.reason)
    return str(exc) or type(exc).__name__


def _download(spec: SystemVoiceSpec) -> tuple[bytes, str]:
    failures: list[str] = []
    candidates = (spec.reference_url, *spec.fallback_urls)

    for url in candidates:
        try:
            payload = _payload_from_candidate(spec, url)
            if not _looks_like_wav(payload):
                raise SystemVoiceError("response was not a valid WAV file")
            return payload, url
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            SystemVoiceError,
            zipfile.BadZipFile,
        ) as exc:
            failures.append(f"{url}: {_error_detail(exc)}")

    detail = " | ".join(failures[-3:])
    raise SystemVoiceError(
        "Could not download the preset voice reference clip from any CMU ARCTIC source. "
        f"Last attempts: {detail}. "
        "The preset was not selected. Try again later or use /setupvoice."
    )


def ensure_system_voice(root: Path, voice_id: str) -> tuple[Path, SystemVoiceSpec]:
    spec = SYSTEM_VOICES.get(voice_id)
    if spec is None:
        raise SystemVoiceError(f"Unknown preset voice: {voice_id}")

    directory = Path(root) / "system-voices" / voice_id
    reference = directory / "reference.wav"
    metadata = directory / "metadata.json"
    if reference.is_file() and metadata.is_file():
        return reference, spec

    directory.mkdir(parents=True, exist_ok=True)
    try:
        directory.parent.chmod(0o700)
        directory.chmod(0o700)
    except OSError:
        pass

    payload, resolved_url = _download(spec)
    fd, temp_name = tempfile.mkstemp(prefix="reference-", suffix=".wav", dir=directory)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            temp_path.chmod(0o600)
        except OSError:
            pass
        temp_path.replace(reference)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)

    metadata_payload = asdict(spec)
    metadata_payload.update(
        {
            "backend": DEFAULT_BACKEND,
            "reference_audio": "reference.wav",
            "resolved_reference_url": resolved_url,
            "source_note": (
                "CMU ARCTIC BDL and SLT are licensed US English speech recordings. "
                "Lectra uses this clip only as a local Chatterbox reference prompt."
            ),
        }
    )
    metadata.write_text(
        json.dumps(metadata_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        reference.chmod(0o600)
        metadata.chmod(0o600)
    except OSError:
        pass
    return reference, spec
