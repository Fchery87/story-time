import os
import torch
import wave
from io import BytesIO
from .base import TTSEngine
from TTS.api import TTS

class CoquiEngine(TTSEngine):
    def __init__(self):
        super().__init__()
        model_name = os.environ.get("COQUI_MODEL_NAME", "tts_models/en/ljspeech/vits")

        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.tts = TTS(model_name).to(device)
        except Exception as e:
            raise RuntimeError(f"Failed to load Coqui TTS model: {model_name}") from e

    def _synthesize_chunk(self, text: str) -> bytes:
        """
        Synthesizes a single chunk of text using Coqui TTS and returns the
        WAV bytes.
        """
        # Synthesize to a waveform
        wav_list = self.tts.tts(text)

        if not wav_list:
            return b''

        # Convert the waveform to bytes
        output_buffer = BytesIO()
        with wave.open(output_buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.tts.synthesizer.output_sample_rate)
            # Convert float waveform to 16-bit PCM
            pcm_data = (torch.tensor(wav_list) * 32767).to(torch.int16).numpy()
            wf.writeframes(pcm_data.tobytes())

        return output_buffer.getvalue()
