import numpy as np
import pyloudnorm as pyln
from pydub import AudioSegment
from io import BytesIO

def measure_loudness(audio: AudioSegment) -> float:
    """Measures the integrated loudness of an AudioSegment in LUFS."""
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    samples = samples / np.iinfo(np.int16).max
    meter = pyln.Meter(audio.frame_rate)
    return meter.integrated_loudness(samples)

def normalize_loudness(wav_bytes: bytes, target_lufs: float = -20.0) -> bytes:
    """
    Normalizes the loudness of a WAV file to a target LUFS, caps the peak,
    and converts to stereo.
    """
    if not wav_bytes:
        return b''

    try:
        audio = AudioSegment.from_wav(BytesIO(wav_bytes))

        # Measure loudness
        loudness = measure_loudness(audio)

        # Calculate gain for LUFS normalization
        gain_db = target_lufs - loudness
        normalized_audio = audio.apply_gain(gain_db)

        # Cap the peak at -3.0 dBFS
        if normalized_audio.max_dBFS > -3.0:
            peak_reduction = -3.0 - normalized_audio.max_dBFS
            normalized_audio = normalized_audio.apply_gain(peak_reduction)

        # Convert to stereo
        stereo_audio = normalized_audio.set_channels(2)

        # Export to bytes
        output_buffer = BytesIO()
        stereo_audio.export(output_buffer, format="wav")

        return output_buffer.getvalue()
    except Exception as e:
        print(f"Error during loudness normalization: {e}")
        return wav_bytes  # Return original bytes if normalization fails
