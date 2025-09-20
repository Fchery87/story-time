# Local Audiobook Generator

A free, local audiobook generator in Python.

## Quickstart

1.  Install ffmpeg.
    -   macOS (Homebrew): `brew install ffmpeg`
    -   Windows (Chocolatey): `choco install ffmpeg`
    -   Linux (apt): `sudo apt update && sudo apt install ffmpeg`

2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Run the application (UI):
    ```bash
    python app.py
    ```

## CLI (Headless) Usage

A command-line interface is available for headless generation.

- Basic:
  ```bash
  python -m audiobooker.cli \
    samples/sample.txt \
    --engine piper \
    --out /tmp/book.wav
  ```

- MP3 with metadata and per-chapter files:
  ```bash
  python -m audiobooker.cli \
    samples/sample.txt \
    --engine piper \
    --title "My Book" \
    --author "Jane Doe" \
    --per-chapter-dir /tmp/chapters \
    --out /tmp/book.mp3
  ```

- Piper with a specific voice:
  ```bash
  python -m audiobooker.cli \
    my.epub \
    --engine piper \
    --voice "/path/to/en_US-amy-medium.onnx" \
    --out /tmp/book.wav
  ```

- M4B:
  ```bash
  python -m audiobooker.cli \
    my.epub \
    --engine piper \
    --voice "/path/to/en_US-amy-medium.onnx" \
    --title "My Audiobook" \
    --author "Jane Doe" \
    --out /tmp/book.m4b
  ```
  Notes:
  - Chapters are exported optionally via `--per-chapter-dir`. Embedded chapter markers inside M4B are not yet added.
  - Global metadata (title/author/album) is written for MP3/M4A/M4B/FLAC.

Other options:
- `--no-cache` disable on-disk synthesis cache for this run
- `--clear-cache` clear the cache and exit

## Engines

This application supports the following TTS engines:

- Coqui TTS — High-quality, slower and more resource-intensive.
- Piper TTS — Fast, lightweight, and produces good quality audio.
- pyttsx3 — Very fast but lower quality (native OS voices).

## Loudness Targets

The audio is normalized to ACX-ish loudness:
- Peak: -3.0 dBFS
- Integrated loudness: around -20 LUFS
- Stereo, 16-bit, 44.1 kHz output

Handled by `pyloudnorm` and `pydub`.

## Export Formats

- `wav`, `mp3`, `flac`, `ogg`, `m4a`, `m4b` (M4B uses MP4/AAC container; chapter markers not yet embedded)
- Per-chapter files with metadata via the CLI `--per-chapter-dir` option

## Caching

- By default, synthesized chunks are cached on disk to speed up repeat runs.
- Configure via environment variables:
  - `AUDIOBOOKER_CACHE_ENABLED` (default `1`)
  - `AUDIOBOOKER_CACHE_DIR` (default `~/.cache/audiobooker`)

## UI Usage

1.  Launch the Gradio UI: `python app.py`
2.  Upload a text file, EPUB, or PDF.
3.  Select a TTS engine.
4.  Click "Generate Audiobook".
5.  Download the generated audio.

## Development

- Linting/formatting/type-checking:
  - Pre-commit, Ruff, Black, and mypy configurations are included (`pyproject.toml`, `.pre-commit-config.yaml`).
  - Install pre-commit hooks:
    ```bash
    pip install pre-commit
    pre-commit install
    ```
- Run tests:
  ```bash
  python -m unittest discover -s audiobooker/tests
  ```
