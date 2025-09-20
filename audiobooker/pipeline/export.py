import logging
from io import BytesIO

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
