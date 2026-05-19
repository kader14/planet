#!/bin/bash
# -----------------------------------------------------------------------------
# Planet Python — cron runner for cPanel
# -----------------------------------------------------------------------------
# Schedule from cPanel -> "Cron Jobs" (every 30 minutes is plenty):
#
#     */30 * * * * /home/YOUR_CPANEL_USER/planet/deploy/cpanel/run-planet.sh
#
# The script:
#   1. Loads the virtualenv created by cPanel's "Setup Python App" (or a manual
#      `python3 -m venv ~/virtualenv/planet`).
#   2. Runs planet.py against config/config.ini.
#   3. Copies the bundled static assets (logo + stylesheets) into output_dir
#      so the generated pages render correctly.
#   4. Logs everything to ~/planet/logs/planet.log with timestamped entries.
# -----------------------------------------------------------------------------
set -euo pipefail

# --- Resolve paths relative to this script (no hard-coded usernames) ---------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLANET_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${PLANET_ROOT}/logs"
LOG_FILE="${LOG_DIR}/planet.log"

mkdir -p "${LOG_DIR}"

log() {
    printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "${LOG_FILE}"
}

# --- Activate the virtualenv -------------------------------------------------
# cPanel's "Setup Python App" places the venv under ~/virtualenv/<app>/<py>/.
# If PLANET_VENV is not provided we auto-detect the newest 3.x venv that has
# an activate script under ~/virtualenv/planet/.
if [[ -z "${PLANET_VENV:-}" ]]; then
    BASE="${HOME}/virtualenv/planet"
    if [[ -d "${BASE}" ]]; then
        # Sort -V picks the highest version (e.g. 3.13 before 3.11).
        for candidate in $(ls -1 "${BASE}" 2>/dev/null | sort -Vr); do
            if [[ -f "${BASE}/${candidate}/bin/activate" ]]; then
                PLANET_VENV="${BASE}/${candidate}"
                break
            fi
        done
    fi
    PLANET_VENV="${PLANET_VENV:-${HOME}/virtualenv/planet/3.11}"
fi

if [[ -f "${PLANET_VENV}/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${PLANET_VENV}/bin/activate"
    log "Using virtualenv ${PLANET_VENV}"
else
    log "WARN: virtualenv not found at ${PLANET_VENV}; falling back to system python3"
fi

# Many shared/cPanel hosts mount $HOME on a filesystem (NFS, CageFS, …) that
# does not honour flock(); without this gdbm fails with EAGAIN. The Python
# cache layer respects the variable and skips locking when it is set.
export PLANET_GDBM_NOLOCK="${PLANET_GDBM_NOLOCK:-1}"

# --- Read output_dir straight from config.ini --------------------------------
CONFIG_FILE="${PLANET_ROOT}/config/config.ini"
OUTPUT_DIR="$(awk -F '= *' '/^output_dir/ {print $2; exit}' "${CONFIG_FILE}" | tr -d '[:space:]')"

if [[ -z "${OUTPUT_DIR}" ]]; then
    log "ERROR: could not read output_dir from ${CONFIG_FILE}"
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"

# --- Run the aggregator ------------------------------------------------------
log "Running planet.py (output -> ${OUTPUT_DIR})"
cd "${PLANET_ROOT}"

if python3 code/planet.py "${CONFIG_FILE}" >> "${LOG_FILE}" 2>&1; then
    log "planet.py finished OK"
else
    log "ERROR: planet.py exited non-zero"
    exit 1
fi

# --- Sync static assets (stylesheets + images + fonts + scripts) ------------
# The templates reference /styles/..., /images/..., /fonts/... and /scripts/...
# at the docroot, so the contents of static/ must be available beside the
# generated HTML.
if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete-after \
        "${PLANET_ROOT}/static/styles/" "${OUTPUT_DIR}/styles/"
    rsync -a --delete-after \
        "${PLANET_ROOT}/static/images/" "${OUTPUT_DIR}/images/"
    rsync -a --delete-after \
        "${PLANET_ROOT}/static/fonts/" "${OUTPUT_DIR}/fonts/"
    rsync -a --delete-after \
        "${PLANET_ROOT}/static/scripts/" "${OUTPUT_DIR}/scripts/"
else
    cp -r "${PLANET_ROOT}/static/styles/." "${OUTPUT_DIR}/styles/"
    cp -r "${PLANET_ROOT}/static/images/." "${OUTPUT_DIR}/images/"
    cp -r "${PLANET_ROOT}/static/fonts/." "${OUTPUT_DIR}/fonts/"
    cp -r "${PLANET_ROOT}/static/scripts/." "${OUTPUT_DIR}/scripts/"
fi

# --- Top-level SEO files (robots.txt + sitemap.xml) ------------------------
# These live at the docroot, not in a subdirectory, so they're shipped here
# from static/ rather than via rsync above.
cp -f "${PLANET_ROOT}/static/robots.txt" "${OUTPUT_DIR}/robots.txt"
cp -f "${PLANET_ROOT}/static/sitemap.xml" "${OUTPUT_DIR}/sitemap.xml"

log "Static assets synced into ${OUTPUT_DIR}"
log "Done."
