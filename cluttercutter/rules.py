"""Category rules.

The whole rule table lives here so it can be shown on screen during a
demo in one glance, and edited without touching engine code.

PROTECTED is special: it is a destination, not a licence. Files that land in
PROTECTED are not moved at all unless the caller explicitly opts in
(via --include-protected). The default is to leave them alone.
"""

from __future__ import annotations

CATEGORIES: dict[str, tuple[str, ...]] = {
    "Images": (
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg",
        ".heic", ".heif", ".tiff", ".tif", ".ico", ".raw", ".cr2", ".nef",
    ),
    "Video": (
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
        ".m4v", ".mpg", ".mpeg", ".3gp",
    ),
    "Audio": (
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
        ".wma", ".opus", ".aiff",
    ),
    "Documents": (
        ".pdf", ".doc", ".docx", ".odt", ".txt", ".rtf", ".md",
        ".epub", ".pages",
    ),
    "Spreadsheets": (
        ".xls", ".xlsx", ".ods", ".csv", ".tsv", ".numbers",
    ),
    "Presentations": (
        ".ppt", ".pptx", ".odp", ".key",
    ),
    "Archives": (
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
        ".iso", ".dmg",
    ),
    "Code": (
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".h",
        ".cpp", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".sh",
        ".bat", ".ps1", ".json", ".yaml", ".yml", ".toml", ".ini",
        ".html", ".css", ".sql",
    ),
    "Fonts": (".ttf", ".otf", ".woff", ".woff2", ".fon"),
}

# Anything not matched above goes here and is NOT moved by default.
PROTECTED = "Protected"

# Extension -> category, precomputed lookup.
EXTENSION_MAP: dict[str, str] = {}
for _cat, _exts in CATEGORIES.items():
    for _ext in _exts:
        EXTENSION_MAP.setdefault(_ext, _cat)

# Categories whose contents are safe to move without asking.
MOVERABLE = frozenset(CATEGORIES)

ORGANISED_MARKERS = frozenset(c.lower() for c in CATEGORIES) | {PROTECTED.lower()}


def categorise(filename: str) -> str:
    """Return the category for a filename, or PROTECTED if unknown.

    Rule 4 safety: we only return a real category when we are confident.
    An unrecognised extension is never guessed at.
    """
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    dot = name.rfind(".")
    # No extension, or a dotfile like ".gitignore" -> unclassified.
    if dot <= 0:
        return PROTECTED
    ext = name[dot:].lower()
    return EXTENSION_MAP.get(ext, PROTECTED)