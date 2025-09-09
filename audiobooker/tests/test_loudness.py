import unittest
import numpy as np
import pyloudnorm as pyln
from pydub import AudioSegment
from io import BytesIO
import tempfile
import os
from audiobooker.pipeline.loudness import normalize_loudness

class TestLoudness(unittest.TestCase):
    def setUp(self):
        # Create a dummy WAV file on disk
        self.sample_rate = 16000
        duration_s = 2
        frequency = 440
        t = np.linspace(0., duration_s, int(self.sample_rate * duration_s))
        amplitude = np.iinfo(np.int16).max * 0.5
        data = amplitude * np.sin(2. * np.pi * frequency * t)

        audio = AudioSegment(
            data.astype("int16").tobytes(),
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
        target_lufs = -23.0
        normalized_bytes = normalize_loudness(wav_bytes, target_lufs)

        # Measure the loudness of the normalized audio
        normalized_audio = AudioSegment.from_wav(BytesIO(normalized_bytes))
        normalized_samples = np.array(normalized_audio.get_array_of_samples()).astype(np.float32)
        normalized_samples = normalized_samples / np.iinfo(np.int16).max

        meter = pyln.Meter(normalized_audio.frame_rate)
        measured_lufs = meter.integrated_loudness(normalized_samples)

        # Assert that the measured loudness is close to the target
        self.assertAlmostEqual(target_lufs, measured_lufs, delta=1.0)

if __name__ == '__main__':
    unittest.main()
