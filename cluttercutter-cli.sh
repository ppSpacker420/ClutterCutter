#!/usr/bin/env bash
# ============================================================================
#  ClutterCutter - CLI launcher (Linux / macOS)
#
#  ./cluttercutter-cli.sh ~/Downloads
#  ./cluttercutter-cli.sh ~/Downloads --apply
#
#  Without --apply this only previews what would happen. Nothing is moved.
# ============================================================================
set -uo pipefail

SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
HERE="$(cd -P "$(dirname "$SOURCE")" && pwd)"

if [ $# -eq 0 ]; then
    cat <<'EOF'
Usage: cluttercutter-cli.sh <folder> [options]

Options:
  --apply               actually move the files (prompts first)
  --yes                 skip the confirmation prompt
  --include-protected   also move files whose type could not be identified
  --recursive           descend into subfolders
  --json                output the plan as JSON

Without --apply this only previews what would happen. Nothing is moved.
EOF
    exit 2
fi

# Prefer the installed console script.
if command -v cluttercutter >/dev/null 2>&1; then
    exec cluttercutter "$@"
fi

# A virtualenv next to us.
for candidate in "$HERE/.venv/bin/python" "$HERE/venv/bin/python"; do
    if [ -x "$candidate" ]; then
        cd "$HERE" || exit 1
        exec "$candidate" -m cluttercutter "$@"
    fi
done

PY=""
for c in python3 python; do
    command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }
done

if [ -z "$PY" ]; then
    echo "ClutterCutter could not find Python 3." >&2
    echo "  Debian/Ubuntu   sudo apt install python3" >&2
    echo "  Fedora          sudo dnf install python3" >&2
    echo "  Arch            sudo pacman -S python" >&2
    exit 1
fi

# Note: no tkinter check here. The CLI does not use tkinter, and demanding it
# would break the CLI on a machine that only wants to script it.
cd "$HERE" || exit 1
exec "$PY" -m cluttercutter "$@"