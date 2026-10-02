"""ClutterCutter - Automated Local Storage Manager.

Scans a cluttered directory, categorises the files it finds, and organises
them into per-category subfolders.

Safety contract (non-negotiable, enforced in code):
  1. Dry-run is the DEFAULT. Nothing moves without --apply.
  2. Only the folder you name is touched.
  3. Nothing is ever deleted or overwritten.
  4. Ambiguous files land in PROTECTED and are not moved unless you opt in.
  5. A locked/unreadable file is skipped and logged; it never aborts the run.
"""

__version__ = "1.0.0"
__all__ = ["__version__"]