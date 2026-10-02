"""Standalone entry point for the GUI.

PyInstaller bundles a single script rather than a package, so this file does
the import that the package-relative modules cannot do themselves. Point
PyInstaller at THIS file, not at cluttercutter/gui.py:

    pyinstaller --onefile --windowed cluttercutter-gui-entry.py

Equivalent to `python -m cluttercutter.gui`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cluttercutter.gui import main  # noqa: E402

if __name__ == "__main__":
    main()