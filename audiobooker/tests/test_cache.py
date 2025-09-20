import os
import tempfile

from audiobooker.utils import cache as cache_mod


def test_cache_put_get_and_clear():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["AUDIOBOOKER_CACHE_DIR"] = tmpdir
        key = "abc123"
        data = b"test-bytes"
        assert cache_mod.get_from_cache(key) is None

        cache_mod.put_in_cache(key, data)
        out = cache_mod.get_from_cache(key)
        assert out == data

        cache_mod.clear_cache()
        assert cache_mod.get_from_cache(key) is None

    # Cleanup env var for other tests
    os.environ.pop("AUDIOBOOKER_CACHE_DIR", None)