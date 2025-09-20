import logging
import os
import shutil
import tempfile
from io import BytesIO

import gradio as gr
from dotenv import load_dotenv
from pydub import AudioSegment

from pipeline.chunker import chunk
from pipeline.loudness import normalize_loudness
from pipeline.export import (
    concat_wav_files_ffmpeg,
    export_audio_file,
    export_m4b_with_chapters,
)
from pipeline.post import apply_postprocessing
from tts_engines.coqui_engine import CoquiEngine
from tts_engines.piper_engine import PiperEngine
from tts_engines.pyttsx3_engine import Pyttsx3Engine
from utils.book_loader import load_book
from utils.cache import (
    get_from_cache,
    is_cache_enabled,
    make_cache_key,
    put_in_cache,
)
from utils.voice_discovery import discover_piper_voices

# Load environment variables from .env file
load_dotenv()

# --- Logging ---
logger = logging.getLogger(__name__)

# --- Engine Initialization ---
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

available_engines = list(tts_engines.keys())


def _engine_variant(engine) -> str:
    # Best-effort identifier to include in cache key
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


# --- Piper voice discovery and reload ---
def scan_piper_voices_ui(base_dir: str | None):
    voices = discover_piper_voices(base_dir)
    labels = [label for label, _ in voices]
    value = labels[0] if labels else None
    return gr.update(choices=labels, value=value), voices, (
        f"Found {len(labels)} Piper voice(s)." if labels else "No Piper voices found."
    )


def reload_piper_engine_ui(selected_label: str | None, voices_state: list[tuple[str, str]]):
    path = None
    if selected_label and voices_state:
        for label, p in voices_state:
            if label == selected_label:
                path = p
                break
    if not path:
        return "Select a Piper voice first (scan if needed)."
    try:
        tts_engines["piper"] = PiperEngine(model_path=path)
        return f"Piper engine reloaded: {os.path.basename(path)}"
    except Exception as e:
        logger.exception("Failed to reload Piper engine")
        return f"Failed to reload Piper: {e}"


# --- Gradio App Callbacks ---
def update_chapters(file):
    if file is None:
        return gr.update(choices=[], value=None), "", []

    chapters = load_book(file.name)
    chapter_titles = [title for title, _ in chapters]

    first_chapter_text = chapters[0][1] if chapters else ""
    return (
        gr.update(choices=chapter_titles, value=chapter_titles[0] if chapter_titles else None),
        first_chapter_text,
        chapters,
    )


def update_text(chapter_title, chapters):
    if not chapters:
        return ""

    for title, text in chapters:
        if title == chapter_title:
            return text
    return ""


def generate_audio(
    text,
    tts_engine_name,
    max_chars,
    piper_length_scale,
    pyttsx3_rate,
    enable_trim,
    enable_compress,
    fade_ms,
    progress=gr.Progress(),
):
    if not text:
        return None, "Please enter some text."

    if not tts_engine_name:
        return None, "Please select a TTS engine."

    engine = tts_engines.get(tts_engine_name)
    if not engine:
        return None, f"Engine '{tts_engine_name}' not available."

    # Apply engine-specific UI parameters
    try:
        if tts_engine_name == "piper" and hasattr(engine, "update_params"):
            engine.update_params(length_scale=piper_length_scale)
        if tts_engine_name == "pyttsx3" and hasattr(engine, "update_params"):
            engine.update_params(rate=int(pyttsx3_rate))
    except Exception as e:
        logger.warning("Failed to update engine parameters: %s", e)

    try:
        text_chunks = chunk(text, max_chars=int(max_chars))
        num_chunks = len(text_chunks)
        processed_chunks = []

        for i, text_chunk in enumerate(text_chunks):
            progress((i + 1) / max(num_chunks, 1), desc=f"Synthesizing chunk {i+1}/{num_chunks}")
            wav_bytes = _synthesize_with_cache(tts_engine_name, engine, text_chunk)
            wav_bytes = normalize_loudness(wav_bytes)
            processed_chunks.append(wav_bytes)

        # Combine the chunks into a single audio segment with slight crossfades
        combined_audio = AudioSegment.empty()
        for wav_bytes in processed_chunks:
            if wav_bytes:
                chunk_audio = AudioSegment.from_wav(BytesIO(wav_bytes))
                combined_audio = combined_audio.append(chunk_audio, crossfade=10)

        if len(combined_audio) == 0:
            return None, "Synthesis failed. Check the logs."

        # Optional post-processing
        combined_audio = apply_postprocessing(
            combined_audio, enable_compression=enable_compress, enable_trim=enable_trim, fade_ms=int(fade_ms)
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
            combined_audio.export(temp_audio_file.name, format="wav")
            temp_filename = temp_audio_file.name

        return temp_filename, "Synthesis complete."

    except Exception as e:
        logger.exception("Error during single chapter synthesis")
        return None, f"An error occurred: {e}"


def generate_full_audiobook(
    tts_engine_name,
    chapters,
    max_chars,
    silence_ms,
    piper_length_scale,
    pyttsx3_rate,
    export_format,
    title,
    author,
    enable_trim,
    enable_compress,
    fade_ms,
    progress=gr.Progress(),
):
    if not chapters:
        return None, "No book loaded."

    engine = tts_engines.get(tts_engine_name)
    if not engine:
        return None, f"Engine '{tts_engine_name}' not available."

    # Apply engine-specific UI parameters
    try:
        if tts_engine_name == "piper" and hasattr(engine, "update_params"):
            engine.update_params(length_scale=piper_length_scale)
        if tts_engine_name == "pyttsx3" and hasattr(engine, "update_params"):
            engine.update_params(rate=int(pyttsx3_rate))
    except Exception as e:
        logger.warning("Failed to update engine parameters: %s", e)

    num_chapters = len(chapters)
    temp_chapter_files: list[str] = []
    chapter_segments: list[AudioSegment] = []
    chapter_titles: list[str] = []

    for i, (ch_title, text) in enumerate(chapters):
        progress((i + 1) / max(num_chapters, 1), desc=f"Processing Chapter: {ch_title}")

        text_chunks = chunk(text, max_chars=int(max_chars))
        num_chunks = len(text_chunks)
        chapter_audio = AudioSegment.empty()

        for j, text_chunk in enumerate(text_chunks):
            progress((j + 1) / max(num_chunks, 1), desc=f"Synthesizing chunk {j+1}/{num_chunks} of {ch_title}")
            wav_bytes = _synthesize_with_cache(tts_engine_name, engine, text_chunk)
            wav_bytes = normalize_loudness(wav_bytes)

            if wav_bytes:
                chunk_audio = AudioSegment.from_wav(BytesIO(wav_bytes))
                chapter_audio = chapter_audio.append(chunk_audio, crossfade=10)

        # Optional per-chapter post-processing
        chapter_audio = apply_postprocessing(
            chapter_audio, enable_compression=enable_compress, enable_trim=enable_trim, fade_ms=int(fade_ms)
        )

        # Add silence between chapters
        if len(chapter_audio) > 0 and int(silence_ms) > 0:
            chapter_audio += AudioSegment.silent(duration=int(silence_ms))

        chapter_titles.append(ch_title)

        if export_format == "m4b":
            # Keep segments in memory for M4B chapter embedding
            chapter_segments.append(chapter_audio)
        else:
            # Stream to disk for low memory usage
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_ch:
                chapter_audio.export(tmp_ch.name, format="wav")
                temp_chapter_files.append(tmp_ch.name)

    metadata = {
        "title": title or "Audiobook",
        "artist": author or "Unknown",
        "album": title or "Audiobook",
    }

    if export_format == "m4b":
        with tempfile.NamedTemporaryFile(suffix=".m4b", delete=False) as tmp_out:
            out_path = tmp_out.name
        ok = export_m4b_with_chapters(
            chapter_audios=chapter_segments,
            titles=chapter_titles,
            output_path=out_path,
            chapter_silence_ms=int(silence_ms),
            metadata=metadata,
        )
        if not ok:
            return None, "Failed to export M4B with chapters."
        return out_path, "Audiobook generation complete."

    # Non-M4B path: concatenate wavs then export
    progress(1.0, desc="Combining chapters...")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
        wav_out_path = temp_audio_file.name

    # Prefer ffmpeg for stream-copy concatenation
    ffmpeg_ok = shutil.which("ffmpeg") is not None and concat_wav_files_ffmpeg(temp_chapter_files, wav_out_path)

    if not ffmpeg_ok:
        # Fallback to in-memory concatenation if ffmpeg is unavailable
        full_audiobook = AudioSegment.empty()
        for f in temp_chapter_files:
            try:
                full_audiobook += AudioSegment.from_wav(f)
            except Exception:
                logger.exception("Failed reading temp chapter file %s", f)
        if len(full_audiobook) == 0:
            return None, "Audiobook generation failed."
        full_audiobook.export(wav_out_path, format="wav")

    # Cleanup temp chapter files
    for f in temp_chapter_files:
        try:
            os.remove(f)
        except Exception:
            pass

    # If target format is wav, return that file; else convert to target
    if export_format == "wav":
        return wav_out_path, "Audiobook generation complete."

    # Convert to selected format with metadata
    with tempfile.NamedTemporaryFile(suffix=f".{export_format}", delete=False) as tmp_final:
        final_path = tmp_final.name
    try:
        audio_seg = AudioSegment.from_wav(wav_out_path)
        export_audio_file(audio_seg, final_path, metadata=metadata)
        # Remove intermediate wav
        try:
            os.remove(wav_out_path)
        except Exception:
            pass
        return final_path, "Audiobook generation complete."
    except Exception as e:
        logger.exception("Failed converting to target format: %s", e)
        return wav_out_path, "Generated WAV (conversion failed)."


with gr.Blocks() as demo:
    gr.Markdown("# Local Audiobook Generator")

    if engine_errors:
        gr.Markdown("---")
        for error in engine_errors:
            gr.Markdown(f"⚠️ **Engine Loading Error:** {error}")
        gr.Markdown("---")

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(label="Upload Book (txt, md, epub, pdf)")
            chapter_dropdown = gr.Dropdown([], label="Chapter", interactive=True)
            tts_engine_dropdown = gr.Dropdown(
                available_engines, label="TTS Engine", value=available_engines[0] if available_engines else None
            )

            # Synthesis parameters
            max_chars_slider = gr.Slider(200, 3000, value=1200, step=50, label="Chunk size (max chars)")
            piper_speed_slider = gr.Slider(0.6, 1.6, value=1.0, step=0.05, label="Piper speed (length_scale)")
            pyttsx3_rate_slider = gr.Slider(100, 250, value=200, step=1, label="pyttsx3 rate")

            # Post-processing options (applied to synthesized audio)
            with gr.Accordion("Post-processing", open=False):
                trim_checkbox = gr.Checkbox(value=False, label="Trim silence")
                compress_checkbox = gr.Checkbox(value=False, label="Dynamic compression")
                fade_slider = gr.Slider(0, 200, value=0, step=10, label="Fade in/out (ms)")

            with gr.Accordion("Single Chapter Synthesis", open=False):
                generate_button = gr.Button("Generate Chapter Audio")

            with gr.Accordion("Full Audiobook Generation", open=True):
                silence_slider = gr.Slider(0, 5000, value=1000, step=100, label="Silence between chapters (ms)")
                export_format_dd = gr.Dropdown(
                    ["wav", "mp3", "flac", "m4a", "m4b"], value="wav", label="Export format"
                )
                title_input = gr.Textbox(label="Title (metadata)", placeholder="Audiobook title")
                author_input = gr.Textbox(label="Author (metadata)", placeholder="Author/Artist")
                generate_full_button = gr.Button("Generate Full Audiobook")

            with gr.Accordion("Engine Settings", open=False):
                piper_scan_dir = gr.Textbox(
                    label="Piper voices directory (optional)",
                    placeholder="Leave empty to search default locations",
                )
                piper_scan_btn = gr.Button("Scan Piper Voices")
                piper_voice_dropdown = gr.Dropdown(label="Piper Voice (discovered)", choices=[], interactive=True)
                reload_piper_button = gr.Button("Reload Piper Engine")
                coqui_model_input = gr.Textbox(
                    label="Coqui model name",
                    placeholder="e.g., tts_models/en/ljspeech/vits",
                )
                reload_coqui_button = gr.Button("Reload Coqui Engine")

        with gr.Column(scale=2):
            chapter_text_input = gr.Textbox(label="Chapter Text", lines=10, interactive=True)
            audio_output = gr.Audio(label="Synthesized Audio")
            full_audiobook_output = gr.File(label="Download Full Audiobook")
            status_output = gr.Textbox(label="Status")

    # Use Gradio State to store chapters and piper voices
    chapters_state = gr.State([])
    piper_voices_state = gr.State([])

    file_input.change(
        update_chapters,
        inputs=[file_input],
        outputs=[chapter_dropdown, chapter_text_input, chapters_state],
    )

    chapter_dropdown.change(
        update_text,
        inputs=[chapter_dropdown, chapters_state],
        outputs=[chapter_text_input],
    )

    piper_scan_btn.click(
        scan_piper_voices_ui,
        inputs=[piper_scan_dir],
        outputs=[piper_voice_dropdown, piper_voices_state, status_output],
    )

    reload_piper_button.click(
        reload_piper_engine_ui,
        inputs=[piper_voice_dropdown, piper_voices_state],
        outputs=[status_output],
    )

    def reload_coqui_engine_ui(model_name: str | None):
        if not model_name:
            return "Enter a Coqui model name to reload."
        try:
            tts_engines["coqui"] = CoquiEngine(model_name=model_name)
            return f"Coqui engine reloaded: {model_name}"
        except Exception as e:
            logger.exception("Failed to reload Coqui engine")
            return f"Failed to reload Coqui: {e}"

    reload_coqui_button.click(
        reload_coqui_engine_ui,
        inputs=[coqui_model_input],
        outputs=[status_output],
    )

    generate_button.click(
        generate_audio,
        inputs=[
            chapter_text_input,
            tts_engine_dropdown,
            max_chars_slider,
            piper_speed_slider,
            pyttsx3_rate_slider,
            trim_checkbox,
            compress_checkbox,
            fade_slider,
        ],
        outputs=[audio_output, status_output],
    )

    generate_full_button.click(
        generate_full_audiobook,
        inputs=[
            tts_engine_dropdown,
            chapters_state,
            max_chars_slider,
            silence_slider,
            piper_speed_slider,
            pyttsx3_rate_slider,
            export_format_dd,
            title_input,
            author_input,
            trim_checkbox,
            compress_checkbox,
            fade_slider,
        ],
        outputs=[full_audiobook_output, status_output],
    )

if __name__ == "__main__":
    # Basic logging configuration for the app entrypoint
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    demo.launch()
