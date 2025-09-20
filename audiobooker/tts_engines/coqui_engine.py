import logging
import os
import wave
from io import BytesIO
from typing import Optional

import torch
from TTS.api import TTS

from .base import TTSEngine

logger = logging.getLogger(__name__)


class CoquiEngine(TTSEngine):
    def __init__(self, model_name: Optional[str] = None):
        super().__init__()
        self.model_name = model_name or os.environ.get("COQUI_MODEL_NAME", "tts_models/en/ljspeech/vits")
        self._load_model(self.model_name)

    def _load_model(self, model_name: str) -> None:
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.tts = TTS(model_name).to(device)
            self.model_name = model_name
        except Exception as e:
            raise RuntimeError(f"Failed to load Coqui TTS model: {model_name}") from e

    def update_model(self, model_name: str) -> None:
        """Reload engine with a new model name."""
        self._load_model(model_name)

    def _synthesize_chunk(self, text: str) -> bytes:
        """
        Synthesizes a single chunk of text using Coqui TTS and returns the
        WAV bytes.
        """
        # Synthesize to a waveform
        wav_array = self.tts.tts(text)

        if not wav_array:
            return b""

        # Convert the waveform to bytes
        output_buffer = BytesIO()
        with wave.open(output_buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.tts.synthesizer.output_sample_rate)
            # Convert float waveform to 16-bit PCM
            import numpy as np

            pcm_data = (np.array(wav_array) * 32767).astype("<i2").tobytes()
            wf.writeframes(pcm_data)

        return output_buffer.getvalue()
