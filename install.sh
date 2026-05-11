#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# STM32 Flash  —  Installation Script for Linux / macOS
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
BLD='\033[1m'
RST='\033[0m'

info()  { echo -e "  ${BLD}[•]${RST} $*"; }
ok()    { echo -e "  ${GRN}[✓]${RST} $*"; }
warn()  { echo -e "  ${YLW}[!]${RST} $*"; }
die()   { echo -e "  ${RED}[✗]${RST} $*" >&2; exit 1; }

echo
echo -e "${BLD}  STM32 Flash — Installation Script${RST}"
echo    "  ──────────────────────────────────────────────────────"
echo

# ── [1/4] Check Python ───────────────────────────────────────────────────────
info "[1/4] Checking Python..."

PYTHON_BIN=""
for candidate in python3 python3.13 python3.12 python3.11 python3.10 python; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" -c 'import sys; print(sys.version_info[:2])')
        major=$("$candidate" -c 'import sys; print(sys.version_info.major)')
        minor=$("$candidate" -c 'import sys; print(sys.version_info.minor)')
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

[ -z "$PYTHON_BIN" ] && die "Python 3.10+ not found. Install it via your package manager:\n     sudo apt install python3  (Debian/Ubuntu)\n     brew install python       (macOS)"
ok "Found: $($PYTHON_BIN --version)"

# ── [2/4] Create virtual environment ─────────────────────────────────────────
info "[2/4] Creating virtual environment (.venv)..."

if [ -d ".venv" ]; then
    warn ".venv already exists — skipping creation."
else
    "$PYTHON_BIN" -m venv .venv
    ok "Created .venv"
fi

# Activate
# shellcheck disable=SC1091
source .venv/bin/activate

# ── [3/4] Install dependencies ────────────────────────────────────────────────
info "[3/4] Installing dependencies..."

pip install --upgrade pip --quiet
pip install -r requirements.txt
ok "Dependencies installed."

# ── [4/4] Done ────────────────────────────────────────────────────────────────
echo
ok "[4/4] Setup complete."
echo
echo    "  ──────────────────────────────────────────────────────"
echo    "  To run the application:"
echo    "    source .venv/bin/activate"
echo    "    python src/main.py"
echo    "  ──────────────────────────────────────────────────────"
echo

# ── Optional: build with Nuitka ───────────────────────────────────────────────
read -r -p "  Build a standalone executable with Nuitka? [y/N]: " BUILD_EXE

case "$BUILD_EXE" in
    [Yy]|[Yy][Ee][Ss])
        ;;
    *)
        echo
        warn "Skipping build. Run './install.sh' again or use 'python build.py' later."
        echo
        exit 0
        ;;
esac

info "Installing Nuitka..."
pip install nuitka --quiet
ok "Nuitka installed."

echo
info "Building standalone executable... (this may take a few minutes)"
echo

# Detect OS for icon / extra flags
UNAME_OS=$(uname -s)
EXTRA_FLAGS=""
if [ "$UNAME_OS" = "Darwin" ]; then
    EXTRA_FLAGS="--macos-app-name=STM32Flash"
fi

# shellcheck disable=SC2086
python -m nuitka \
    --onefile \
    --enable-plugin=pyqt6 \
    --output-dir=dist \
    --output-filename=STM32Flash \
    --include-data-dir=config=config \
    $EXTRA_FLAGS \
    src/main.py

echo
ok "Build complete!"
echo
echo    "  ──────────────────────────────────────────────────────"
echo    "  Executable: dist/STM32Flash"
if [ "$UNAME_OS" = "Linux" ]; then
echo    "  Run: chmod +x dist/STM32Flash && ./dist/STM32Flash"
fi
echo    "  ──────────────────────────────────────────────────────"
echo
