"""Shared pytest fixtures for the Planet aggregator tests.

The aggregator code lives at ``code/`` (not on ``sys.path`` by default), and
the tests need to import the ``planet`` package from there. We add it to
``sys.path`` once, here, so individual test modules can do plain
``import planet``.
"""

import os
import sys

# Make the ``planet`` package importable. Tests run from the repo root.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE_DIR = os.path.join(_REPO_ROOT, "code")
if _CODE_DIR not in sys.path:
    sys.path.insert(0, _CODE_DIR)


import pytest  # noqa: E402  (sys.path tweak above must come first)


@pytest.fixture
def planet_factory(tmp_path):
    """Return a callable that builds a Planet with a config-string and a
    temp cache_directory.

    Yields a tuple of (planet_instance, cache_dir, config_parser).
    """
    from configparser import ConfigParser

    import planet

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    def _build(extra_sections=""):
        cfg = ConfigParser()
        cfg.read_string(
            f"""
[Planet]
name = pytest planet
owner_name = pytest
owner_email = pytest@example.com
encoding = utf-8
cache_directory = {cache_dir}
output_dir = {output_dir}
items_per_page = 5
new_feed_items = 1
template_files =

{extra_sections}
"""
        )
        p = planet.Planet(cfg)
        p.cache_directory = str(cache_dir)
        return p, str(cache_dir), cfg

    return _build
