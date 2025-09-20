import os
import tempfile
from io import BytesIO

import numpy as np
from pydub import AudioSegment

from audiobooker.pipeline.export import export_audiobook


def _gen_wav_bytes(seconds: float = 0.2, sr: int = 16000) -> bytes:
    num_samples = int(seconds * sr)
    samples = (np.random.uniform(-1.0, 1.0, num_samples) * np.iinfo(np.int16).max).astype(np.int16)
    audio = AudioSegment(samples.tobytes(), frame_rate=sr, sample_width=2, channels=1)
    buf = BytesIO()
    audio.export(buf, format="wav")
    return buf.getvalue()


def test_export_audiobook_wav():
    wav1 = _gen_wav_bytes()
    wav2 = _gen_wav_bytes()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out_path = tmp.name

    try:
        export_audiobook([wav1, wav2], out_path)
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 0
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)