"""Detect folders that must not be taken apart.

The problem this solves: ClutterCutter sorts by file extension, but real
code lives in folders whose parts depend on each other. Splitting them
silently breaks them.

    mysite/                    <- index.html needs style.css and app.js
      index.html                     Without --recursive: untouched, because
      style.css                      we only ever look at the top level.
      app.js
      logo.png                       With --recursive: without this module the
      data.json                      image and the JSON would be pulled out
                                     from under the HTML and the page breaks.

    myproject/                 <- requirements.txt must sit beside main.py
      main.py                       Splitting them moves requirements.txt to
      requirements.txt             Documents/ and `pip install -r` fails.
      utils.py
      config.yaml

So: a folder containing a recognised project marker is treated as ONE
ATOMIC UNIT. If it is not safe to move a whole folder, we do not move any of
it.

Detection is deliberately conservative. A false negative (missing a project
we should have spared) merely means the folder gets sorted, which is the old
behaviour. A false positive would mean refusing to tidy a folder full of
screenshots, which is worse. So we only trigger on unambiguous markers.
"""

from __future__ import annotations

from pathlib import Path

# A file whose presence means "this folder is a project".
# Keys are lowercase. Matched against the filename exactly.
PROJECT_MARKERS: frozenset[str] = frozenset({
    # Python
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "pipfile", "poetry.lock", "environment.yml",
    # Node / frontend
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "vite.config.js", "vite.config.ts", "webpack.config.js",
    "tsconfig.json", "next.config.js",
    # Java / JVM
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    # Rust / Go / Ruby / PHP
    "cargo.toml", "cargo.lock", "go.mod", "go.sum",
    "gemfile", "composer.json",
    # C / C++
    "cmakelists.txt", "makefile",
    # Other ecosystems
    "composer.lock", "pubspec.yaml", "build.gradle.settings",
    # Generic project roots
    ".git", ".hg", ".svn",
})

# Folders that are almost certainly a single deployable artifact. Their
# contents are interdependent even though the folder has no marker file.
UNIT_NAMES: frozenset[str] = frozenset({
    "node_modules", "venv", ".venv", "env", "site-packages",
    "dist", "build", "target", "__pycache__", "vendor", "migrations",
    "static", "assets", "public", "templates", "locale", "locales",
})

# A web page with no config file is still a web page. If the folder holds an
# .html file, treat the whole folder as a unit - the HTML's references to
# sibling css/js/images break the moment those files are moved elsewhere.
WEB_ENTRY_EXTENSIONS: frozenset[str] = frozenset({".html", ".htm"})


def is_project_unit(folder: Path) -> tuple[bool, str]:
    """Decide whether ``folder`` must be kept whole.

    Returns:
        (True, reason) if the folder is an atomic unit that must not be split.
        (False, "") otherwise.

    Never raises: an unreadable folder is reported as a unit, because failing
    to inspect a folder is a reason not to touch it.
    """
    try:
        if not folder.is_dir():
            return False, ""
        entries = list(folder.iterdir())
    except (OSError, PermissionError):
        return True, "folder could not be inspected - left whole"

    names = {e.name.lower() for e in entries}

    # An explicit project marker.
    for marker in PROJECT_MARKERS:
        if marker in names:
            return True, f"project folder (contains {marker}) - kept whole"

    # A name that implies a self-contained artifact.
    lowered = folder.name.lower()
    if lowered in UNIT_NAMES:
        return True, f"'{folder.name}' is a self-contained unit - kept whole"

    # A web page: the HTML references its siblings by relative path.
    for entry in entries:
        if entry.is_file() and entry.suffix.lower() in WEB_ENTRY_EXTENSIONS:
            return True, "contains a web page that references sibling files - kept whole"

    return False, ""


def dependency_warning(folder: Path) -> str | None:
    """A human-readable note about why ``folder`` will not be sorted.

    Returns None when the folder is safe to sort normally.
    """
    is_unit, reason = is_project_unit(folder)
    return reason if is_unit else None


def is_project_root(folder: Path) -> bool:
    """True when ``folder`` is itself a project the user pointed us at.

    Stricter than :func:`is_project_unit`: it requires an explicit marker
    file (package.json, requirements.txt, pom.xml, ...) rather than the
    softer signals. Used to protect the scan root, where a false positive
    would leave a genuinely messy folder untouched.
    """
    try:
        names = {e.name.lower() for e in folder.iterdir()}
    except (OSError, PermissionError):
        return True  # cannot inspect -> do not touch
    if names & PROJECT_MARKERS:
        return True
    return folder.name.lower() in UNIT_NAMES