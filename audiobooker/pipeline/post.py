import logging
from io import BytesIO

from pydub import AudioSegment

logger = logging.getLogger(__name__)


def add_silence(wav_bytes: bytes, duration_ms: int) -> bytes:
    """
    Adds silence to the end of a WAV audio segment.
    """
    if not wav_bytes:
        return b""

    try:
        audio = AudioSegment.from_wav(BytesIO(wav_bytes))
        silence = AudioSegment.silent(duration=duration_ms)

        processed_audio = audio + silence

        output_buffer = BytesIO()
        processed_audio.export(output_buffer, format="wav")

        return output_buffer.getvalue()
    except Exception:
        logger.exception("Error adding silence")
        return wav_bytes
