"""Standalone entry point for the CLI.

PyInstaller bundles a single script rather than a package, so this file does
the import that the package-relative modules cannot do themselves. Point
PyInstaller at THIS file, not at cluttercutter/cli.py:

    pyinstaller --onefile cluttercutter-cli-entry.py

Equivalent to `python -m cluttercutter`.
"""

import os
import sys

# Run correctly whether or not the package is installed, and whether or not
# the process was started from the project directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cluttercutter.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())