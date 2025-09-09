from abc import ABC, abstractmethod, abstractproperty
import nltk
from io import BytesIO
from pydub import AudioSegment

class TTSEngine(ABC):
    def __init__(self):
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')

    @property
    def is_raw_output(self) -> bool:
        """Indicates if the synthesis output is raw PCM data."""
        return False

    @property
    def sample_rate(self) -> int:
        """The sample rate of the synthesized audio."""
        return 22050  # A common default

    def chunk_text(self, text: str) -> list[str]:
        """Splits the text into sentences."""
        return nltk.sent_tokenize(text)

    @abstractmethod
    def _synthesize_chunk(self, text: str) -> bytes:
        """Synthesizes a single chunk of text and returns the audio bytes."""
        pass

    def synth_to_wav_bytes(self, text: str) -> bytes:
        """
        Synthesizes text to 16-bit PCM WAV bytes, handling long text by
        chunking.
        """
        chunks = self.chunk_text(text)

        if not chunks:
            return b''

        combined_audio = AudioSegment.empty()

        for chunk in chunks:
            if not chunk.strip():
                continue

            audio_bytes = self._synthesize_chunk(chunk)

            if not audio_bytes:
                continue

            try:
                if self.is_raw_output:
                    chunk_audio = AudioSegment.from_raw(
                        BytesIO(audio_bytes),
                        sample_width=2,  # 16-bit
                        frame_rate=self.sample_rate,
                        channels=1
                    )
                else:
                    chunk_audio = AudioSegment.from_wav(BytesIO(audio_bytes))

                combined_audio += chunk_audio
            except Exception as e:
                print(f"Could not process audio chunk: {e}")

        if len(combined_audio) == 0:
            return b''

        # Export the combined audio to a single WAV byte string
        output_buffer = BytesIO()
        combined_audio.export(output_buffer, format="wav")
        return output_buffer.getvalue()
