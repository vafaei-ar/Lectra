from lectra_voice.tts.qwen3 import Qwen3TTSBackend


def test_qwen_language_mapping_handles_bcp47():
    assert Qwen3TTSBackend._language_name("en-US") == "English"
    assert Qwen3TTSBackend._language_name("fr-CA") == "French"
