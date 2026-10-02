#!/usr/bin/env bash
# ============================================================================
#  ClutterCutter - GUI launcher (Linux / macOS)
#
#  ./cluttercutter.sh
#
#  Runs from a clone with no install step. If ClutterCutter is installed via
#  pip or pipx, the installed `cluttercutter-gui` command is preferred.
# ============================================================================
set -uo pipefail

# Resolve this script's directory even when reached through a symlink, so it
# works from a PATH entry or a ~/bin symlink.
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
HERE="$(cd -P "$(dirname "$SOURCE")" && pwd)"

# ---------------------------------------------------------------------------
# 1. Already installed as a console script? Use it.
# ---------------------------------------------------------------------------
if command -v cluttercutter-gui >/dev/null 2>&1; then
    exec cluttercutter-gui "$@"
fi

# ---------------------------------------------------------------------------
# 2. A virtualenv next to us?
# ---------------------------------------------------------------------------
for candidate in "$HERE/.venv/bin/python" "$HERE/venv/bin/python"; do
    if [ -x "$candidate" ]; then
        cd "$HERE" || exit 1
        exec "$candidate" -m cluttercutter.gui "$@"
    fi
done

# ---------------------------------------------------------------------------
# 3. A system Python. tkinter is required for the GUI and is packaged
#    separately on most Linux distributions - tell the user how to get it
#    rather than dying with an ImportError.
# ---------------------------------------------------------------------------
PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then
        if "$c" -c "import tkinter" >/dev/null 2>&1; then
            PY="$c"
            break
        fi
        # Found a Python but no tkinter - keep looking, then explain.
        [ -z "$PY" ] && PY="$c"
    fi
done

if [ -z "$PY" ]; then
    cat >&2 <<'EOF'
ClutterCutter could not find Python 3.

Install it with one of:
  Debian/Ubuntu   sudo apt install python3 python3-tk
  Fedora          sudo dnf install python3 python3-tkinter
  Arch            sudo pacman -S python tk
  macOS           brew install python-tk
EOF
    exit 1
fi

if ! "$PY" -c "import tkinter" >/dev/null 2>&1; then
    cat >&2 <<EOF
ClutterCutter needs Python's tkinter module for its GUI, and it is missing
from: $PY

Install it with one of:
  Debian/Ubuntu   sudo apt install python3-tk
  Fedora          sudo dnf install python3-tkinter
  Arch            sudo pacman -S tk
  macOS           brew install python-tk

The command line interface does not need tkinter - try ./cluttercutter-cli.sh
EOF
    exit 1
fi

cd "$HERE" || exit 1
exec "$PY" -m cluttercutter.gui "$@"