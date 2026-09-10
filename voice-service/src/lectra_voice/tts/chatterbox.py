from __future__ import annotations

import numpy as np

from .base import AudioChunk, BackendCapabilities, SynthesisRequest, TTSBackend


_TONE_SETTINGS: dict[str, tuple[float, float]] = {
    "explanatory": (0.35, 0.50),
    "serious": (0.25, 0.55),
    "enthusiastic": (0.60, 0.40),
    "reflective": (0.30, 0.40),
}


class ChatterboxTTSBackend(TTSBackend):
    """Local Resemble AI Chatterbox voice-cloning adapter.

    Uses the original English Chatterbox model because it exposes CFG and
    exaggeration controls. Lectra maps its small tone vocabulary to conservative
    settings. Pace remains a neutral Lectra control for a later audio stage.
    """

    name = "chatterbox"
    capabilities = BackendCapabilities(
        voice_cloning=True,
        pace_control=False,
        tone_control=True,
        multilingual=False,
        requires_reference_text=False,
    )

    def __init__(self, *, device: str = "auto") -> None:
        try:
            import torch
            from chatterbox.tts import ChatterboxTTS
        except ImportError as exc:
            raise RuntimeError(
                "Chatterbox is not installed. Install this project in a dedicated "
                "environment with: pip install -e '.[chatterbox]'"
            ) from exc

        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"

        self.device = device
        self._model = ChatterboxTTS.from_pretrained(device=device)

    def synthesize(self, request: SynthesisRequest) -> AudioChunk:
        if request.language.split("-", 1)[0].lower() != "en":
            raise ValueError(
                "The initial Lectra Chatterbox adapter uses the English model. "
                "Use Qwen3-TTS for this bake-off or add the multilingual adapter later."
            )

        exaggeration, cfg_weight = _TONE_SETTINGS[request.tone]
        wav = self._model.generate(
            request.text,
            audio_prompt_path=str(request.reference_audio),
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
        )
        if hasattr(wav, "detach"):
            wav = wav.detach().cpu().numpy()

        return AudioChunk(
            samples=np.asarray(wav),
            sample_rate=int(self._model.sr),
            metadata={
                "backend": self.name,
                "exaggeration": exaggeration,
                "cfg_weight": cfg_weight,
                "pace_honored": False,
                "tone_honored": True,
            },
        )
