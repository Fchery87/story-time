import logging
import os
import tempfile
from io import BytesIO

import gradio as gr
from dotenv import load_dotenv
from pydub import AudioSegment

from pipeline.chunker import chunk
from pipeline.loudness import normalize_loudness
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

        # Combine the chunks into a single audio segment
        combined_audio = AudioSegment.empty()
        for wav_bytes in processed_chunks:
            if wav_bytes:
                chunk_audio = AudioSegment.from_wav(BytesIO(wav_bytes))
                combined_audio += chunk_audio

        if len(combined_audio) == 0:
            return None, "Synthesis failed. Check the logs."

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

    processed_chapters = []
    num_chapters = len(chapters)

    for i, (title, text) in enumerate(chapters):
        progress((i + 1) / max(num_chapters, 1), desc=f"Processing Chapter: {title}")

        text_chunks = chunk(text, max_chars=int(max_chars))
        num_chunks = len(text_chunks)
        chapter_audio = AudioSegment.empty()

        for j, text_chunk in enumerate(text_chunks):
            progress((j + 1) / max(num_chunks, 1), desc=f"Synthesizing chunk {j+1}/{num_chunks} of {title}")
            wav_bytes = _synthesize_with_cache(tts_engine_name, engine, text_chunk)
            wav_bytes = normalize_loudness(wav_bytes)

            if wav_bytes:
                chunk_audio = AudioSegment.from_wav(BytesIO(wav_bytes))
                chapter_audio += chunk_audio

        # Add silence between chapters
        if len(chapter_audio) > 0 and int(silence_ms) > 0:
            chapter_audio += AudioSegment.silent(duration=int(silence_ms))

        processed_chapters.append(chapter_audio)

    progress(1.0, desc="Combining chapters...")

    # Combine all chapter audio segments
    full_audiobook = AudioSegment.empty()
    for chapter_audio in processed_chapters:
        full_audiobook += chapter_audio

    if len(full_audiobook) == 0:
        return None, "Audiobook generation failed."

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
        output_path = temp_audio_file.name

    full_audiobook.export(output_path, format="wav")

    return output_path, "Audiobook generation complete."


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

            with gr.Accordion("Single Chapter Synthesis", open=False):
                generate_button = gr.Button("Generate Chapter Audio")

            with gr.Accordion("Full Audiobook Generation", open=True):
                silence_slider = gr.Slider(0, 5000, value=1000, step=100, label="Silence between chapters (ms)")
                generate_full_button = gr.Button("Generate Full Audiobook")

        with gr.Column(scale=2):
            chapter_text_input = gr.Textbox(label="Chapter Text", lines=10, interactive=True)
            audio_output = gr.Audio(label="Synthesized Audio")
            full_audiobook_output = gr.File(label="Download Full Audiobook")
            status_output = gr.Textbox(label="Status")

    # Use Gradio State to store chapters instead of global attributes
    chapters_state = gr.State([])

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

    generate_button.click(
        generate_audio,
        inputs=[chapter_text_input, tts_engine_dropdown, max_chars_slider, piper_speed_slider, pyttsx3_rate_slider],
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
