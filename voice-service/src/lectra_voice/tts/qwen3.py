from __future__ import annotations

from pathlib import Path

import numpy as np

from .base import AudioChunk, BackendCapabilities, SynthesisRequest, TTSBackend


_LANGUAGE_MAP = {
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "de": "German",
    "fr": "French",
    "ru": "Russian",
    "pt": "Portuguese",
    "es": "Spanish",
    "it": "Italian",
}


class Qwen3TTSBackend(TTSBackend):
    """Local Qwen3-TTS Base voice-cloning adapter.

    Qwen3 Base voice cloning uses reference audio plus its transcript for the
    highest-quality ICL path. `x_vector_only=True` permits transcript-free
    cloning at a likely quality cost.
    """

    name = "qwen3"
    capabilities = BackendCapabilities(
        voice_cloning=True,
        pace_control=False,
        tone_control=False,
        multilingual=True,
        requires_reference_text=True,
    )

    def __init__(
        self,
        *,
        model_id: str = "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device: str = "auto",
        flash_attention: bool = False,
        x_vector_only: bool = False,
    ) -> None:
        try:
            import torch
            from qwen_tts import Qwen3TTSModel
        except ImportError as exc:
            raise RuntimeError(
                "Qwen3-TTS is not installed. Install this project in a dedicated "
                "environment with: pip install -e '.[qwen3]'"
            ) from exc

        cuda_available = torch.cuda.is_available()

        if device == "auto":
            if not cuda_available:
                raise RuntimeError(
                    "CUDA is not available to PyTorch. Lectra will not silently fall back "
                    "to CPU for Qwen3-TTS because generation can become extremely slow. "
                    "Check the NVIDIA driver/PyTorch CUDA compatibility, or explicitly "
                    "pass --device cpu if CPU generation is intentional."
                )
            device = "cuda:0"
        elif device == "cuda":
            device = "cuda:0"

        if device.startswith("cuda") and not cuda_available:
            raise RuntimeError(
                f"Requested device '{device}', but CUDA is not available to PyTorch. "
                "Check the NVIDIA driver and the CUDA version used by the installed "
                "PyTorch build."
            )

        if device.startswith("cuda"):
            dtype = torch.bfloat16
        else:
            dtype = torch.float32

        load_kwargs: dict[str, object] = {
            "device_map": device,
            "dtype": dtype,
        }
        if flash_attention:
            load_kwargs["attn_implementation"] = "flash_attention_2"

        self.model_id = model_id
        self.device = device
        self.x_vector_only = x_vector_only
        self._model = Qwen3TTSModel.from_pretrained(model_id, **load_kwargs)
        self._prompt_cache: dict[tuple[str, str | None, bool], object] = {}

    @staticmethod
    def _language_name(language: str) -> str:
        primary = language.split("-", 1)[0].lower()
        try:
            return _LANGUAGE_MAP[primary]
        except KeyError as exc:
            supported = ", ".join(sorted(_LANGUAGE_MAP))
            raise ValueError(
                f"Qwen3-TTS language '{language}' is not mapped by Lectra. "
                f"Mapped primary tags: {supported}."
            ) from exc

    def _get_prompt(self, reference_audio: Path, reference_text: str | None) -> object:
        key = (str(reference_audio.resolve()), reference_text, self.x_vector_only)
        if key in self._prompt_cache:
            return self._prompt_cache[key]

        if not self.x_vector_only and not reference_text:
            raise ValueError(
                "Qwen3-TTS voice cloning requires --reference-text unless "
                "--qwen-x-vector-only is explicitly enabled."
            )

        prompt = self._model.create_voice_clone_prompt(
            ref_audio=str(reference_audio),
            ref_text=reference_text,
            x_vector_only_mode=self.x_vector_only,
        )
        self._prompt_cache[key] = prompt
        return prompt

    def synthesize(self, request: SynthesisRequest) -> AudioChunk:
        prompt = self._get_prompt(request.reference_audio, request.reference_text)
        wavs, sample_rate = self._model.generate_voice_clone(
            text=request.text,
            language=self._language_name(request.language),
            voice_clone_prompt=prompt,
            # Qwen3-TTS currently defaults this to False, which simulates
            # streaming text input and can cause speaking-rate drift in offline
            # generation. Lectra is an offline presentation renderer, so use the
            # full-text prompt layout explicitly for more stable delivery.
            non_streaming_mode=True,
        )
        return AudioChunk(
            samples=np.asarray(wavs[0]),
            sample_rate=int(sample_rate),
            metadata={
                "backend": self.name,
                "model_id": self.model_id,
                "pace_honored": False,
                "tone_honored": False,
                "non_streaming_mode": True,
            },
        )
