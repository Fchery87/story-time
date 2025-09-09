# Local Audiobook Generator

A free, local audiobook generator in Python.

## Quickstart

1.  **Install ffmpeg.**
    -   **macOS (using Homebrew):** `brew install ffmpeg`
    -   **Windows (using Chocolatey):** `choco install ffmpeg`
    -   **Linux (using apt):** `sudo apt update && sudo apt install ffmpeg`

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    ```bash
    python app.py
    ```

## Engines

This application supports the following TTS engines:

*   **Coqui TTS:** High-quality, but slower and more resource-intensive.
*   **Piper TTS:** Fast, lightweight, and produces good quality audio.
*   **pyttsx3:** A cross-platform text-to-speech library that uses native speech engines. It's very fast but the quality is lower.

## ACX-ish Loudness Targets

The audio is normalized to meet ACX-ish standards for loudness:

*   **Peak value:** -3.5 dB
*   **RMS level:** between -23dB and -18dB RMS

These values are handled by the `pyloudnorm` library.

## Usage

1.  Launch the Gradio UI by running `python app.py`.
2.  Upload a text file, EPUB, or PDF.
3.  Select a TTS engine and voice.
4.  Click "Generate Audiobook".
5.  The generated audiobook will be available for download.
