import os
from typing import Iterable, List, Tuple


DEFAULT_VOICE_DIRS: List[str] = [
    os.path.expanduser("~/.local/share/piper-voices"),
    os.path.expanduser("~/models/piper"),
    os.path.expanduser("~/piper-voices"),
    "/usr/share/piper-voices",
    "/opt/piper-voices",
]


def _is_piper_voice(path: str) -> bool:
    """
    A Piper voice is an .onnx file with a sibling .json config.
    """
    if not path.lower().endswith(".onnx"):
        return False
    cfg = path + ".json"
    return os.path.exists(cfg)


def _make_label(path: str) -> str:
    """
    Human-friendly label derived from filename and parent directory.
    """
    base = os.path.basename(path)
    name = os.path.splitext(base)[0]
    parent = os.path.basename(os.path.dirname(path))
    if parent and parent not in {"", ".", "/"}:
        return f"{name} ({parent})"
    return name


def discover_piper_voices(base_dir: str | None = None, extra_dirs: Iterable[str] | None = None) -> List[Tuple[str, str]]:
    """
    Discover Piper voices by scanning default directories and optional paths.

    Returns a list of (label, path) tuples suitable for populating a UI dropdown.
    """
    search_dirs: List[str] = []
    if base_dir:
        search_dirs.append(os.path.expanduser(base_dir))
    env_dir = os.environ.get("PIPER_VOICES_DIR")
    if env_dir:
        search_dirs.append(os.path.expanduser(env_dir))
    search_dirs.extend(DEFAULT_VOICE_DIRS)
    if extra_dirs:
        search_dirs.extend([os.path.expanduser(d) for d in extra_dirs])

    found: List[Tuple[str, str]] = []
    seen_paths = set()

    for root_dir in search_dirs:
        if not root_dir or not os.path.isdir(root_dir):
            continue
        for root, _, files in os.walk(root_dir):
            for fname in files:
                path = os.path.join(root, fname)
                if _is_piper_voice(path) and path not in seen_paths:
                    seen_paths.add(path)
                    found.append((_make_label(path), path))

    # Sort by label
    found.sort(key=lambda t: t[0].lower())
    return found