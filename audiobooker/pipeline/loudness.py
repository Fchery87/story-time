import logging
from io import BytesIO

import numpy as np
import pyloudnorm as pyln
from pydub import AudioSegment

logger = logging.getLogger(__name__)


def measure_loudness(audio: AudioSegment) -> float:
    """Measures the integrated loudness of an AudioSegment in LUFS."""
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    samples = samples / np.iinfo(np.int16).max
    meter = pyln.Meter(audio.frame_rate)
    return meter.integrated_loudness(samples)


def normalize_loudness(
    wav_bytes: bytes,
    target_lufs: float = -20.0,
    peak_dbfs: float = -3.0,
    target_sample_rate: int = 44100,
) -> bytes:
    """
    Normalizes the loudness of a WAV file to a target LUFS, caps the peak,
    and converts to a canonical format (stereo, 16-bit, target_sample_rate).
    """
    if not wav_bytes:
        return b""

    try:
        audio = AudioSegment.from_wav(BytesIO(wav_bytes))

        # Measure loudness
        loudness = measure_loudness(audio)

        # Calculate gain for LUFS normalization
        gain_db = target_lufs - loudness
        normalized_audio = audio.apply_gain(gain_db)

        # Cap the peak
        if normalized_audio.max_dBFS > peak_dbfs:
            peak_reduction = peak_dbfs - normalized_audio.max_dBFS
            normalized_audio = normalized_audio.apply_gain(peak_reduction)

        # Convert to canonical format
        canonical_audio = (
            normalized_audio.set_channels(2)
            .set_frame_rate(target_sample_rate)
            .set_sample_width(2)  # 16-bit
        )

        # Export to bytes
        output_buffer = BytesIO()
        canonical_audio.export(output_buffer, format="wav")

        return output_buffer.getvalue()
    except Exception:
        logger.exception("Error during loudness normalization")
        return wav_bytes  # Return original bytes if normalization fails
