import logging
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
    import os

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
        from mutagen.mp4 import MP4, MP4Cover

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
