import os
import tempfile
from io import BytesIO
from unittest.mock import patch

from pydub import AudioSegment
from pydub.generators import Sine

from audiobooker.cli import run_cli


def _to_wav_bytes(seg: AudioSegment) -> bytes:
    buf = BytesIO()
    seg.export(buf, format="wav")
    return buf.getvalue()


class DummyEngineTrim:
    model_name = "dummy-trim"

    def update_params(self, **kwargs):
        pass

    def synth_to_wav_bytes(self, text: str) -> bytes:
        # 200ms silence + 500ms tone + 200ms silence = 900ms
        sr = 44100
        tone = Sine(440, sample_rate=sr).to_audio_segment(duration=500).apply_gain(-3)
        audio = AudioSegment.silent(duration=200, frame_rate=sr) + tone + AudioSegment.silent(
            duration=200, frame_rate=sr
        )
        return _to_wav_bytes(audio.set_channels(2).set_frame_rate(44100))


class DummyEngineFade:
    model_name = "dummy-fade"

    def update_params(self, **kwargs):
        pass

    def synth_to_wav_bytes(self, text: str) -> bytes:
        # 600ms constant tone, no silence
        sr = 44100
        tone = Sine(440, sample_rate=sr).to_audio_segment(duration=600).apply_gain(-3)
        return _to_wav_bytes(tone.set_channels(2).set_frame_rate(44100))


class DummyEngineCompress:
    model_name = "dummy-compress"

    def update_params(self, **kwargs):
        pass

    def synth_to_wav_bytes(self, text: str) -> bytes:
        # 500ms quiet (-15 dB) + 500ms loud (0 dB)
        sr = 44100
        quiet = Sine(440, sample_rate=sr).to_audio_segment(duration=500).apply_gain(-15)
        loud = Sine(440, sample_rate=sr).to_audio_segment(duration=500).apply_gain(0)
        audio = quiet + loud
        return _to_wav_bytes(audio.set_channels(2).set_frame_rate(44100))


def _make_input_txt() -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    with open(tmp.name, "w", encoding="utf-8") as f:
        f.write("Chapter 1\nHello world. This is a test.")
    return tmp.name


def test_cli_trim_silence_reduces_length():
    inp = _make_input_txt()
    try:
        # Without trimming
        with patch("audiobooker.cli._init_engines", new=lambda: ({"piper": DummyEngineTrim()}, [])):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out1:
                rc1 = run_cli(
                    input_path=inp,
                    engine_name="piper",
                    output_path=out1.name,
                    max_chars=10000,
                    silence_between_chapters_ms=0,
                )
            assert rc1 == 0
            a1 = AudioSegment.from_wav(out1.name)

        # With trimming
        with patch("audiobooker.cli._init_engines", new=lambda: ({"piper": DummyEngineTrim()}, [])):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out2:
                rc2 = run_cli(
                    input_path=inp,
                    engine_name="piper",
                    output_path=out2.name,
                    max_chars=10000,
                    silence_between_chapters_ms=0,
                    enable_trim=True,
                )
            assert rc2 == 0
            a2 = AudioSegment.from_wav(out2.name)

        # Expect trimmed audio to be shorter by at least ~150ms (padding remains)
        assert len(a1) - len(a2) >= 150
    finally:
        try:
            os.remove(inp)
        except Exception:
            pass


def test_cli_fade_ms_lowers_start_level():
    inp = _make_input_txt()
    try:
        with patch("audiobooker.cli._init_engines", new=lambda: ({"piper": DummyEngineFade()}, [])):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as outp:
                rc = run_cli(
                    input_path=inp,
                    engine_name="piper",
                    output_path=outp.name,
                    max_chars=10000,
                    silence_between_chapters_ms=0,
                    fade_ms=100,
                )
            assert rc == 0
            a = AudioSegment.from_wav(outp.name)

        head = a[:30]
        mid = a[300:330]
        # Head should be at least a few dB lower than mid due to fade-in
        assert head.dBFS < mid.dBFS - 2.0
    finally:
        try:
            os.remove(inp)
        except Exception:
            pass


def test_cli_compress_reduces_dynamic_range():
    inp = _make_input_txt()
    try:
        # Without compression
        with patch("audiobooker.cli._init_engines", new=lambda: ({"piper": DummyEngineCompress()}, [])):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out1:
                rc1 = run_cli(
                    input_path=inp,
                    engine_name="piper",
                    output_path=out1.name,
                    max_chars=10000,
                    silence_between_chapters_ms=0,
                )
            assert rc1 == 0
            a1 = AudioSegment.from_wav(out1.name)

        # With compression
        with patch("audiobooker.cli._init_engines", new=lambda: ({"piper": DummyEngineCompress()}, [])):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out2:
                rc2 = run_cli(
                    input_path=inp,
                    engine_name="piper",
                    output_path=out2.name,
                    max_chars=10000,
                    silence_between_chapters_ms=0,
                    enable_compress=True,
                )
            assert rc2 == 0
            a2 = AudioSegment.from_wav(out2.name)

        # Measure dBFS of first half (quiet) vs second half (loud)
        a1_q = a1[:300]
        a1_l = a1[-300:]
        a2_q = a2[:300]
        a2_l = a2[-300:]

        diff_before = a1_l.dBFS - a1_q.dBFS
        diff_after = a2_l.dBFS - a2_q.dBFS
        # Compression should reduce the dynamic range
        assert diff_after < diff_before - 1.0
    finally:
        try:
            os.remove(inp)
        except Exception:
            pass