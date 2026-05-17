#!/bin/bash
# =============================================================================
# Planet Python — one-shot installer for cPanel.
#
# Usage (run on the cPanel SSH shell, NOT as root):
#
#     bash ~/planet/deploy/cpanel/setup.sh
#
# Or with options:
#
#     bash ~/planet/deploy/cpanel/setup.sh \
#         --output-dir /home/$USER/public_html \
#         --python python3.11
#
# What this script does (idempotent — safe to re-run):
#   1. Detects your cPanel username and home directory.
#   2. Creates a virtualenv under ~/virtualenv/planet/<pyver>/.
#   3. Installs the Python dependencies from requirements.txt.
#   4. Copies config/config.ini -> config/config.ini (keeps the original) and
#      patches output_dir + cache_directory to point at cPanel paths.
#   5. Creates the cache + logs directories.
#   6. Runs planet.py once to verify everything works.
#   7. Prints the exact line you need to paste into cPanel -> Cron Jobs.
# =============================================================================
set -euo pipefail

# ----------------------------- helpers ---------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { printf "${BLUE}==>${NC} %s\n" "$*"; }
ok()    { printf "${GREEN}OK${NC}  %s\n" "$*"; }
warn()  { printf "${YELLOW}WARN${NC} %s\n" "$*"; }
fail()  { printf "${RED}ERR${NC} %s\n" "$*" >&2; exit 1; }

# ----------------------------- defaults --------------------------------------
PLANET_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CPANEL_USER="${USER:-$(whoami)}"
HOME_DIR="${HOME:-/home/${CPANEL_USER}}"
OUTPUT_DIR="${HOME_DIR}/public_html"
CACHE_DIR="${PLANET_ROOT}/cache"
LOG_DIR="${PLANET_ROOT}/logs"
PYTHON_BIN=""
SKIP_FIRST_RUN=0

# ----------------------------- arg parsing -----------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir)   OUTPUT_DIR="$2";       shift 2 ;;
        --cache-dir)    CACHE_DIR="$2";        shift 2 ;;
        --python)       PYTHON_BIN="$2";       shift 2 ;;
        --skip-run)     SKIP_FIRST_RUN=1;      shift   ;;
        -h|--help)
            sed -n '2,30p' "$0"
            exit 0
            ;;
        *) fail "Unknown option: $1" ;;
    esac
done

# ----------------------------- safety checks ---------------------------------
if [[ "${EUID}" -eq 0 ]]; then
    fail "Do NOT run this script as root. Run it as your cPanel user."
fi

if [[ ! -f "${PLANET_ROOT}/code/planet.py" ]]; then
    fail "Could not find code/planet.py under ${PLANET_ROOT}. Is the repo at ~/planet ?"
fi

# ----------------------------- pick Python -----------------------------------
if [[ -z "${PYTHON_BIN}" ]]; then
    for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "${candidate}" >/dev/null 2>&1; then
            PYTHON_BIN="${candidate}"
            break
        fi
    done
fi
[[ -n "${PYTHON_BIN}" ]] || fail "No python3 interpreter found in PATH."

PYVER=$("${PYTHON_BIN}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
VENV_DIR="${HOME_DIR}/virtualenv/planet/${PYVER}"

info "cPanel user      : ${CPANEL_USER}"
info "Project root     : ${PLANET_ROOT}"
info "Python           : ${PYTHON_BIN} (${PYVER})"
info "Virtualenv       : ${VENV_DIR}"
info "Output directory : ${OUTPUT_DIR}"
info "Cache directory  : ${CACHE_DIR}"
info "Log  directory   : ${LOG_DIR}"
echo

# ----------------------------- 1. virtualenv ---------------------------------
if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
    info "Creating virtualenv ..."
    mkdir -p "$(dirname "${VENV_DIR}")"
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
    ok "virtualenv created"
else
    ok "virtualenv already exists, reusing"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

# ----------------------------- 2. dependencies -------------------------------
info "Upgrading pip and installing requirements ..."
python -m pip install --upgrade pip wheel >/dev/null
python -m pip install -r "${PLANET_ROOT}/requirements.txt"
ok "dependencies installed"

# ----------------------------- 3. patch config.ini ---------------------------
CONFIG_FILE="${PLANET_ROOT}/config/config.ini"
[[ -f "${CONFIG_FILE}" ]] || fail "config/config.ini not found"

# Make a one-time backup so we never lose the original.
if [[ ! -f "${CONFIG_FILE}.orig" ]]; then
    cp "${CONFIG_FILE}" "${CONFIG_FILE}.orig"
    ok "backup written to ${CONFIG_FILE}.orig"
fi

info "Patching output_dir and cache_directory ..."
python - "${CONFIG_FILE}" "${OUTPUT_DIR}" "${CACHE_DIR}" <<'PY'
import re, sys, pathlib
path, out_dir, cache_dir = sys.argv[1], sys.argv[2], sys.argv[3]
text = pathlib.Path(path).read_text()

def replace_or_insert(text, key, value):
    pattern = re.compile(rf'^\s*{re.escape(key)}\s*=.*$', re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(f'{key} = {value}', text, count=1)
    # otherwise insert just under [Planet]
    return re.sub(r'(\[Planet\]\s*\n)', rf'\1{key} = {value}\n', text, count=1)

text = replace_or_insert(text, 'output_dir',      out_dir)
text = replace_or_insert(text, 'cache_directory', cache_dir)
pathlib.Path(path).write_text(text)
PY
ok "config.ini patched (original preserved as config.ini.orig)"

# ----------------------------- 4. directories --------------------------------
mkdir -p "${OUTPUT_DIR}" "${CACHE_DIR}" "${LOG_DIR}"
ok "output / cache / logs directories ready"

# ----------------------------- 5. cron runner --------------------------------
chmod +x "${PLANET_ROOT}/deploy/cpanel/run-planet.sh"

# ----------------------------- 6. first run ----------------------------------
if [[ "${SKIP_FIRST_RUN}" -eq 0 ]]; then
    info "Running planet.py once to verify the setup ..."
    PLANET_VENV="${VENV_DIR}" "${PLANET_ROOT}/deploy/cpanel/run-planet.sh" \
        || fail "planet.py failed; inspect ${LOG_DIR}/planet.log"
    ok "first run finished, ${OUTPUT_DIR} now contains:"
    ls -1 "${OUTPUT_DIR}" | sed 's/^/      /'
else
    warn "skipping first run (per --skip-run)"
fi

# ----------------------------- 7. cron snippet -------------------------------
CRON_LINE="*/30 * * * * PLANET_VENV=${VENV_DIR} ${PLANET_ROOT}/deploy/cpanel/run-planet.sh"

cat <<EOF

${GREEN}=============================================================${NC}
  Setup complete. Final step: schedule the cron job.
${GREEN}=============================================================${NC}

  Open  cPanel  ->  Advanced  ->  Cron Jobs  and add:

    ${YELLOW}${CRON_LINE}${NC}

  Or, equivalently, fill the form like this:

      Common Settings : Twice an hour (*/30 * * * *)
      Command         : ${YELLOW}${PLANET_ROOT}/deploy/cpanel/run-planet.sh${NC}
      (and tick "Add an environment variable" with
       PLANET_VENV=${VENV_DIR}
       if your host requires the venv path to be passed explicitly)

  After 30 minutes, check:

      tail -n 50 ${LOG_DIR}/planet.log
      ls -la ${OUTPUT_DIR}

${GREEN}=============================================================${NC}
EOF
