# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2025-09-20

Added
- UI: M4B export with embedded chapter markers (ffmpeg metadata).
- UI: Post-processing options (trim silence, dynamic compression, fades).
- UI: Piper voice discovery and selection; Coqui model reload.
- CLI: New flags --trim-silence, --compress, --fade-ms.
- Docker: docker-compose.yml with model/cache/output mounts and environment configuration.

Changed
- Audio pipeline: centralized chunking and standardized audio format (stereo, 16-bit, 44.1 kHz).
- Slight crossfades between chunks to reduce clicks.
- Logging across app and pipeline for better traceability.

Fixed
- Removed duplicate chunking in engines and pipeline; engines now synthesize single chunks.
- More robust export helpers and metadata writing.

## [0.1.0] - 2025-09-01

- Initial public version with UI, basic pipeline, and multiple TTS engines.