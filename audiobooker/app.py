import gradio as gr
import tempfile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from tts_engines.coqui_engine import CoquiEngine
from tts_engines.piper_engine import PiperEngine
from tts_engines.pyttsx3_engine import Pyttsx3Engine

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

with gr.Blocks() as demo:
    gr.Markdown("# Local Audiobook Generator - TTS Test")

    if engine_errors:
        gr.Markdown("---")
        for error in engine_errors:
            gr.Markdown(f"⚠️ **Engine Loading Error:** {error}")
        gr.Markdown("---")

    with gr.Row():
        with gr.Column():
            text_input = gr.Textbox(
                label="Text to Synthesize",
                value="This is a test of the text to speech synthesis."
            )
            tts_engine_dropdown = gr.Dropdown(
                available_engines, label="TTS Engine", value=available_engines[0] if available_engines else None
            )
            generate_button = gr.Button("Generate Audio")

        with gr.Column():
            audio_output = gr.Audio(label="Synthesized Audio")
            status_output = gr.Textbox(label="Status")

    generate_button.click(
        generate_audio,
        inputs=[text_input, tts_engine_dropdown],
        outputs=[audio_output, status_output],
    )

if __name__ == "__main__":
    demo.launch()
