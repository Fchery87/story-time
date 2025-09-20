import logging
from abc import ABC, abstractmethod
from io import BytesIO

from pydub import AudioSegment

logger = logging.getLogger(__name__)


class TTSEngine(ABC):
    def __init__(self):
        # Engines can override if they need specific initialization
        pass

    @property
    def is_raw_output(self) -> bool:
        """Indicates if the synthesis output is raw PCM data."""
        return False

    @property
    def sample_rate(self) -> int:
        """The sample rate of the synthesized audio when output is raw."""
        return 22050  # A common default

    @abstractmethod
    def _synthesize_chunk(self, text: str) -> bytes:
        """Synthesizes a single chunk of text and returns the audio bytes."""
        pass

    def synth_to_wav_bytes(self, text: str) -> bytes:
        """
        Synthesizes text to 16-bit PCM WAV bytes.

        The engine is expected to handle the provided text as a single chunk.
        Higher-level chunking should be performed by the pipeline layer.
        """
        if not text or not text.strip():
            return b""

        audio_bytes = self._synthesize_chunk(text)

        if not audio_bytes:
            return b""

        try:
            if self.is_raw_output:
                audio = AudioSegment.from_raw(
                    BytesIO(audio_bytes),
                    sample_width=2,  # 16-bit
                    frame_rate=self.sample_rate,
                    channels=1,
                )
            else:
                audio = AudioSegment.from_wav(BytesIO(audio_bytes))

            # Export the audio to a WAV byte string
            output_buffer = BytesIO()
            audio.export(output_buffer, format="wav")
            return output_buffer.getvalue()
        except Exception:
            logger.exception("Could not process audio from engine output")
            return b""
