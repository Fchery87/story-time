import pyttsx3
import tempfile
import os
from .base import TTSEngine

class Pyttsx3Engine(TTSEngine):
    def __init__(self):
        super().__init__()
        self.engine = pyttsx3.init()

    def _synthesize_chunk(self, text: str) -> bytes:
        """
        Synthesizes a single chunk of text using pyttsx3 and returns the
        WAV bytes.
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
            temp_filename = temp_audio_file.name

        try:
            self.engine.save_to_file(text, temp_filename)
            self.engine.runAndWait()

            with open(temp_filename, 'rb') as f:
                wav_bytes = f.read()
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

        return wav_bytes
