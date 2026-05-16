Planet Python
=============

This is the source code that drives `planetpython.org
<https://planetpython.org>`_, a feed aggregator for the Python community.

The project was originally based on the venerable `Planet Planet
<https://web.archive.org/web/2010/http://www.planetplanet.org>`_ aggregator
which targeted Python 2. This branch ports the codebase to **Python 3** and
trims a few legacy backports (the bundled ``feedparser`` and ``compat_logging``
copies).

.. contents::


Maintaining the feed list
-------------------------

* New feed requests come in via GitHub issues
  (https://github.com/python/planet/issues).

* Validate the feed first using a service such as
  https://validator.w3.org/feed/ or https://www.rssboard.org/rss-validator/.

* Confirm the content is *Python-specific* and *English-language* (ask the
  submitter for a Python-only or English-only feed if needed).

* Add the feed URL as a new section to ``config/config.ini``::

      [http://example.org/feed/url/]
      name = Author/Group/Project Name

  Then sort the file::

      cd config
      python sort-ini.py

  Commit the result.


Running locally
---------------

Requirements: **Python 3.9 or newer** and ``pip``.

.. code-block:: bash

   pip install -r requirements.txt
   python code/planet.py config/config.ini

The aggregator reads the feed list from ``config/config.ini``, downloads each
feed, caches the parsed entries in ``cache_directory`` (configured in the
``[Planet]`` section), and writes the rendered output to ``output_dir``.

Defaults assume ``/srv/planetpython.org/`` for output and ``/srv/cache`` for
the cache. For a local run, copy the file and override those paths::

   cp config/config.ini /tmp/local.ini
   sed -i 's|/srv/planetpython.org/|/tmp/planet-output|;s|/srv/cache|/tmp/planet-cache|' /tmp/local.ini
   mkdir -p /tmp/planet-output /tmp/planet-cache
   python code/planet.py /tmp/local.ini


Running with Docker
-------------------

The provided ``Dockerfile`` runs the aggregator inside ``python:3.11-slim``
and serves the resulting static site over the stdlib ``http.server`` on port
8080:

.. code-block:: bash

   docker compose up --build
   # then visit http://localhost:8080

``Dockerfile.deploy`` is the slim image used for production deployments; it
contains only the application code and Python dependencies (no debug tools,
no embedded webserver) so an external reverse proxy can serve the static
output directory.


Project layout
--------------

::

   code/
       planet.py          # CLI entry point
       planet-cache.py    # Inspect / mutate the on-disk cache
       planet/
           __init__.py    # Planet, Channel, NewsItem
           cache.py       # dbm.gnu-backed CachedInfo
           sanitize.py    # HTML sanitiser used on feed content
           atomstyler.py  # Atom output post-processor
           htmltmpl.py    # The HTMLTMPL templating language
   config/
       config.ini         # Subscription list + per-template options
       *.tmpl             # Output templates (HTML, RSS, Atom, OPML, FOAF)
   static/                # Logo and stylesheets bundled with the site


Notes about the Python 3 port
-----------------------------

The original codebase shipped its own copies of ``feedparser`` and ``logging``
backports, plus several modules that have since been removed from the
standard library. This branch makes the following changes, all behind a
compatible public API:

* The bundled ``code/planet/feedparser.py`` and ``code/planet/compat_logging/``
  packages have been removed in favour of the modern PyPI ``feedparser`` and
  the stdlib ``logging`` module.
* ``code/planet/cache.py`` now wraps a ``dbm.gnu`` handle and transparently
  encodes/decodes UTF-8 at the I/O boundary so the rest of the code can
  continue to deal in ``str``.
* ``md5`` has been replaced with ``hashlib.md5``.
* ``cgi.escape`` has been replaced with ``html.escape``.
* ``Dockerfile`` now uses ``python:3.11-slim`` and serves the output with
  ``python3 -m http.server`` (the stdlib replacement for the old
  ``SimpleHTTPServer``).
* ``htmltmpl.py`` was kept (it is unmaintained on PyPI for Python 3) but
  patched in-tree for Python 3 compatibility (``cgi`` removal, ``types``
  module constants, ``urllib`` reorganisation, ``cPickle`` -> ``pickle``).

If anything misbehaves, please open an issue with the offending feed URL and
the traceback.
