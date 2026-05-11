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
pip install -r requirements.txt --quiet
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
    [Yy]|[Yy][Ee][Ss]) ;;
    *)
        echo
        warn "Skipping build. Run './install.sh' again to build later."
        echo
        exit 0
        ;;
esac

# ── Linux: check patchelf (required by Nuitka --onefile) ────────────────────────
UNAME_OS=$(uname -s)

if [ "$UNAME_OS" = "Linux" ] && ! command -v patchelf &>/dev/null; then
    echo
    warn "patchelf is not installed. Nuitka requires it for --onefile builds on Linux."
    read -r -p "  Install patchelf now? Requires sudo. [y/N]: " INSTALL_PATCHELF
    case "$INSTALL_PATCHELF" in
        [Yy]|[Yy][Ee][Ss])
            # Detect package manager
            if command -v apt-get &>/dev/null; then
                sudo apt-get install -y patchelf
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y patchelf
            elif command -v pacman &>/dev/null; then
                sudo pacman -S --noconfirm patchelf
            elif command -v zypper &>/dev/null; then
                sudo zypper install -y patchelf
            else
                die "Could not detect a supported package manager (apt/dnf/pacman/zypper).\n     Install patchelf manually and run this script again."
            fi
            ok "patchelf installed."
            ;;
        *)
            die "patchelf is required to build. Install it with:\n     sudo apt install patchelf   (Debian/Ubuntu)\n     sudo dnf install patchelf   (Fedora)\n     sudo pacman -S patchelf     (Arch)"
            ;;
    esac
fi

# ── Install Nuitka and build ──────────────────────────────────────────────────────
info "Installing Nuitka..."
pip install nuitka --quiet
ok "Nuitka installed."

echo
info "Building standalone executable... (this may take a few minutes)"
echo

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
