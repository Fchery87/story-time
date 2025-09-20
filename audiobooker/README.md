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

- M4B with embedded chapters:
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
  - Embedded chapter markers are added using ffmpeg's ffmetadata.
  - Global metadata (title/author/album) is written for MP3/M4A/M4B/FLAC.

Other useful options:
- `--max-chars` chunk size for TTS synthesis (default 1200)
- `--silence-between-chapters-ms` silence appended between chapters (default 1000)
- `--piper-length-scale` Piper speed control (e.g., 0.8 faster, 1.2 slower)
- `--pyttsx3-rate` pyttsx3 speech rate (e.g., 200)
- `--trim-silence` trim leading/trailing silence per chapter (leaves small padding)
- `--compress` apply dynamic range compression per chapter
- `--fade-ms` apply equal fade in/out (ms) per chapter
- `--no-cache` disable on-disk synthesis cache for this run
- `--clear-cache` clear the cache and exit

Examples for new flags:
- Trim and light fades:
  ```bash
  python -m audiobooker.cli samples/sample.txt --engine piper --out /tmp/book.wav \
    --trim-silence --fade-ms 50
  ```
- Compression and trims to even out dynamics:
  ```bash
  python -m audiobooker.cli samples/sample.txt --engine piper --out /tmp/book.mp3 \
    --compress --trim-silence
  ```

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

- `wav`, `mp3`, `flac`, `ogg`, `m4a`, `m4b` (M4B uses MP4/AAC container; chapter markers supported)
- Per-chapter files with metadata via the CLI `--per-chapter-dir` option

## UI Usage

1.  Launch the Gradio UI: `python app.py`
2.  Upload a text file, EPUB, or PDF.
3.  Select a TTS engine.
4.  Tune parameters (chunk size, Piper speed, pyttsx3 rate), and generate.
5.  (Optional) Use Post-processing to trim silence, compress, and add fades.
6.  Download the generated audio.

## Docker

### Compose (recommended)

A Docker Compose file is provided.

- Prepare directories:
  ```bash
  mkdir -p models/piper cache output
  ```
- Put your Piper voice models (.onnx + .json) under `models/piper/`
- Run:
  ```bash
  docker compose up --build
  ```
- Open the UI at http://localhost:7860

Mounts and environment:
- Volumes:
  - `./models:/models:ro` — read-only models mount. Piper voices discovered under `/models/piper`.
  - `./cache:/cache` — cache for synthesized chunks (`AUDIOBOOKER_CACHE_DIR`).
  - `./output:/output` — optional output directory for future export workflows.
- Environment variables:
  - `PIPER_VOICES_DIR=/models/piper`
  - `AUDIOBOOKER_CACHE_DIR=/cache`
  - `AUDIOBOOKER_CACHE_ENABLED=1`
  - `GRADIO_SERVER_NAME=0.0.0.0` (exposes UI outside the container)

### Plain Docker

- Build:
  ```bash
  docker build -t audiobooker .
  ```
- Run UI:
  ```bash
  docker run --rm -p 7860:7860 \
    -e PIPER_VOICES_DIR=/models/piper \
    -e AUDIOBOOKER_CACHE_DIR=/cache \
    -v "$(pwd)"/models:/models:ro \
    -v "$(pwd)"/cache:/cache \
    audiobooker
  ```

## Caching

- By default, synthesized chunks are cached on disk to speed up repeat runs.
- Configure via environment variables:
  - `AUDIOBOOKER_CACHE_ENABLED` (default `1`)
  - `AUDIOBOOKER_CACHE_DIR` (default `~/.cache/audiobooker`)

## Development

- Linting/formatting/type-checking:
  - Pre-commit, Ruff, Black, and mypy configurations are included (`pyproject.toml`, `.pre-commit-config.yaml`).
  - Install pre-commit hooks:
    ```bash
    pip install -r requirements-dev.txt
    pre-commit install
    ```
- Run tests:
  ```bash
  python -m unittest discover -s audiobooker/tests
  ```
