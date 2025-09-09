from TTS.api import TTS

# This should download the model if it's not already cached.
print("Downloading/loading Coqui TTS model...")
try:
    TTS("tts_models/en/ljspeech/vits")
    print("Model downloaded/loaded successfully.")
except Exception as e:
    print(f"Failed to download/load model: {e}")
