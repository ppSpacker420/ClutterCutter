#!/usr/bin/env bash
# ============================================================================
#  ClutterCutter - one-command install (Linux / macOS)
#
#  curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/main/install.sh | bash
#
#  Installs into ~/.local/bin. No root, no sudo, no system modification.
#  You can delete the directory afterwards and nothing else is affected.
# ============================================================================
set -uo pipefail

REPO_URL="${CLUTTERCUTTER_REPO:-https://github.com/ClutterCutter/ClutterCutter}"
INSTALL_DIR="${HOME}/.local/bin"
PYTHON=""

say()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mWarning:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31mError:\033[0m %s\n' "$*" >&2; exit 1; }

# --- 1. find Python --------------------------------------------------------
say "Looking for Python 3.10 or newer..."
for c in python3.13 python3.12 python3.11 python3.10 python3 python; do
    command -v "$c" >/dev/null 2>&1 || continue
    if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
        PYTHON="$c"
        break
    fi
done
[ -n "$PYTHON" ] || die "Python 3.10+ is required. Install it and run this again."
say "Using $("$PYTHON" --version)"

# --- 2. get the source -----------------------------------------------------
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

say "Downloading ClutterCutter..."
if command -v git >/dev/null 2>&1; then
    git clone --depth 1 --quiet "$REPO_URL" "$TMP/ClutterCutter" \
        || die "clone failed. Check your internet connection, or download and unzip manually."
else
    command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1 \
        || die "Need git, curl, or wget. Install one and run this again."
    ARCHIVE="$TMP/src.tar.gz"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$REPO_URL/archive/refs/heads/main.tar.gz" -o "$ARCHIVE" \
            || die "download failed."
    else
        wget -qO "$ARCHIVE" "$REPO_URL/archive/refs/heads/main.tar.gz" \
            || die "download failed."
    fi
    tar -xzf "$ARCHIVE" -C "$TMP" || die "could not unpack the download."
    mv "$TMP"/ClutterCutter-* "$TMP/ClutterCutter" 2>/dev/null || true
fi

SRC="$TMP/ClutterCutter"
[ -d "$SRC" ] || die "unexpected download layout."

# --- 3. install into a user venv -------------------------------------------
VENV="$HOME/.local/share/cluttercutter/venv"
say "Creating a private environment in ~/.local/share/cluttercutter/venv..."
mkdir -p "$(dirname "$VENV")" || die "could not create ~/.local/share"
"$PYTHON" -m venv "$VENV" 2>/dev/null \
    || die "Could not create a virtualenv. On Debian/Ubuntu install python3-venv."

# tkinter cannot be pip-installed; it is a system package. Install the CLI
# regardless and report the GUI situation afterwards rather than failing here.
say "Installing..."
"$VENV/bin/python" -m pip install --quiet --upgrade pip >/dev/null 2>&1
if ! "$VENV/bin/python" -m pip install --quiet "$SRC"; then
    warn "pip install failed. Falling back to running straight from the source folder."
    mkdir -p "$INSTALL_DIR" || die "could not create $INSTALL_DIR"
    cat > "$INSTALL_DIR/cluttercutter-cli" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/python" -m cluttercutter "\$@"
EOF
    chmod +x "$INSTALL_DIR/cluttercutter-cli"
    say "Installed the CLI only, to $INSTALL_DIR/cluttercutter-cli"
    exit 0
fi

# --- 4. link the console scripts -------------------------------------------
mkdir -p "$INSTALL_DIR" || die "could not create $INSTALL_DIR"
for name in cluttercutter cluttercutter-gui; do
    if [ -f "$VENV/bin/$name" ]; then
        ln -sf "$VENV/bin/$name" "$INSTALL_DIR/$name"
    fi
done
chmod +x "$INSTALL_DIR"/cluttercutter* 2>/dev/null || true

# --- 5. tkinter check, reported honestly ------------------------------------
say "Checking GUI support (tkinter)..."
if "$VENV/bin/python" -c 'import tkinter' >/dev/null 2>&1; then
    say "GUI available:  cluttercutter-gui"
else
    warn "tkinter is missing, so the GUI will not start yet."
    warn "The CLI works now:  cluttercutter ~/Downloads"
    warn ""
    warn "To enable the GUI, install tkinter with your package manager:"
    warn "  Debian/Ubuntu   sudo apt install python3-tk"
    warn "  Fedora          sudo dnf install python3-tkinter"
    warn "  Arch            sudo pacman -S tk"
    warn "  macOS           brew install python-tk"
fi

# --- 6. make sure the new PATH is picked up -------------------------------
case ":$PATH:" in
    *":$INSTALL_DIR:"*) ;;
    *)
        warn ""
        warn "$INSTALL_DIR is not on your PATH. Add this to your ~/.bashrc:"
        warn "    export PATH=\"\$HOME/.local/bin:\$PATH\""
        warn "then run:  source ~/.bashrc"
        ;;
esac

say ""
say "Installed to $INSTALL_DIR"
say "Try it:  cluttercutter ~/Downloads          # preview, moves nothing"
say "         cluttercutter ~/Downloads --apply # actually sort"