FROM python:3.11-slim

# System tools that helpers and the Makefile occasionally rely on. Kept
# minimal vs. the old Ubuntu Bionic image which carried a lot of debugging
# baggage.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        dumb-init \
        locales \
        tzdata \
 && rm -rf /var/lib/apt/lists/* \
 && sed -i '/^#.* en_US.UTF-8 /s/^#//' /etc/locale.gen \
 && locale-gen en_US.UTF-8

ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /planet

# Install Python deps first to maximise build cache hits.
COPY requirements.txt /planet/requirements.txt
RUN pip install --no-cache-dir -r /planet/requirements.txt

COPY code   /planet/code
COPY config /planet/config
COPY static /planet/static

VOLUME /srv/planetpython.org/

# Aggregate feeds, then serve the resulting site directly with the stdlib
# http.server (the modern replacement for the old SimpleHTTPServer).
RUN printf '%s\n' \
    '#!/bin/bash -eux' \
    'python3 code/planet.py config/config.ini' \
    'cd /srv/planetpython.org/' \
    'exec python3 -m http.server 8080' \
    > /start.sh \
 && chmod +x /start.sh

ENTRYPOINT ["dumb-init", "--"]
EXPOSE 8080
CMD ["/start.sh"]
