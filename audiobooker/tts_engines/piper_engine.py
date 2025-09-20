import json
import logging
import os
import shutil
import subprocess
from typing import Optional

from .base import TTSEngine

logger = logging.getLogger(__name__)


class PiperEngine(TTSEngine):
    def __init__(self, model_path: Optional[str] = None):
        super().__init__()
        self.piper_executable = shutil.which("piper")
        if not self.piper_executable:
            raise RuntimeError("Piper TTS executable not found. Please ensure 'piper' is in your PATH.")

        # Resolve model path from param or environment
        self.model_path = model_path or os.environ.get("PIPER_VOICE_PATH")
        if not self.model_path or not os.path.exists(self.model_path):
            raise RuntimeError(
                f"Piper model not found at path: {self.model_path}. Please set the PIPER_VOICE_PATH environment variable or pass a model_path."
            )

        # Load the model's config file
        self._load_model_config(self.model_path)

        # Optional synthesis parameters
        self.length_scale: Optional[float] = None
        self.noise_scale: Optional[float] = None
        self.noise_w: Optional[float] = None

    def _load_model_config(self, model_path: str) -> None:
        config_path = model_path + ".json"
        if not os.path.exists(config_path):
            raise RuntimeError(f"Piper model config not found at path: {config_path}")

        with open(config_path, "r") as f:
            self.config = json.load(f)

        self._sample_rate = self.config.get("audio", {}).get("sample_rate", 22050)

    def update_params(
        self,
        *,
        length_scale: Optional[float] = None,
        noise_scale: Optional[float] = None,
        noise_w: Optional[float] = None,
        model_path: Optional[str] = None,
    ) -> None:
        """Update runtime parameters for synthesis."""
        if model_path and model_path != self.model_path:
            if not os.path.exists(model_path):
                raise RuntimeError(f"Piper model not found at path: {model_path}")
            self.model_path = model_path
            self._load_model_config(self.model_path)

        if length_scale is not None:
            self.length_scale = float(length_scale)
        if noise_scale is not None:
            self.noise_scale = float(noise_scale)
        if noise_w is not None:
            self.noise_w = float(noise_w)

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
        command = [self.piper_executable, "--model", self.model_path, "--output_raw"]

        # Optional parameters
        if self.length_scale is not None:
            command += ["--length_scale", str(self.length_scale)]
        if self.noise_scale is not None:
            command += ["--noise_scale", str(self.noise_scale)]
        if self.noise_w is not None:
            command += ["--noise_w", str(self.noise_w)]

        try:
            process = subprocess.run(
                command,
                input=text.encode("utf-8"),
                capture_output=True,
                check=True,
                text=False,
            )
            return process.stdout
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="ignore") if e.stderr else ""
            logger.error("Error running Piper: %s", stderr)
            return b""
