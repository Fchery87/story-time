import numpy as np
import pyloudnorm as pyln
from pydub import AudioSegment
from io import BytesIO

def normalize_loudness(wav_bytes: bytes, target_lufs: float = -20.0) -> bytes:
    """
    Normalizes the loudness of a WAV file to a target LUFS.
    """
    if not wav_bytes:
        return b''

    try:
        # Load the audio data
        audio = AudioSegment.from_wav(BytesIO(wav_bytes))

        # Convert to a numpy array and normalize to the range [-1.0, 1.0]
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        samples = samples / np.iinfo(np.int16).max

        # Create a loudness meter
        meter = pyln.Meter(audio.frame_rate)

        # Measure the loudness
        loudness = meter.integrated_loudness(samples)

        # Calculate the gain needed to reach the target loudness
        gain_db = target_lufs - loudness

        # Apply the gain using pydub
        normalized_audio = audio.apply_gain(gain_db)

        # Export the normalized audio to bytes
        output_buffer = BytesIO()
        normalized_audio.export(output_buffer, format="wav")

        return output_buffer.getvalue()
    except Exception as e:
        print(f"Error during loudness normalization: {e}")
        return wav_bytes  # Return original bytes if normalization fails
