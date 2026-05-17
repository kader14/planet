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
# Override PLANET_VENV in the cron command if yours lives elsewhere.
PLANET_VENV="${PLANET_VENV:-${HOME}/virtualenv/planet/3.11}"
if [[ -f "${PLANET_VENV}/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${PLANET_VENV}/bin/activate"
else
    log "WARN: virtualenv not found at ${PLANET_VENV}; falling back to system python3"
fi

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

# --- Sync static assets (stylesheets + images) -------------------------------
# The templates reference /styles/... and /images/... at the docroot, so the
# contents of static/ must be available beside the generated HTML.
if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete-after \
        "${PLANET_ROOT}/static/styles/" "${OUTPUT_DIR}/styles/"
    rsync -a --delete-after \
        "${PLANET_ROOT}/static/images/" "${OUTPUT_DIR}/images/"
else
    cp -r "${PLANET_ROOT}/static/styles/." "${OUTPUT_DIR}/styles/"
    cp -r "${PLANET_ROOT}/static/images/." "${OUTPUT_DIR}/images/"
fi

log "Static assets synced into ${OUTPUT_DIR}"
log "Done."
