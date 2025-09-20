import logging
from io import BytesIO
from typing import Optional

from pydub import AudioSegment, effects

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


def _detect_leading_silence(sound: AudioSegment, silence_thresh: float = -40.0, chunk_size: int = 10) -> int:
    """
    Detects leading silence in ms.
    """
    trim_ms = 0  # ms
    while trim_ms < len(sound):
        seg = sound[trim_ms : trim_ms + chunk_size]
        if seg.dBFS > silence_thresh:
            break
        trim_ms += chunk_size
    return trim_ms


def trim_silence_segment(
    audio: AudioSegment,
    silence_thresh: float = -40.0,
    chunk_size: int = 10,
    padding_ms: int = 100,
) -> AudioSegment:
    """
    Trim leading and trailing silence, leaving small padding on both sides for naturalness.
    """
    try:
        start = _detect_leading_silence(audio, silence_thresh=silence_thresh, chunk_size=chunk_size)
        end = _detect_leading_silence(audio.reverse(), silence_thresh=silence_thresh, chunk_size=chunk_size)
        trimmed = audio[start : len(audio) - end if end > 0 else None]
        if start > 0 and padding_ms > 0:
            trimmed = AudioSegment.silent(duration=padding_ms) + trimmed
        if end > 0 and padding_ms > 0:
            trimmed = trimmed + AudioSegment.silent(duration=padding_ms)
        return trimmed
    except Exception:
        logger.exception("Error trimming silence; returning original audio")
        return audio


def compress_segment(
    audio: AudioSegment,
    threshold: float = -20.0,
    ratio: float = 2.0,
    attack: int = 5,
    release: int = 50,
) -> AudioSegment:
    """
    Apply dynamic range compression to the segment.
    """
    try:
        return effects.compress_dynamic_range(
            audio, threshold=threshold, ratio=ratio, attack=attack, release=release
        )
    except Exception:
        logger.exception("Error compressing audio; returning original")
        return audio


def apply_postprocessing(
    audio: AudioSegment,
    enable_compression: bool = False,
    enable_trim: bool = False,
    fade_ms: int = 0,
    *,
    compression_threshold: float = -20.0,
    compression_ratio: float = 2.0,
    trim_silence_thresh: float = -40.0,
    trim_chunk_size_ms: int = 10,
    trim_padding_ms: int = 100,
) -> AudioSegment:
    """
    Apply a set of optional postprocessing steps to an AudioSegment.
    """
    out = audio
    if enable_trim:
        out = trim_silence_segment(
            out, silence_thresh=trim_silence_thresh, chunk_size=trim_chunk_size_ms, padding_ms=trim_padding_ms
        )
    if enable_compression:
        out = compress_segment(out, threshold=compression_threshold, ratio=compression_ratio)
    if fade_ms and fade_ms > 0:
        try:
            out = out.fade_in(fade_ms).fade_out(fade_ms)
        except Exception:
            logger.exception("Error applying fades; skipping")
    return out
