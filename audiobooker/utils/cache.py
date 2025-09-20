import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_CACHE_SUBDIR = ".cache/audiobooker"


def get_cache_dir() -> Path:
    """Return the cache directory path, creating it if necessary."""
    base = os.environ.get("AUDIOBOOKER_CACHE_DIR")
    if base:
        cache_dir = Path(base)
    else:
        cache_dir = Path.home() / DEFAULT_CACHE_SUBDIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def is_cache_enabled() -> bool:
    """Return True if caching is enabled via env (default: enabled)."""
    val = os.environ.get("AUDIOBOOKER_CACHE_ENABLED", "1").strip().lower()
    return val not in {"0", "false", "no", "off"}


def make_cache_key(engine_name: str, engine_variant: str, text: str) -> str:
    """Create a deterministic key for a given engine + variant + text."""
    h = hashlib.sha256()
    h.update(engine_name.encode("utf-8"))
    h.update(b"|")
    h.update(engine_variant.encode("utf-8"))
    h.update(b"|")
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def _cache_path_for(key: str) -> Path:
    return get_cache_dir() / f"{key}.wav"


def get_from_cache(key: str) -> Optional[bytes]:
    """Return cached WAV bytes if present."""
    path = _cache_path_for(key)
    if path.exists():
        try:
            return path.read_bytes()
        except Exception:
            logger.exception("Failed reading cache file: %s", path)
    return None


def put_in_cache(key: str, wav_bytes: bytes) -> None:
    """Store WAV bytes into cache."""
    path = _cache_path_for(key)
    try:
        path.write_bytes(wav_bytes)
    except Exception:
        logger.exception("Failed writing cache file: %s", path)


def clear_cache() -> None:
    """Delete all cache files."""
    cache_dir = get_cache_dir()
    try:
        for p in cache_dir.glob("*.wav"):
            try:
                p.unlink()
            except Exception:
                logger.exception("Failed removing cache file: %s", p)
    except Exception:
        logger.exception("Failed clearing cache directory: %s", cache_dir)