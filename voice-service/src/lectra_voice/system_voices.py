from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from .tts import DEFAULT_BACKEND


MAX_PRESET_DOWNLOAD_BYTES = 20 * 1024 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 45.0


@dataclass(frozen=True)
class SystemVoiceSpec:
    voice_id: str
    display_name: str
    gender: str
    accent: str
    source_speaker: str
    reference_url: str
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
            "https://festvox.org/cmu_arctic/cmu_arctic/"
            "cmu_us_slt_arctic/wav/arctic_a0001.wav"
        ),
        source_homepage="https://www.festvox.org/cmu_arctic/",
    ),
    "us-man": SystemVoiceSpec(
        voice_id="us-man",
        display_name="US Man",
        gender="male",
        accent="US English",
        source_speaker="CMU ARCTIC BDL",
        reference_url=(
            "https://festvox.org/cmu_arctic/cmu_arctic/"
            "cmu_us_bdl_arctic/wav/arctic_a0001.wav"
        ),
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


def _download(reference_url: str) -> bytes:
    request = urllib.request.Request(
        reference_url,
        headers={"User-Agent": "Lectra preset-voice downloader"},
    )
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            payload = response.read(MAX_PRESET_DOWNLOAD_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SystemVoiceError(
            "Could not download the preset voice reference clip. "
            "Check internet access and try again, or use /setupvoice."
        ) from exc

    if len(payload) > MAX_PRESET_DOWNLOAD_BYTES:
        raise SystemVoiceError("Preset voice reference clip exceeded the safety size limit.")
    if not _looks_like_wav(payload):
        raise SystemVoiceError("Preset voice download was not a valid WAV file.")
    return payload


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

    payload = _download(spec.reference_url)
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
