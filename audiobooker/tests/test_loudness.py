import unittest
import numpy as np
from pydub import AudioSegment
from io import BytesIO
import tempfile
import os
from audiobooker.pipeline.loudness import normalize_loudness, measure_loudness

class TestLoudness(unittest.TestCase):
    def setUp(self):
        # Create a dummy white noise WAV file on disk
        self.sample_rate = 16000
        duration_s = 2
        # Generate white noise
        num_samples = int(self.sample_rate * duration_s)
        samples = np.random.uniform(low=-1.0, high=1.0, size=num_samples)
        # Scale to 16-bit integer range
        samples = (samples * np.iinfo(np.int16).max).astype(np.int16)

        audio = AudioSegment(
            samples.tobytes(),
            frame_rate=self.sample_rate,
            sample_width=2,
            channels=1
        )

        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        audio.export(self.temp_file.name, format="wav")

    def tearDown(self):
        os.remove(self.temp_file.name)

    def test_normalize_loudness(self):
        # Read the WAV file bytes
        with open(self.temp_file.name, 'rb') as f:
            wav_bytes = f.read()

        # Normalize the loudness
        target_lufs = -20.0
        normalized_bytes = normalize_loudness(wav_bytes, target_lufs)

        # Load the normalized audio
        normalized_audio = AudioSegment.from_wav(BytesIO(normalized_bytes))

        # 1. Test loudness
        measured_lufs = measure_loudness(normalized_audio)
        self.assertAlmostEqual(target_lufs, measured_lufs, delta=1.0)

        # 2. Test peak capping
        self.assertLessEqual(normalized_audio.max_dBFS, -3.0)

        # 3. Test stereo conversion
        self.assertEqual(normalized_audio.channels, 2)

if __name__ == '__main__':
    unittest.main()
