import os
from dotenv import load_dotenv

load_dotenv()

from tts_engines.coqui_engine import CoquiEngine
from tts_engines.piper_engine import PiperEngine
from tts_engines.pyttsx3_engine import Pyttsx3Engine

TEST_TEXT = "This is a test of the text to speech synthesis. This is the second sentence."

def test_engine(engine_class, output_filename):
    print(f"--- Testing {engine_class.__name__} ---")
    try:
        engine = engine_class()
        wav_bytes = engine.synth_to_wav_bytes(TEST_TEXT)

        if wav_bytes:
            with open(output_filename, "wb") as f:
                f.write(wav_bytes)
            print(f"✅ Success: Saved to {output_filename}")
            # Check file size
            file_size = os.path.getsize(output_filename)
            print(f"File size: {file_size} bytes")
            if file_size == 0:
                print("⚠️ Warning: Output file is empty.")
        else:
            print("❌ Failure: Synthesis returned empty bytes.")

    except Exception as e:
        print(f"❌ Failure: An error occurred: {e}")
    print("-" * (len(engine_class.__name__) + 14))


if __name__ == "__main__":
    test_engine(Pyttsx3Engine, "pyttsx3_output.wav")
    test_engine(CoquiEngine, "coqui_output.wav")
    test_engine(PiperEngine, "piper_output.wav")
