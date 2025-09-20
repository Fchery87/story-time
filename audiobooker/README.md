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

3.  **Run the application (UI):**
    ```bash
    python app.py
    ```

## CLI (Headless) Usage

A command-line interface is available for headless generation.

- Basic:
  ```bash
  python -m audiobooker.cli \
    --input samples/sample.txt \
    --engine piper \
    --format wav \
    --out /tmp/book.wav
  ```

- MP3 with metadata and per-chapter files:
  ```bash
  python -m audiobooker.cli \
    --input samples/sample.txt \
    --engine piper \
    --format mp3 \
    --title "My Book" \
    --author "Jane Doe" \
    --album "Series 1" \
    --chapters-out-dir /tmp/chapters \
    --out /tmp/book.mp3
  ```

- Piper with a specific voice:
  ```bash
  python -m audiobooker.cli \
    --input my.epub \
    --engine piper \
    --piper-voice "/path/to/en_US-amy-medium.onnx" \
    --format wav \
    --out /tmp/book.wav
  ```

- M4B (chapterized, requires ffmpeg):
  ```bash
  python -m audiobooker.cli \
    --input my.epub \
    --engine piper \
    --piper-voice "/path/to/en_US-amy-medium.onnx" \
    --format m4b \
    --title "My Audiobook" \
    --author "Jane Doe" \
    --album "Series 1" \
    --out /tmp/book.m4b
  ```

Options:
- `--max-chars`: chunk size for TTS synthesis (default 1200)
- `--silence-between-chapters-ms`: silence appended after each chapter (default 1000ms)
- `--log-level`: logging verbosity (default INFO)

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

## Export Formats

- Direct export via the pipeline: `wav`, `mp3`, `flac`, `ogg`, `m4a`
- Chapterized `m4b` (AAC) with embedded chapters via ffmpeg
  - Global metadata (title/author/album) supported
  - Requires `ffmpeg` in PATH

Per-chapter files can be emitted via the CLI with `--chapters-out-dir`.

## UI Usage

1.  Launch the Gradio UI by running `python app.py`.
2.  Upload a text file, EPUB, or PDF.
3.  Select a TTS engine and voice (for Piper, set `PIPER_VOICE_PATH` or use the CLI `--piper-voice`).
4.  Click "Generate Audiobook".
5.  The generated audiobook will be available for download.

## Development

- Linting/formatting/type-checking:
  - Pre-commit, Ruff, Black, and mypy configuration included (`pyproject.toml`, `.pre-commit-config.yaml`).
  - Install pre-commit hooks:
    ```bash
    pip install pre-commit
    pre-commit install
    ```
- Tests:
  ```bash
  python -m unittest discover -s audiobooker/tests
  ```
