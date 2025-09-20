import argparse
import logging
import os
import sys
from io import BytesIO
from typing import List, Tuple

from pydub import AudioSegment

from pipeline.chunker import chunk
from pipeline.export import export_audio_file, export_chapters, export_m4b_with_chapters
from pipeline.loudness import normalize_loudness
from tts_engines.coqui_engine import CoquiEngine
from tts_engines.piper_engine import PiperEngine
from tts_engines.pyttsx3_engine import Pyttsx3Engine
from utils.book_loader import load_book
from utils.cache import clear_cache, get_from_cache, is_cache_enabled, make_cache_key, put_in_cache


def _init_engines():
    tts_engines = {}
    engine_errors = []

    try:
        tts_engines["pyttsx3"] = Pyttsx3Engine()
    except Exception as e:
        engine_errors.append(f"Failed to initialize pyttsx3: {e}")

    try:
        tts_engines["coqui"] = CoquiEngine()
    except Exception as e:
        engine_errors.append(f"Failed to initialize Coqui TTS: {e}")

    try:
        tts_engines["piper"] = PiperEngine()
    except Exception as e:
        engine_errors.append(f"Failed to initialize Piper TTS: {e}")

    return tts_engines, engine_errors


def _engine_variant(engine) -> str:
    return getattr(engine, "model_path", None) or getattr(engine, "model_name", None) or "default"


def _synthesize_with_cache(engine_name, engine, text_chunk: str) -> bytes:
    use_cache = is_cache_enabled()
    variant = _engine_variant(engine)
    key = make_cache_key(engine_name, variant, text_chunk)

    if use_cache:
        cached = get_from_cache(key)
        if cached:
            return cached

    wav_bytes = engine.synth_to_wav_bytes(text_chunk)

    if use_cache and wav_bytes:
        put_in_cache(key, wav_bytes)

    return wav_bytes


def _combine_wav_bytes_to_segment(wav_bytes_list: List[bytes]) -> AudioSegment:
    combined = AudioSegment.empty()
    for b in wav_bytes_list:
        if not b:
            continue
        seg = AudioSegment.from_wav(BytesIO(b))
        combined += seg
    return combined


def run_cli(
    input_path: str,
    engine_name: str,
    output_path: str,
    per_chapter_dir: str | None = None,
    title: str | None = None,
    author: str | None = None,
    max_chars: int = 1200,
    silence_between_chapters_ms: int = 1000,
    piper_length_scale: float | None = None,
    pyttsx3_rate: int | None = None,
) -> int:
    engines, errors = _init_engines()
    if errors:
        for e in errors:
            logging.warning("Engine error: %s", e)

    if engine_name not in engines:
        logging.error("Engine '%s' is not available. Available: %s", engine_name, ", ".join(engines.keys()))
        return 2

    engine = engines[engine_name]

    # Apply engine-specific params
    if engine_name == "piper" and piper_length_scale is not None:
        try:
            engine.update_params(length_scale=piper_length_scale)
        except Exception as e:
            logging.warning("Failed to apply Piper parameters: %s", e)
    if engine_name == "pyttsx3" and pyttsx3_rate is not None:
        try:
            engine.update_params(rate=pyttsx3_rate)
        except Exception as e:
            logging.warning("Failed to apply pyttsx3 parameters: %s", e)

    # Load book
    chapters: List[Tuple[str, str]] = load_book(input_path)
    if not chapters:
        logging.error("No chapters found in input.")
        return 3

    chapter_segments: List[AudioSegment] = []
    chapter_titles: List[str] = []

    for idx, (ch_title, ch_text) in enumerate(chapters, start=1):
        logging.info("Processing chapter %d/%d: %s", idx, len(chapters), ch_title)
        text_chunks = chunk(ch_text, max_chars=max_chars)
        wav_bytes_list: List[bytes] = []

        for j, text_chunk in enumerate(text_chunks, start=1):
            logging.info("  Synthesizing chunk %d/%d", j, len(text_chunks))
            wav_bytes = _synthesize_with_cache(engine_name, engine, text_chunk)
            wav_bytes = normalize_loudness(wav_bytes)
            wav_bytes_list.append(wav_bytes)

        chapter_audio = _combine_wav_bytes_to_segment(wav_bytes_list)
        chapter_segments.append(chapter_audio)
        chapter_titles.append(ch_title)

    # Build full audiobook
    full = AudioSegment.empty()
    for i, seg in enumerate(chapter_segments):
        full += seg
        if i != len(chapter_segments) - 1 and silence_between_chapters_ms > 0:
            full += AudioSegment.silent(duration=silence_between_chapters_ms)

    # Export chapters if requested
    if per_chapter_dir:
        logging.info("Exporting per-chapter files to %s", per_chapter_dir)
        export_chapters(
            chapter_segments,
            titles=chapter_titles,
            out_dir=per_chapter_dir,
            base_album=title or "Audiobook",
            base_artist=author or "Unknown",
            ext=output_path.split(".")[-1].lower(),
        )

    # Export full audiobook with metadata
    metadata = {
        "title": title or os.path.basename(output_path),
        "artist": author or "Unknown",
        "album": title or "Audiobook",
    }
    ext = output_path.split(".")[-1].lower()
    if ext == "m4b":
        ok = export_m4b_with_chapters(
            chapter_segments,
            titles=chapter_titles,
            output_path=output_path,
            chapter_silence_ms=silence_between_chapters_ms,
            metadata=metadata,
        )
        if not ok:
            logging.error("Failed exporting M4B with chapters")
            return 4
    else:
        export_audio_file(full, output_path, metadata=metadata)

    logging.info("Audiobook exported to %s", output_path)
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local Audiobook Generator CLI")
    parser.add_argument("input", help="Path to input book file (txt, md, epub, pdf)")
    parser.add_argument("-o", "--out", required=True, help="Output file path (e.g., out.m4b, out.mp3, out.wav)")
    parser.add_argument(
        "-e",
        "--engine",
        default="piper",
        choices=["pyttsx3", "coqui", "piper"],
        help="TTS engine to use",
    )
    parser.add_argument("--title", help="Title metadata for the audiobook")
    parser.add_argument("--author", help="Author/artist metadata for the audiobook")
    parser.add_argument("--per-chapter-dir", help="Output directory to also export per-chapter files")
    parser.add_argument(
        "--voice",
        help="Override voice/model for engine (currently used by Piper via PIPER_VOICE_PATH env var)",
    )
    parser.add_argument("--max-chars", type=int, default=1200, help="Chunk size for TTS synthesis")
    parser.add_argument(
        "--silence-between-chapters-ms",
        type=int,
        default=1000,
        help="Silence appended between chapters in the final output (ms)",
    )
    parser.add_argument(
        "--piper-length-scale",
        type=float,
        help="Piper length_scale (speed) parameter (e.g., 0.8 faster, 1.2 slower)",
    )
    parser.add_argument("--pyttsx3-rate", type=int, help="pyttsx3 speech rate (e.g., 200)")
    parser.add_argument("--clear-cache", action="store_true", help="Clear TTS synthesis cache and exit")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache for this run")

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    if args.clear_cache:
        clear_cache()
        logging.info("Cache cleared.")
        return 0

    if args.no_cache:
        os.environ["AUDIOBOOKER_CACHE_ENABLED"] = "0"

    if args.voice:
        os.environ["PIPER_VOICE_PATH"] = args.voice

    return run_cli(
        input_path=args.input,
        engine_name=args.engine,
        output_path=args.out,
        per_chapter_dir=args.per_chapter_dir,
        title=args.title,
        author=args.author,
        max_chars=args.max_chars,
        silence_between_chapters_ms=args.silence_between_chapters_ms,
        piper_length_scale=args.piper_length_scale,
        pyttsx3_rate=args.pyttsx3_rate,
    )


if __name__ == "__main__":
    import sys as _sys

    _sys.exit(main())