"""
Content filtering and context building for LLM consumption.

This module implements a tiered file prioritization strategy:
1. Skip irrelevant files (binary, lock files, generated code, etc.)
2. Prioritise files by information value (README → manifests → configs → source)
3. Build a structured context string within a character budget

The goal is to give the LLM the *best possible understanding* of the project
while staying well within the context window.
"""

import os
from app.config import MAX_CONTEXT_CHARS, MAX_TREE_LINES, MAX_FILE_LINES


# ── Skip Rules ────────────────────────────────────────────────────────

# Directories to always skip entirely
SKIP_DIRS: set[str] = {
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".git",
    "__pycache__",
    ".next",
    ".nuxt",
    ".output",
    ".cache",
    ".tox",
    ".nox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".eggs",
    "eggs",
    ".venv",
    "venv",
    "env",
    ".env",
    "site-packages",
    "coverage",
    "htmlcov",
    ".terraform",
    ".gradle",
    ".idea",
    ".vscode",
    "target",          # Java/Rust build output
    "out",             # Common build output
    "bin",             # Compiled binaries
    "obj",             # .NET build intermediate
}

# File extensions to always skip (binary / non-informative)
SKIP_EXTENSIONS: set[str] = {
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".bmp", ".webp", ".tiff",
    # Fonts
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    # Compiled / binary
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".o", ".a", ".lib",
    ".class", ".jar", ".war", ".ear",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".rar", ".7z",
    # Data / media
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Database
    ".sqlite", ".sqlite3", ".db",
    # Maps / minified
    ".map", ".min.js", ".min.css",
    # Misc
    ".DS_Store", ".lock",
}

# Exact filenames to always skip
SKIP_FILES: set[str] = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Pipfile.lock",
    "poetry.lock",
    "Cargo.lock",
    "composer.lock",
    "Gemfile.lock",
    "go.sum",
    "flake.lock",
    ".gitattributes",
    ".editorconfig",
    ".browserslistrc",
    "thumbs.db",
}


# ── Priority Tiers ────────────────────────────────────────────────────

# Tier 1: Project overview (always include)
TIER_1_FILES: set[str] = {
    "readme.md", "readme.rst", "readme.txt", "readme",
}

# Tier 2: Package manifests (technologies & dependencies)
TIER_2_FILES: set[str] = {
    "package.json",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "gemfile",
    "composer.json",
    "mix.exs",
    "project.clj",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements_dev.txt",
    "pipfile",
    "environment.yml",
}

# Tier 3: Config / infrastructure files (architecture & tooling)
TIER_3_FILES: set[str] = {
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".env.example",
    ".env.sample",
    "makefile",
    "procfile",
    "tsconfig.json",
    "webpack.config.js",
    "vite.config.ts",
    "vite.config.js",
    "next.config.js",
    "next.config.mjs",
    "rollup.config.js",
    "babel.config.js",
    ".babelrc",
    "jest.config.js",
    "jest.config.ts",
    "vitest.config.ts",
    "tox.ini",
    "noxfile.py",
    "justfile",
    "taskfile.yml",
    "vercel.json",
    "netlify.toml",
    "fly.toml",
    "render.yaml",
    "app.yaml",
    "serverless.yml",
    "cdk.json",
    "terraform.tf",
    "ansible.cfg",
}

# Tier 4: Source code entry points (core logic)
TIER_4_BASENAMES: set[str] = {
    "main", "app", "index", "server", "cli", "run", "manage",
    "__main__", "wsgi", "asgi",
}

# Source code extensions for Tier 4/5
SOURCE_EXTENSIONS: set[str] = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".go", ".rs", ".rb", ".java", ".kt",
    ".c", ".cpp", ".h", ".hpp", ".cs",
    ".swift", ".scala", ".clj", ".ex", ".exs",
    ".php", ".lua", ".r", ".jl",
    ".sh", ".bash", ".zsh", ".fish",
    ".sql", ".graphql", ".gql",
    ".proto",
}

# Tier 6: Supplementary docs (low priority)
TIER_6_FILES: set[str] = {
    "contributing.md",
    "changelog.md",
    "changes.md",
    "history.md",
    "authors.md",
    "code_of_conduct.md",
    "security.md",
    "license",
    "license.md",
    "license.txt",
    "notice",
}


# ── Filtering Logic ──────────────────────────────────────────────────


def _should_skip(path: str) -> bool:
    """Return True if this file/dir path should be excluded from context."""
    parts = path.lower().split("/")

    # Skip if any path segment matches a skipped directory
    for part in parts[:-1]:  # Check directory segments, not the filename
        if part in SKIP_DIRS:
            return True

    filename = parts[-1]
    _, ext = os.path.splitext(filename)

    # Skip by exact filename
    if filename in SKIP_FILES:
        return True

    # Skip by extension
    if ext in SKIP_EXTENSIONS:
        return True

    return False


def _get_tier(path: str, size: int) -> int:
    """
    Assign a priority tier (1=highest, 6=lowest, 99=skip) to a file.
    Lower tier = more important = fetched first.
    """
    filename = os.path.basename(path).lower()
    basename_no_ext, ext = os.path.splitext(filename)

    if filename in TIER_1_FILES:
        return 1
    if filename in TIER_2_FILES:
        return 2
    if filename in TIER_3_FILES:
        return 3

    # Tier 4: Entry point source files
    if basename_no_ext in TIER_4_BASENAMES and ext in SOURCE_EXTENSIONS:
        return 4

    # Tier 4 bonus: root-level __init__.py (package overview)
    if filename == "__init__.py" and "/" not in path:
        return 4

    # Tier 5: Other source files
    if ext in SOURCE_EXTENSIONS:
        return 5

    # Tier 6: Supplementary docs
    if filename in TIER_6_FILES:
        return 6

    # Everything else: skip for LLM context
    return 99


def select_files(tree: list[dict]) -> list[dict]:
    """
    Filter and prioritise files from the repository tree.

    Returns a list of file entries sorted by priority tier, then by path.
    Each entry has keys: path, size, tier.
    """
    candidates = []

    for item in tree:
        if item["type"] != "blob":
            continue

        path = item["path"]
        size = item.get("size", 0)

        if _should_skip(path):
            continue

        tier = _get_tier(path, size)
        if tier == 99:
            continue

        candidates.append({
            "path": path,
            "size": size,
            "tier": tier,
        })

    # Sort by tier (ascending), then alphabetically within each tier
    candidates.sort(key=lambda f: (f["tier"], f["path"]))
    return candidates


# ── Directory Tree Formatting ─────────────────────────────────────────


def format_tree(tree: list[dict]) -> str:
    """
    Build a clean directory tree string from the GitHub tree data.

    Skips entries inside ignored directories and truncates if too long.
    """
    lines: list[str] = []

    for item in tree:
        path = item["path"]

        # Skip entries inside ignored directories
        parts = path.split("/")
        if any(p.lower() in SKIP_DIRS for p in parts[:-1]):
            continue

        # Skip binary / noise files in the tree view too
        filename = parts[-1].lower()
        _, ext = os.path.splitext(filename)
        if ext in SKIP_EXTENSIONS or filename in SKIP_FILES:
            continue

        # Indent based on depth
        depth = len(parts) - 1
        prefix = "  " * depth
        name = parts[-1]

        if item["type"] == "tree":
            lines.append(f"{prefix}{name}/")
        else:
            size = item.get("size", 0)
            if size > 0:
                size_str = _format_size(size)
                lines.append(f"{prefix}{name}  ({size_str})")
            else:
                lines.append(f"{prefix}{name}")

        if len(lines) >= MAX_TREE_LINES:
            lines.append(f"  ... (truncated, {len(tree)} total entries)")
            break

    return "\n".join(lines)


def _format_size(size_bytes: int) -> str:
    """Format byte count into human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# ── Context Building ─────────────────────────────────────────────────


def truncate_file_content(content: str, max_lines: int = MAX_FILE_LINES) -> str:
    """Truncate file content to a maximum number of lines."""
    lines = content.split("\n")
    if len(lines) <= max_lines:
        return content
    truncated = "\n".join(lines[:max_lines])
    truncated += f"\n\n... (truncated, {len(lines)} total lines)"
    return truncated


def build_context(
    metadata: dict,
    tree: list[dict],
    file_contents: dict[str, str],
    selected_files: list[dict],
) -> str:
    """
    Build the final context string to send to the LLM.

    Structure:
      1. Repository metadata
      2. Directory tree
      3. File contents (in priority order, within budget)

    Returns the context string, staying within MAX_CONTEXT_CHARS.
    """
    sections: list[str] = []
    total_chars = 0

    # ── Section 1: Metadata ───────────────────────────────────────────
    meta_section = _build_metadata_section(metadata)
    sections.append(meta_section)
    total_chars += len(meta_section)

    # ── Section 2: Directory tree ─────────────────────────────────────
    tree_str = format_tree(tree)
    tree_section = f"=== DIRECTORY STRUCTURE ===\n{tree_str}\n"
    sections.append(tree_section)
    total_chars += len(tree_section)

    # ── Section 3: File contents (priority order) ─────────────────────
    file_section_header = "=== FILE CONTENTS ===\n"
    sections.append(file_section_header)
    total_chars += len(file_section_header)

    for file_info in selected_files:
        path = file_info["path"]
        if path not in file_contents:
            continue

        content = file_contents[path]
        content = truncate_file_content(content)

        file_block = f"--- {path} ---\n{content}\n\n"
        block_len = len(file_block)

        # Check budget before adding
        if total_chars + block_len > MAX_CONTEXT_CHARS:
            # For high-priority files (tier 1–3), try harder: truncate more
            if file_info["tier"] <= 3:
                available = MAX_CONTEXT_CHARS - total_chars - 200  # Leave room for header
                if available > 500:
                    content = content[:available]
                    file_block = f"--- {path} (truncated to fit budget) ---\n{content}\n\n"
                    sections.append(file_block)
                    total_chars += len(file_block)
            # For lower-priority files, just stop
            remaining = sum(
                1 for f in selected_files
                if f["path"] in file_contents and f["path"] != path
            )
            sections.append(
                f"... ({remaining} additional files omitted due to context budget)\n"
            )
            break

        sections.append(file_block)
        total_chars += block_len

    return "\n".join(sections)


def _build_metadata_section(metadata: dict) -> str:
    """Format repository metadata as a context section."""
    lines = [
        "=== REPOSITORY METADATA ===",
        f"Name: {metadata.get('name', 'Unknown')}",
        f"Owner: {metadata.get('owner', 'Unknown')}",
    ]
    desc = metadata.get("description")
    if desc:
        lines.append(f"Description: {desc}")

    lang = metadata.get("language")
    if lang:
        lines.append(f"Primary Language: {lang}")

    topics = metadata.get("topics", [])
    if topics:
        lines.append(f"Topics: {', '.join(topics)}")

    stars = metadata.get("stars", 0)
    lines.append(f"Stars: {stars}")
    lines.append("")  # trailing newline
    return "\n".join(lines)
