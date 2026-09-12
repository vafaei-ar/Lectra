from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .tts import DEFAULT_BACKEND


_VOICE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class VoiceProfileError(RuntimeError):
    pass


class ConsentRequiredError(VoiceProfileError):
    pass


@dataclass(frozen=True)
class VoiceRecord:
    user_id: int
    voice_id: str
    reference_audio: Path
    created_at: str
    consent_confirmed: bool
    backend: str
    reference_text: str | None = None


class VoiceStore:
    def __init__(self, root: Path | str | None = None) -> None:
        if root is None:
            root = os.getenv("LECTRA_DATA_DIR", "~/.local/share/lectra")
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass

    @staticmethod
    def _validate_user_id(user_id: int) -> int:
        if not isinstance(user_id, int) or user_id <= 0:
            raise VoiceProfileError("Telegram user_id must be a positive integer.")
        return user_id

    @staticmethod
    def _validate_voice_id(voice_id: str) -> str:
        if not _VOICE_ID_RE.fullmatch(voice_id):
            raise VoiceProfileError(
                "voice_id must contain only letters, numbers, underscore, or hyphen "
                "and be 1-64 characters long."
            )
        return voice_id

    def user_dir(self, user_id: int) -> Path:
        user_id = self._validate_user_id(user_id)
        return self.root / "users" / str(user_id)

    def voice_dir(self, user_id: int, voice_id: str) -> Path:
        voice_id = self._validate_voice_id(voice_id)
        return self.user_dir(user_id) / "voices" / voice_id

    def _profile_path(self, user_id: int) -> Path:
        return self.user_dir(user_id) / "profile.json"

    @staticmethod
    def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            tmp.chmod(0o600)
        except OSError:
            pass
        tmp.replace(path)

    def _read_user_profile(self, user_id: int) -> dict[str, object]:
        path = self._profile_path(user_id)
        if not path.is_file():
            return {"telegram_user_id": user_id, "default_voice": None}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise VoiceProfileError(f"Could not read user profile: {path}") from exc

    def save_voice(
        self,
        *,
        user_id: int,
        source_wav: Path,
        voice_id: str = "default",
        consent_confirmed: bool,
        reference_text: str | None = None,
        backend: str = DEFAULT_BACKEND,
    ) -> VoiceRecord:
        user_id = self._validate_user_id(user_id)
        voice_id = self._validate_voice_id(voice_id)
        if not consent_confirmed:
            raise ConsentRequiredError(
                "Voice enrollment requires confirmation that the recording is the user's "
                "own voice or is used with the speaker's permission."
            )
        source_wav = Path(source_wav)
        if not source_wav.is_file():
            raise VoiceProfileError(f"Reference WAV does not exist: {source_wav}")

        directory = self.voice_dir(user_id, voice_id)
        directory.mkdir(parents=True, exist_ok=True)
        try:
            self.user_dir(user_id).chmod(0o700)
            directory.parent.chmod(0o700)
            directory.chmod(0o700)
        except OSError:
            pass
        target = directory / "reference.wav"
        shutil.copy2(source_wav, target)
        try:
            target.chmod(0o600)
        except OSError:
            pass

        created_at = datetime.now(timezone.utc).isoformat()
        record = VoiceRecord(
            user_id=user_id,
            voice_id=voice_id,
            reference_audio=target,
            created_at=created_at,
            consent_confirmed=True,
            backend=backend,
            reference_text=reference_text,
        )
        metadata = asdict(record)
        metadata["reference_audio"] = "reference.wav"
        self._write_json_atomic(directory / "metadata.json", metadata)

        user_profile = self._read_user_profile(user_id)
        if not user_profile.get("default_voice"):
            user_profile["default_voice"] = voice_id
        user_profile["telegram_user_id"] = user_id
        self._write_json_atomic(self._profile_path(user_id), user_profile)
        return record

    def get_voice(self, user_id: int, voice_id: str | None = None) -> VoiceRecord:
        user_id = self._validate_user_id(user_id)
        if voice_id is None:
            voice_id = self.default_voice_id(user_id)
        if not voice_id:
            raise VoiceProfileError("No voice profile is configured for this user.")
        voice_id = self._validate_voice_id(voice_id)

        directory = self.voice_dir(user_id, voice_id)
        metadata_path = directory / "metadata.json"
        audio_path = directory / "reference.wav"
        if not metadata_path.is_file() or not audio_path.is_file():
            raise VoiceProfileError(f"Voice profile '{voice_id}' does not exist.")
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise VoiceProfileError(f"Could not read voice profile '{voice_id}'.") from exc

        return VoiceRecord(
            user_id=user_id,
            voice_id=voice_id,
            reference_audio=audio_path,
            created_at=str(metadata.get("created_at", "")),
            consent_confirmed=bool(metadata.get("consent_confirmed", False)),
            backend=str(metadata.get("backend", DEFAULT_BACKEND)),
            reference_text=(
                str(metadata["reference_text"])
                if metadata.get("reference_text") is not None
                else None
            ),
        )

    def list_voices(self, user_id: int) -> list[VoiceRecord]:
        user_id = self._validate_user_id(user_id)
        voices_dir = self.user_dir(user_id) / "voices"
        if not voices_dir.is_dir():
            return []
        records: list[VoiceRecord] = []
        for path in sorted(voices_dir.iterdir()):
            if not path.is_dir():
                continue
            try:
                records.append(self.get_voice(user_id, path.name))
            except VoiceProfileError:
                continue
        return records

    def default_voice_id(self, user_id: int) -> str | None:
        profile = self._read_user_profile(self._validate_user_id(user_id))
        voice_id = profile.get("default_voice")
        return str(voice_id) if voice_id else None

    def set_default_voice(self, user_id: int, voice_id: str) -> None:
        self.get_voice(user_id, voice_id)
        profile = self._read_user_profile(user_id)
        profile["telegram_user_id"] = user_id
        profile["default_voice"] = voice_id
        self._write_json_atomic(self._profile_path(user_id), profile)

    def delete_voice(self, user_id: int, voice_id: str) -> bool:
        user_id = self._validate_user_id(user_id)
        voice_id = self._validate_voice_id(voice_id)
        directory = self.voice_dir(user_id, voice_id)
        if not directory.exists():
            return False
        shutil.rmtree(directory)

        profile = self._read_user_profile(user_id)
        if profile.get("default_voice") == voice_id:
            remaining = self.list_voices(user_id)
            profile["default_voice"] = remaining[0].voice_id if remaining else None
        self._write_json_atomic(self._profile_path(user_id), profile)
        return True
