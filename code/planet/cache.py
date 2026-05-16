#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Item cache.

Between runs of Planet we need somewhere to store the feed information
we parsed, this is so we don't lose information when a particular feed
goes away or is too short to hold enough items.

This module provides the code to handle this cache transparently enough
that the rest of the code can take the persistance for granted.

Python 3 notes:
    The underlying ``dbm.gnu`` store accepts only ``bytes`` for both keys and
    values. To keep the public API of :class:`CachedInfo` working in terms of
    ``str`` (as it did under Python 2 with implicit encode/decode), this module
    encodes/decodes at the dbm boundary using UTF-8.
"""

import os
import re


# Regular expressions to sanitise cache filenames
re_url_scheme    = re.compile(r'^[^:]*://')
re_slash         = re.compile(r'[?/]+')
re_initial_cruft = re.compile(r'^[,.]*')
re_final_cruft   = re.compile(r'[,.]*$')


def _to_bytes(value):
    """Encode a str to bytes for storage in dbm.gnu. Bytes pass through."""
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return str(value).encode("utf-8")


def _to_str(value):
    """Decode bytes from dbm.gnu back to a str. Strings pass through."""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.decode("utf-8", "replace")
    return value


class _DbmStrWrapper:
    """Thin wrapper around a dbm.gnu handle that exposes a str-keyed,
    str-valued mapping. Encoding/decoding happens on every access.

    This lets the rest of the codebase pretend the cache works with regular
    Python strings, the way it used to under Python 2.
    """

    def __init__(self, db):
        self._db = db

    def __contains__(self, key):
        return _to_bytes(key) in self._db

    def __getitem__(self, key):
        return _to_str(self._db[_to_bytes(key)])

    def __setitem__(self, key, value):
        self._db[_to_bytes(key)] = _to_bytes(value)

    def __delitem__(self, key):
        del self._db[_to_bytes(key)]

    def keys(self):
        return [_to_str(k) for k in self._db.keys()]

    # ``has_key`` is referenced in legacy code paths.
    def has_key(self, key):
        return _to_bytes(key) in self._db

    def sync(self):
        if hasattr(self._db, "sync"):
            self._db.sync()

    def close(self):
        self._db.close()


def open_cache(filename_, mode="c", perm=0o666):
    """Open a planet cache file as a str-keyed, str-valued dictionary.

    Wraps ``dbm.gnu.open`` so the rest of the planet codebase can keep using
    plain ``str`` objects for both keys and values, the way it did under
    Python 2.
    """
    import dbm.gnu as gdbm
    return _DbmStrWrapper(gdbm.open(filename_, mode, perm))


class CachedInfo:
    """Cached information.

    This class is designed to hold information that is stored in a cache
    between instances.  It can act both as a dictionary (c['foo']) and
    as an object (c.foo) to get and set values and supports both string
    and date values.

    If you wish to support special fields you can derive a class off this
    and implement get_FIELD and set_FIELD functions which will be
    automatically called.
    """
    STRING = "string"
    DATE   = "date"
    NULL   = "null"

    def __init__(self, cache, id_, root=0):
        self._type = {}
        self._value = {}
        self._cached = {}

        # Wrap a raw dbm.gnu handle so the rest of this class can deal in
        # ``str``. Existing wrappers pass through unchanged.
        if not isinstance(cache, _DbmStrWrapper) and hasattr(cache, "keys"):
            try:
                # If it quacks like dbm.gnu, wrap it.
                import dbm.gnu  # noqa: F401
                cache = _DbmStrWrapper(cache)
            except ImportError:
                pass

        self._cache = cache
        self._id = id_.replace(" ", "%20")
        self._root = root

    def cache_key(self, key):
        """Return the cache key name for the given key."""
        key = key.replace(" ", "_")
        if self._root:
            return key
        else:
            return self._id + " " + key

    def cache_read(self):
        """Read information from the cache."""
        if self._root:
            keys_key = " keys"
        else:
            keys_key = self._id

        if keys_key in self._cache:
            keys = self._cache[keys_key].split(" ")
        else:
            return

        for key in keys:
            cache_key = self.cache_key(key)
            if key not in self._cached or self._cached[key]:
                # Key either hasn't been loaded, or is one for the cache
                self._value[key] = self._cache[cache_key]
                self._type[key] = self._cache[cache_key + " type"]
                self._cached[key] = 1

    def cache_write(self, sync=1):
        """Write information to the cache."""
        self.cache_clear(sync=0)

        keys = []
        for key in list(self.keys()):
            cache_key = self.cache_key(key)
            if not self._cached[key]:
                if cache_key in self._cache:
                    # Non-cached keys need to be cleared
                    del(self._cache[cache_key])
                    del(self._cache[cache_key + " type"])
                continue

            keys.append(key)
            self._cache[cache_key] = self._value[key]
            self._cache[cache_key + " type"] = self._type[key]

        if self._root:
            keys_key = " keys"
        else:
            keys_key = self._id

        self._cache[keys_key] = " ".join(keys)
        if sync:
            self._cache.sync()

    def cache_clear(self, sync=1):
        """Remove information from the cache."""
        if self._root:
            keys_key = " keys"
        else:
            keys_key = self._id

        if keys_key in self._cache:
            keys = self._cache[keys_key].split(" ")
            del(self._cache[keys_key])
        else:
            return

        for key in keys:
            cache_key = self.cache_key(key)
            try:
                del(self._cache[cache_key])
                del(self._cache[cache_key + " type"])
            except KeyError:
                pass

        if sync:
            self._cache.sync()

    def has_key(self, key):
        """Check whether the key exists."""
        key = key.replace(" ", "_")
        return key in self._value

    def key_type(self, key):
        """Return the key type."""
        key = key.replace(" ", "_")
        return self._type[key]

    def set(self, key, value, cached=1):
        """Set the value of the given key.

        If a set_KEY function exists that is called otherwise the
        string function is called and the date function if that fails
        (it nearly always will).
        """
        key = key.replace(" ", "_")

        try:
            func = getattr(self, "set_" + key)
        except AttributeError:
            pass
        else:
            return func(key, value)

        if value is None:
            return self.set_as_null(key, value)

        # Date-like values (tuple/struct_time as returned by feedparser /
        # time.gmtime) must be stored as DATE; everything else is treated as
        # a string.
        import time as _time
        if isinstance(value, (tuple, _time.struct_time)):
            return self.set_as_date(key, value)

        return self.set_as_string(key, value)

    def get(self, key):
        """Return the value of the given key.

        If a get_KEY function exists that is called otherwise the
        correctly typed function is called if that exists.
        """
        key = key.replace(" ", "_")

        try:
            func = getattr(self, "get_" + key)
        except AttributeError:
            pass
        else:
            return func(key)

        try:
            func = getattr(self, "get_as_" + self._type[key])
        except AttributeError:
            pass
        else:
            return func(key)

        return self._value[key]

    def set_as_string(self, key, value, cached=1):
        """Set the key to the string value.

        Under Python 3 the in-memory representation is ``str`` (already
        Unicode). Bytes coming in from feedparser are decoded as UTF-8.
        """
        value = utf8(value)

        key = key.replace(" ", "_")
        self._value[key] = value
        self._type[key] = self.STRING
        self._cached[key] = cached

    def get_as_string(self, key):
        """Return the key as a string value."""
        key = key.replace(" ", "_")
        if not self.has_key(key):
            raise KeyError(key)

        return self._value[key]

    def set_as_date(self, key, value, cached=1):
        """Set the key to the date value.

        The date should be a 9-item tuple as returned by time.gmtime().
        """
        value = " ".join([str(s) for s in value])

        key = key.replace(" ", "_")
        self._value[key] = value
        self._type[key] = self.DATE
        self._cached[key] = cached

    def get_as_date(self, key):
        """Return the key as a date value."""
        key = key.replace(" ", "_")
        if not self.has_key(key):
            raise KeyError(key)

        value = self._value[key]
        return tuple([int(i) for i in value.split(" ")])

    def set_as_null(self, key, value, cached=1):
        """Set the key to the null value.

        This only exists to make things less magic.
        """
        key = key.replace(" ", "_")
        self._value[key] = ""
        self._type[key] = self.NULL
        self._cached[key] = cached

    def get_as_null(self, key):
        """Return the key as the null value."""
        key = key.replace(" ", "_")
        if not self.has_key(key):
            raise KeyError(key)

        return None

    def del_key(self, key):
        """Delete the given key."""
        key = key.replace(" ", "_")
        if not self.has_key(key):
            raise KeyError(key)

        del(self._value[key])
        del(self._type[key])
        del(self._cached[key])

    def keys(self):
        """Return the list of cached keys."""
        return list(self._value.keys())

    def __iter__(self):
        """Iterate the cached keys."""
        return iter(list(self._value.keys()))

    # Special methods
    __contains__ = has_key
    __setitem__  = set_as_string
    __getitem__  = get
    __delitem__  = del_key
    __delattr__  = del_key

    def __setattr__(self, key, value):
        if key.startswith("_"):
            self.__dict__[key] = value
        else:
            self.set(key, value)

    def __getattr__(self, key):
        # ``__contains__`` may be overridden by subclasses (e.g. Channel makes
        # ``in`` mean "is this an item id?"), so check the cached-info store
        # directly via ``has_key`` rather than via ``in self``.
        if self.has_key(key):
            return self.get(key)
        else:
            raise AttributeError(key)


def filename(directory, filename):
    """Return a filename suitable for the cache.

    Strips dangerous and common characters to create a filename we
    can use to store the cache in.
    """
    filename = re_url_scheme.sub("", filename)
    filename = re_slash.sub(",", filename)
    filename = re_initial_cruft.sub("", filename)
    filename = re_final_cruft.sub("", filename)

    return os.path.join(directory, filename)


def utf8(value):
    """Return the value as a Unicode ``str``.

    Under Python 2 this returned a UTF-8 encoded ``bytes`` object. Under
    Python 3 the canonical text type is ``str`` (already Unicode), so we
    decode any incoming ``bytes`` and return ``str``. The function name is
    kept for compatibility with the rest of the codebase.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        for enc in ("utf-8", "iso-8859-1"):
            try:
                return value.decode(enc)
            except UnicodeDecodeError:
                continue
        return value.decode("ascii", "replace")
    return str(value)
