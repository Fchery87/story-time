import os
import subprocess
import shutil
import json
from .base import TTSEngine

class PiperEngine(TTSEngine):
    def __init__(self):
        super().__init__()
        self.piper_executable = shutil.which("piper")
        if not self.piper_executable:
            raise RuntimeError("Piper TTS executable not found. Please ensure 'piper' is in your PATH.")

        self.model_path = os.environ.get("PIPER_VOICE_PATH")
        if not self.model_path or not os.path.exists(self.model_path):
            raise RuntimeError(f"Piper model not found at path: {self.model_path}. Please set the PIPER_VOICE_PATH environment variable.")

        # Load the model's config file
        config_path = self.model_path + ".json"
        if not os.path.exists(config_path):
            raise RuntimeError(f"Piper model config not found at path: {config_path}")

        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self._sample_rate = self.config.get("audio", {}).get("sample_rate", 22050)

    @property
    def is_raw_output(self) -> bool:
        return True

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def _synthesize_chunk(self, text: str) -> bytes:
        """
        Synthesizes a single chunk of text using the piper CLI and returns
        the raw PCM bytes.
        """
        command = [
            self.piper_executable,
            "--model", self.model_path,
            "--output_raw"
        ]

        try:
            process = subprocess.run(
                command,
                input=text.encode('utf-8'),
                capture_output=True,
                check=True,
                text=False
            )
            return process.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error running Piper: {e.stderr.decode('utf-8')}")
            return b''
