import logging
import os
import subprocess
import tempfile
from io import BytesIO
from typing import Iterable, Optional

from pydub import AudioSegment

logger = logging.getLogger(__name__)


def export_audiobook(chapter_audio_bytes: list[bytes], output_path: str):
    """
    Combines a list of chapter audio bytes into a single audiobook file.
    """
    if not chapter_audio_bytes:
        logger.warning("No chapters to export.")
        return

    # Combine all chapters into a single audio segment
    full_audiobook = AudioSegment.empty()
    for wav_bytes in chapter_audio_bytes:
        if wav_bytes:
            try:
                chapter_audio = AudioSegment.from_wav(BytesIO(wav_bytes))
                full_audiobook += chapter_audio
            except Exception:
                logger.exception("Could not process chapter for export")

    # Export the final audiobook
    if len(full_audiobook) > 0:
        try:
            # For now, we'll export as WAV. M4B would require more complex metadata handling.
            output_format = output_path.split(".")[-1].lower()
            if output_format not in ["wav", "mp3", "flac", "ogg", "m4a"]:
                logger.warning("Unsupported export format '%s', defaulting to 'wav'.", output_format)
                output_path += ".wav"
                output_format = "wav"

            full_audiobook.export(output_path, format=output_format)
            logger.info("Audiobook successfully exported to %s", output_path)
        except Exception:
            logger.exception("Error exporting audiobook")
    else:
        logger.warning("No audio data to export.")


def _determine_ffmpeg_format(ext: str) -> str:
    """Map file extension to pydub/ffmpeg format string."""
    ext = ext.lower()
    if ext in {"m4a", "m4b"}:
        return "mp4"
    return ext


def export_audio_file(audio: AudioSegment, output_path: str, metadata: Optional[dict] = None) -> None:
    """
    Export a single audio segment to the given path and optionally write metadata.
    """
    ext = output_path.split(".")[-1].lower()
    fmt = _determine_ffmpeg_format(ext)

    try:
        audio.export(output_path, format=fmt)
    except Exception:
        logger.exception("Failed exporting audio to %s", output_path)
        return

    if metadata and ext != "wav":
        try:
            _write_metadata(output_path, metadata)
        except Exception:
            logger.exception("Failed writing metadata to %s", output_path)


def export_chapters(
    chapter_audios: Iterable[AudioSegment],
    titles: Iterable[str],
    out_dir: str,
    base_album: Optional[str] = None,
    base_artist: Optional[str] = None,
    ext: str = "m4a",
):
    """
    Export chapters as individual files with basic metadata.
    """
    fmt = _determine_ffmpeg_format(ext)
    os.makedirs(out_dir, exist_ok=True)

    for idx, (audio, title) in enumerate(zip(chapter_audios, titles), start=1):
        safe_title = "".join(c for c in title if c not in "\\/:*?\"<>|").strip() or f"Chapter {idx:02d}"
        filename = f"{idx:02d} - {safe_title}.{ext}"
        out_path = os.path.join(out_dir, filename)
        try:
            audio.export(out_path, format=fmt)
            meta = {
                "title": title,
                "album": base_album or "Audiobook",
                "artist": base_artist or "Unknown",
                "tracknumber": str(idx),
            }
            if ext != "wav":
                _write_metadata(out_path, meta)
            logger.info("Exported chapter %s to %s", title, out_path)
        except Exception:
            logger.exception("Failed exporting chapter %s", title)


def concat_wav_files_ffmpeg(input_paths: list[str], output_path: str) -> bool:
    """
    Concatenate WAV files using ffmpeg concat demuxer with stream copy.
    Returns True on success.
    """
    if not input_paths:
        logger.warning("No input files to concatenate.")
        return False

    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    except Exception:
        pass

    # Create ffconcat list file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp_list:
        for p in input_paths:
            tmp_list.write(f"file '{p}'\n")
        list_path = tmp_list.name

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_path,
        "-c",
        "copy",
        output_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        ok = True
    except subprocess.CalledProcessError as e:
        logger.error("ffmpeg concat failed: %s", e.stderr.decode("utf-8", errors="ignore"))
        ok = False
    finally:
        try:
            os.remove(list_path)
        except Exception:
            pass

    if ok:
        logger.info("Concatenated %d files to %s", len(input_paths), output_path)
    return ok


def export_m4b_with_chapters(
    chapter_audios: Iterable[AudioSegment],
    titles: Iterable[str],
    output_path: str,
    chapter_silence_ms: int = 1000,
    metadata: Optional[dict] = None,
) -> bool:
    """
    Export an M4B (AAC/MP4) with embedded chapter markers using ffmpeg's ffmetadata.
    Returns True on success.
    """
    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    except Exception:
        pass

    titles = list(titles)
    audios = list(chapter_audios)
    if not audios:
        logger.warning("No chapter audio to export as m4b.")
        return False

    # Build concatenated audio and compute chapter offsets
    full = AudioSegment.empty()
    starts = []
    ends = []
    cursor = 0
    for i, seg in enumerate(audios):
        starts.append(cursor)
        cursor += len(seg)
        ends.append(cursor)
        if i != len(audios) - 1 and chapter_silence_ms > 0:
            silence = AudioSegment.silent(duration=chapter_silence_ms)
            full += seg + silence
            cursor += chapter_silence_ms
        else:
            full += seg

    # Export concatenated audio to a temporary m4a (mp4) file
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp_audio:
        tmp_audio_path = tmp_audio.name
    try:
        full.export(tmp_audio_path, format="mp4")
    except Exception:
        logger.exception("Failed exporting intermediate m4a for m4b creation")
        try:
            os.remove(tmp_audio_path)
        except Exception:
            pass
        return False

    # Build ffmetadata file content
    ffmeta_lines = [";FFMETADATA1"]
    ffmeta_lines.append("title=%s" % (metadata.get("title") if metadata else "Audiobook"))
    ffmeta_lines.append("artist=%s" % (metadata.get("artist") if metadata else "Unknown"))
    ffmeta_lines.append("album=%s" % (metadata.get("album") if metadata else "Audiobook"))

    for i, (start, end) in enumerate(zip(starts, ends), start=1):
        title = titles[i - 1] if i - 1 < len(titles) else f"Chapter {i}"
        ffmeta_lines.append("[CHAPTER]")
        ffmeta_lines.append("TIMEBASE=1/1000")
        ffmeta_lines.append(f"START={start}")
        ffmeta_lines.append(f"END={end}")
        ffmeta_lines.append(f"title={title}")

    with tempfile.NamedTemporaryFile(suffix=".ffmeta", mode="w", delete=False) as tmp_meta:
        tmp_meta.write("\n".join(ffmeta_lines))
        tmp_meta_path = tmp_meta.name

    # Use ffmpeg to merge metadata and chapters into final m4b
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        tmp_audio_path,
        "-i",
        tmp_meta_path,
        "-map_metadata",
        "1",
        "-map_chapters",
        "1",
        "-codec",
        "copy",
        output_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        ok = True
    except subprocess.CalledProcessError as e:
        logger.error("ffmpeg failed embedding chapters: %s", e.stderr.decode("utf-8", errors="ignore"))
        ok = False

    # Cleanup
    for p in (tmp_audio_path, tmp_meta_path):
        try:
            os.remove(p)
        except Exception:
            pass

    if ok:
        logger.info("M4B with chapters exported to %s", output_path)
    return ok


def _write_metadata(path: str, metadata: dict) -> None:
    """Write minimal metadata to common formats using mutagen."""
    ext = path.split(".")[-1].lower()
    title = metadata.get("title")
    artist = metadata.get("artist")
    album = metadata.get("album")
    tracknumber = metadata.get("tracknumber")

    if ext == "mp3":
        from mutagen.id3 import ID3, TALB, TIT2, TPE1, TRCK, ID3NoHeaderError

        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = ID3()

        if title:
            tags.add(TIT2(text=[title]))
        if artist:
            tags.add(TPE1(text=[artist]))
        if album:
            tags.add(TALB(text=[album]))
        if tracknumber:
            tags.add(TRCK(text=[tracknumber]))
        tags.save(path)

    elif ext in {"m4a", "m4b"}:
        from mutagen.mp4 import MP4

        tags = MP4(path)
        if title:
            tags["\xa9nam"] = [title]
        if artist:
            tags["\xa9ART"] = [artist]
        if album:
            tags["\xa9alb"] = [album]
        if tracknumber:
            try:
                tn = int(tracknumber)
                tags["trkn"] = [(tn, 0)]
            except Exception:
                pass
        tags.save(path)

    elif ext == "flac":
        from mutagen.flac import FLAC

        tags = FLAC(path)
        if title:
            tags["title"] = [title]
        if artist:
            tags["artist"] = [artist]
        if album:
            tags["album"] = [album]
        if tracknumber:
            tags["tracknumber"] = [tracknumber]
        tags.save()
