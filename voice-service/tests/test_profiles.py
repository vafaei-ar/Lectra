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
