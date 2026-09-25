from pathlib import Path

import pytest

from lectra_voice.profiles import ConsentRequiredError, VoiceProfileError, VoiceStore


def _wav(tmp_path: Path, name: str = "source.wav") -> Path:
    path = tmp_path / name
    path.write_bytes(b"RIFF-placeholder")
    return path


def test_enrollment_requires_consent(tmp_path: Path):
    store = VoiceStore(tmp_path / "data")
    with pytest.raises(ConsentRequiredError):
        store.save_voice(
            user_id=123,
            source_wav=_wav(tmp_path),
            consent_confirmed=False,
        )


def test_save_list_default_and_delete(tmp_path: Path):
    store = VoiceStore(tmp_path / "data")
    store.save_voice(
        user_id=123,
        source_wav=_wav(tmp_path),
        voice_id="default",
        consent_confirmed=True,
        reference_text="hello",
    )
    record = store.get_voice(123)
    assert record.voice_id == "default"
    assert record.reference_audio.read_bytes() == b"RIFF-placeholder"
    assert record.reference_text == "hello"
    assert store.default_voice_id(123) == "default"
    assert [v.voice_id for v in store.list_voices(123)] == ["default"]
    assert store.delete_voice(123, "default") is True
    assert store.list_voices(123) == []
    assert store.default_voice_id(123) is None


def test_user_isolation(tmp_path: Path):
    store = VoiceStore(tmp_path / "data")
    store.save_voice(user_id=123, source_wav=_wav(tmp_path, "one.wav"), consent_confirmed=True)
    store.save_voice(user_id=456, source_wav=_wav(tmp_path, "two.wav"), consent_confirmed=True)
    assert store.get_voice(123).reference_audio != store.get_voice(456).reference_audio
    assert "/123/" in store.get_voice(123).reference_audio.as_posix()
    assert "/456/" in store.get_voice(456).reference_audio.as_posix()


def test_invalid_voice_id_is_rejected(tmp_path: Path):
    store = VoiceStore(tmp_path / "data")
    with pytest.raises(VoiceProfileError):
        store.voice_dir(123, "../../escape")


class _FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size: int = -1) -> bytes:
        return self.payload if size < 0 else self.payload[:size]


def _fake_wav_payload() -> bytes:
    return b"RIFF" + (b"\x00" * 4) + b"WAVE" + (b"\x00" * 64)


def test_system_preset_downloads_once_and_can_be_default(tmp_path: Path, monkeypatch):
    calls: list[str] = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        return _FakeResponse(_fake_wav_payload())

    monkeypatch.setattr("lectra_voice.system_voices.urllib.request.urlopen", fake_urlopen)

    store = VoiceStore(tmp_path / "data")
    store.set_default_voice(123, "us-woman")

    first = store.get_voice(123)
    second = store.get_voice(123)

    assert first.voice_id == "us-woman"
    assert first.reference_audio == second.reference_audio
    assert first.reference_audio.is_file()
    assert store.default_voice_id(123) == "us-woman"
    assert store.voice_display_name("us-woman") == "US Woman"
    assert len(calls) == 1


def test_system_preset_ids_are_reserved_for_personal_enrollment(tmp_path: Path):
    store = VoiceStore(tmp_path / "data")
    with pytest.raises(VoiceProfileError, match="reserved"):
        store.save_voice(
            user_id=123,
            source_wav=_wav(tmp_path),
            voice_id="us-man",
            consent_confirmed=True,
        )


def test_system_presets_cannot_be_deleted(tmp_path: Path):
    store = VoiceStore(tmp_path / "data")
    with pytest.raises(VoiceProfileError, match="cannot be deleted"):
        store.delete_voice(123, "us-woman")


def test_system_voice_catalog_has_us_man_and_woman(tmp_path: Path):
    store = VoiceStore(tmp_path / "data")
    specs = {spec.voice_id: spec for spec in store.system_voices()}
    assert specs["us-woman"].gender == "female"
    assert specs["us-woman"].accent == "US English"
    assert specs["us-man"].gender == "male"
    assert specs["us-man"].accent == "US English"
