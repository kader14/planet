"""Tests covering the specific issues found during the semantic review of PR #1.

These tests are designed to prevent regression on the bugs that were fixed:

1. Channel.__contains__ override breaking hidden-channel filtering
2. feedparser 6.x dict-key drift (image.href, source.title/href)
3. CachedInfo.set() correctly routing tuples to set_as_date
4. CachedInfo.__getattr__ using has_key (not __contains__)
5. cache._DbmStrWrapper UTF-8 round-trip
"""

import os
import sys
import time
import tempfile

import pytest

# Ensure code/ is importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE_DIR = os.path.join(_REPO_ROOT, "code")
if _CODE_DIR not in sys.path:
    sys.path.insert(0, _CODE_DIR)

import planet
from planet import cache


# ---------------------------------------------------------------------------
# Issue 1: Channel.__contains__ override and hidden-channel filtering
# ---------------------------------------------------------------------------

class TestHiddenChannelFiltering:
    """Verify that channels with a 'hidden' field in config.ini are correctly
    excluded from Planet.channels(hidden=0) and included in channels(hidden=1).

    The bug: Channel overrides __contains__ = has_item, so 'hidden' in channel
    was checking entry IDs, not cached fields. The fix uses
    channel.has_key('hidden') instead.
    """

    def test_hidden_channel_excluded_by_default(self, planet_factory):
        p, cache_dir, cfg = planet_factory("""
[https://example.com/visible]
name = Visible Feed

[https://example.com/hidden]
name = Hidden Feed
hidden = yes
""")
        for url in cfg.sections():
            if url == "Planet":
                continue
            ch = planet.Channel(p, url)
            p.subscribe(ch)

        visible = p.channels(hidden=0)
        names = [c.name for c in visible]
        assert "Hidden Feed" not in names
        assert "Visible Feed" in names

    def test_hidden_channel_shown_when_requested(self, planet_factory):
        p, cache_dir, cfg = planet_factory("""
[https://example.com/visible]
name = Visible Feed

[https://example.com/hidden]
name = Hidden Feed
hidden = yes
""")
        for url in cfg.sections():
            if url == "Planet":
                continue
            ch = planet.Channel(p, url)
            p.subscribe(ch)

        all_chans = p.channels(hidden=1)
        names = [c.name for c in all_chans]
        assert "Hidden Feed" in names
        assert "Visible Feed" in names


# ---------------------------------------------------------------------------
# Issue 2: feedparser 6.x dict-key drift on <image> and <source>
# ---------------------------------------------------------------------------

class TestFeedparserDictDrift:
    """Verify that update_info and update_entries handle both old (url/value)
    and new (href/title) feedparser dict shapes for <image> and <source>.
    """

    def test_image_url_from_href(self, planet_factory):
        """feedparser 6.x exposes feed.image.href instead of .url."""
        p, cache_dir, _ = planet_factory()
        ch = planet.Channel(p, "https://example.com/feed")

        # Simulate feedparser's image dict with 'href' (new style)
        from feedparser.util import FeedParserDict
        fake_feed = FeedParserDict()
        fake_feed["image"] = FeedParserDict({
            "href": "https://example.com/logo.png",
            "link": "https://example.com",
            "title": "Example Logo",
        })

        ch.update_info(fake_feed)
        assert ch.has_key("image_url")
        assert ch.image_url == "https://example.com/logo.png"

    def test_image_url_from_url_fallback(self, planet_factory):
        """Old feedparser style with 'url' key still works."""
        p, cache_dir, _ = planet_factory()
        ch = planet.Channel(p, "https://example.com/feed2")

        from feedparser.util import FeedParserDict
        fake_feed = FeedParserDict()
        fake_feed["image"] = FeedParserDict({
            "url": "https://example.com/old-logo.png",
            "link": "https://example.com",
            "title": "Old Logo",
        })

        ch.update_info(fake_feed)
        assert ch.has_key("image_url")
        assert ch.image_url == "https://example.com/old-logo.png"

    def test_source_from_title_and_href(self, planet_factory):
        """feedparser 6.x exposes entry.source.title and .href."""
        p, cache_dir, _ = planet_factory()
        ch = planet.Channel(p, "https://example.com/feed3")
        ch.updated = time.gmtime()

        from feedparser.util import FeedParserDict
        entry = FeedParserDict({
            "id": "https://example.com/entry1",
            "title": "Test Entry",
            "source": FeedParserDict({
                "title": "Source Blog",
                "href": "https://source.example.com/feed",
            }),
        })

        item = planet.NewsItem(ch, "https://example.com/entry1")
        ch._items["https://example.com/entry1"] = item
        item.update(entry)

        assert item.has_key("source_name")
        assert item.source_name == "Source Blog"
        assert item.has_key("source_link")
        assert item.source_link == "https://source.example.com/feed"

    def test_source_from_value_and_url_fallback(self, planet_factory):
        """Old feedparser style with 'value' and 'url' still works."""
        p, cache_dir, _ = planet_factory()
        ch = planet.Channel(p, "https://example.com/feed4")
        ch.updated = time.gmtime()

        from feedparser.util import FeedParserDict
        entry = FeedParserDict({
            "id": "https://example.com/entry2",
            "title": "Test Entry 2",
            "source": FeedParserDict({
                "value": "Old Source",
                "url": "https://old-source.example.com/feed",
            }),
        })

        item = planet.NewsItem(ch, "https://example.com/entry2")
        ch._items["https://example.com/entry2"] = item
        item.update(entry)

        assert item.has_key("source_name")
        assert item.source_name == "Old Source"
        assert item.has_key("source_link")
        assert item.source_link == "https://old-source.example.com/feed"


# ---------------------------------------------------------------------------
# Issue 3: CachedInfo.set() type detection (tuples → DATE)
# ---------------------------------------------------------------------------

class TestCachedInfoSetTypeDetection:
    """Verify that CachedInfo.set() routes tuple/struct_time values to
    set_as_date and strings to set_as_string, without a dead TypeError
    fallback.
    """

    def test_tuple_stored_as_date(self, tmp_path):
        db_path = str(tmp_path / "test_dates")
        db = cache.open_cache(db_path, "c")
        ci = cache.CachedInfo(db, "http://test/", root=1)

        date_tuple = (2026, 5, 16, 18, 0, 0, 5, 136, 0)
        ci.set("my_date", date_tuple)

        assert ci.key_type("my_date") == cache.CachedInfo.DATE
        assert ci.get_as_date("my_date") == date_tuple

    def test_struct_time_stored_as_date(self, tmp_path):
        db_path = str(tmp_path / "test_struct_time")
        db = cache.open_cache(db_path, "c")
        ci = cache.CachedInfo(db, "http://test2/", root=1)

        st = time.gmtime()
        ci.set("updated", st)

        assert ci.key_type("updated") == cache.CachedInfo.DATE
        result = ci.get_as_date("updated")
        assert result[:6] == st[:6]  # year/mon/day/hour/min/sec match

    def test_string_stored_as_string(self, tmp_path):
        db_path = str(tmp_path / "test_strings")
        db = cache.open_cache(db_path, "c")
        ci = cache.CachedInfo(db, "http://test3/", root=1)

        ci.set("title", "Hello World")

        assert ci.key_type("title") == cache.CachedInfo.STRING
        assert ci.get_as_string("title") == "Hello World"

    def test_none_stored_as_null(self, tmp_path):
        db_path = str(tmp_path / "test_nulls")
        db = cache.open_cache(db_path, "c")
        ci = cache.CachedInfo(db, "http://test4/", root=1)

        ci.set("etag", None)

        assert ci.key_type("etag") == cache.CachedInfo.NULL
        assert ci.get_as_null("etag") is None


# ---------------------------------------------------------------------------
# Issue 4: CachedInfo.__getattr__ uses has_key (not __contains__)
# ---------------------------------------------------------------------------

class TestGetAttrUsesHasKey:
    """Channel overrides __contains__ = has_item, so __getattr__ must use
    self.has_key(key) to probe cached fields. Verify that attribute access
    on a Channel works for feed-level fields.
    """

    def test_channel_attribute_access(self, planet_factory):
        p, cache_dir, _ = planet_factory()
        ch = planet.Channel(p, "https://example.com/feed-attr")

        # These are set in Channel.__init__ via __setattr__ -> set()
        assert ch.url_status is None  # stored as null, get_as_null returns None
        # ch.name may be None (null) or "" depending on whether a config
        # section with name= exists; the important thing is no AttributeError
        assert ch.has_key("name")
        assert ch.next_order == "0"

    def test_channel_has_key_vs_contains(self, planet_factory):
        """'key in channel' uses has_item (entry ids), but
        channel.has_key('key') checks cached fields.
        """
        p, cache_dir, _ = planet_factory()
        ch = planet.Channel(p, "https://example.com/feed-contains")

        # has_key finds feed-level fields
        assert ch.has_key("url_status") is True
        assert ch.has_key("name") is True

        # 'in' checks entry ids (has_item), not fields
        assert ("url_status" in ch) is False
        assert ("name" in ch) is False


# ---------------------------------------------------------------------------
# Issue 5: cache._DbmStrWrapper UTF-8 round-trip
# ---------------------------------------------------------------------------

class TestDbmStrWrapper:
    """Verify that _DbmStrWrapper correctly encodes/decodes UTF-8 for both
    keys and values, and that the str-keyed API works transparently.
    """

    def test_ascii_round_trip(self, tmp_path):
        db = cache.open_cache(str(tmp_path / "ascii_test"), "c")
        db["hello"] = "world"
        assert db["hello"] == "world"
        assert "hello" in db

    def test_unicode_round_trip(self, tmp_path):
        db = cache.open_cache(str(tmp_path / "unicode_test"), "c")
        db["مفتاح"] = "قيمة عربية"
        assert db["مفتاح"] == "قيمة عربية"
        assert "مفتاح" in db

    def test_cjk_round_trip(self, tmp_path):
        db = cache.open_cache(str(tmp_path / "cjk_test"), "c")
        db["日本語キー"] = "日本語の値"
        assert db["日本語キー"] == "日本語の値"

    def test_keys_returns_str(self, tmp_path):
        db = cache.open_cache(str(tmp_path / "keys_test"), "c")
        db["alpha"] = "1"
        db["beta"] = "2"
        keys = db.keys()
        assert all(isinstance(k, str) for k in keys)
        assert set(keys) == {"alpha", "beta"}

    def test_cache_write_and_read_persistence(self, tmp_path):
        """Verify that CachedInfo can write to disk and read back."""
        db_path = str(tmp_path / "persist_test")
        db = cache.open_cache(db_path, "c")
        ci = cache.CachedInfo(db, "http://persist.example.com/", root=1)
        ci.set_as_string("title", "Persisted Title")
        ci.set_as_date("updated", (2026, 5, 16, 12, 0, 0, 5, 136, 0))
        ci.cache_write()
        db.close()

        # Re-open and read
        db2 = cache.open_cache(db_path, "r")
        ci2 = cache.CachedInfo(db2, "http://persist.example.com/", root=1)
        ci2.cache_read()
        assert ci2.get_as_string("title") == "Persisted Title"
        assert ci2.get_as_date("updated") == (2026, 5, 16, 12, 0, 0, 5, 136, 0)
        db2.close()


# ---------------------------------------------------------------------------
# Bonus: cache.utf8() function
# ---------------------------------------------------------------------------

class TestUtf8Function:
    """Verify the utf8() helper returns str in all cases."""

    def test_str_passthrough(self):
        assert cache.utf8("hello") == "hello"
        assert isinstance(cache.utf8("hello"), str)

    def test_bytes_utf8_decoded(self):
        result = cache.utf8("café".encode("utf-8"))
        assert result == "café"
        assert isinstance(result, str)

    def test_bytes_latin1_decoded(self):
        result = cache.utf8("café".encode("iso-8859-1"))
        assert result == "café"
        assert isinstance(result, str)

    def test_non_string_converted(self):
        result = cache.utf8(42)
        assert result == "42"
        assert isinstance(result, str)

    def test_none_converted(self):
        result = cache.utf8(None)
        assert result == "None"
        assert isinstance(result, str)
