import gradio as gr
import tempfile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from tts_engines.coqui_engine import CoquiEngine
from tts_engines.piper_engine import PiperEngine
from tts_engines.pyttsx3_engine import Pyttsx3Engine
from utils.book_loader import load_book
from pipeline.loudness import normalize_loudness
from pipeline.post import add_silence
from pipeline.export import export_audiobook

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

# --- Gradio App ---

def update_chapters(file):
    if file is None:
        return gr.update(choices=[], value=None), ""

    chapters = load_book(file.name)
    chapter_titles = [title for title, text in chapters]

    # Store chapters in a global state for now (Gradio limitation)
    demo.chapters = chapters

    first_chapter_text = chapters[0][1] if chapters else ""
    return gr.update(choices=chapter_titles, value=chapter_titles[0] if chapter_titles else None), first_chapter_text

def update_text(chapter_title):
    if not hasattr(demo, "chapters") or not demo.chapters:
        return ""

    for title, text in demo.chapters:
        if title == chapter_title:
            return text
    return ""

def generate_audio(text, tts_engine_name):
    if not text:
        return None, "Please enter some text."

    if not tts_engine_name:
        return None, "Please select a TTS engine."

    engine = tts_engines.get(tts_engine_name)
    if not engine:
        return None, f"Engine '{tts_engine_name}' not available."

    try:
        wav_bytes = engine.synth_to_wav_bytes(text)

        if not wav_bytes:
            return None, "Synthesis failed. Check the logs."

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
            temp_audio_file.write(wav_bytes)
            temp_filename = temp_audio_file.name

        return temp_filename, "Synthesis complete."

    except Exception as e:
        return None, f"An error occurred: {e}"

def generate_full_audiobook(tts_engine_name, progress=gr.Progress()):
    if not hasattr(demo, "chapters") or not demo.chapters:
        return None, "No book loaded."

    engine = tts_engines.get(tts_engine_name)
    if not engine:
        return None, f"Engine '{tts_engine_name}' not available."

    processed_chapters = []
    num_chapters = len(demo.chapters)

    for i, (title, text) in enumerate(demo.chapters):
        progress((i + 1) / num_chapters, desc=f"Synthesizing: {title}")

        wav_bytes = engine.synth_to_wav_bytes(text)
        wav_bytes = normalize_loudness(wav_bytes)
        wav_bytes = add_silence(wav_bytes, 1000) # 1 second of silence
        processed_chapters.append(wav_bytes)

    progress(1.0, desc="Combining chapters...")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
        output_path = temp_audio_file.name

    export_audiobook(processed_chapters, output_path)

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

            with gr.Accordion("Single Chapter Synthesis", open=False):
                generate_button = gr.Button("Generate Chapter Audio")

            with gr.Accordion("Full Audiobook Generation", open=True):
                generate_full_button = gr.Button("Generate Full Audiobook")


        with gr.Column(scale=2):
            chapter_text_input = gr.Textbox(label="Chapter Text", lines=10, interactive=True)
            audio_output = gr.Audio(label="Synthesized Audio")
            full_audiobook_output = gr.File(label="Download Full Audiobook")
            status_output = gr.Textbox(label="Status")

    file_input.change(
        update_chapters,
        inputs=[file_input],
        outputs=[chapter_dropdown, chapter_text_input]
    )

    chapter_dropdown.change(
        update_text,
        inputs=[chapter_dropdown],
        outputs=[chapter_text_input]
    )

    generate_button.click(
        generate_audio,
        inputs=[chapter_text_input, tts_engine_dropdown],
        outputs=[audio_output, status_output],
    )

    generate_full_button.click(
        generate_full_audiobook,
        inputs=[tts_engine_dropdown],
        outputs=[full_audiobook_output, status_output]
    )

if __name__ == "__main__":
    demo.launch()
