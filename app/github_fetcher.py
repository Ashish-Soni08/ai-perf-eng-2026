"""
GitHub API interaction — fetch repository metadata, file tree, and file contents.

Uses the GitHub REST API (v3) with optional token authentication.
All functions are async and use httpx for HTTP requests.
"""

import re
from urllib.parse import urlparse

import httpx

from app.config import (
    GITHUB_API_BASE,
    GITHUB_REQUEST_TIMEOUT,
    GITHUB_TOKEN,
    MAX_FILE_SIZE_BYTES,
)


class GitHubFetchError(Exception):
    """Raised when a GitHub API request fails."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ── URL Parsing ───────────────────────────────────────────────────────


def parse_github_url(url: str) -> tuple[str, str]:
    """
    Extract (owner, repo) from a GitHub URL.

    Supports:
      - https://github.com/owner/repo
      - https://github.com/owner/repo/
      - https://github.com/owner/repo.git
      - http://github.com/owner/repo

    Raises GitHubFetchError for malformed URLs.
    """
    url = url.strip().rstrip("/")

    # Remove trailing .git if present
    if url.endswith(".git"):
        url = url[:-4]

    parsed = urlparse(url)
    if parsed.hostname not in ("github.com", "www.github.com"):
        raise GitHubFetchError(
            "URL must be a github.com repository URL.",
            status_code=400,
        )

    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise GitHubFetchError(
            "Could not extract owner/repo from the URL. "
            "Expected format: https://github.com/{owner}/{repo}",
            status_code=400,
        )

    owner, repo = parts[0], parts[1]

    # Basic sanity check on owner/repo names
    name_pattern = re.compile(r"^[\w.\-]+$")
    if not name_pattern.match(owner) or not name_pattern.match(repo):
        raise GitHubFetchError(
            f"Invalid owner or repo name: {owner}/{repo}",
            status_code=400,
        )

    return owner, repo


# ── HTTP Client Helpers ───────────────────────────────────────────────


def _build_headers() -> dict[str, str]:
    """Build request headers, including auth token if available."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "github-repo-summarizer/1.0",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


async def _github_get(client: httpx.AsyncClient, endpoint: str) -> dict:
    """
    Perform a GET request against the GitHub API.

    Raises GitHubFetchError with appropriate status codes on failure.
    """
    url = f"{GITHUB_API_BASE}{endpoint}"
    try:
        response = await client.get(
            url,
            headers=_build_headers(),
            timeout=GITHUB_REQUEST_TIMEOUT,
        )
    except httpx.TimeoutException:
        raise GitHubFetchError(
            "GitHub API request timed out. Please try again.",
            status_code=504,
        )
    except httpx.RequestError as exc:
        raise GitHubFetchError(
            f"Network error while contacting GitHub: {exc}",
            status_code=502,
        )

    if response.status_code == 404:
        raise GitHubFetchError(
            "Repository not found. Make sure the URL points to a public repository.",
            status_code=404,
        )
    if response.status_code == 403:
        raise GitHubFetchError(
            "GitHub API rate limit exceeded. "
            "Set the GITHUB_TOKEN environment variable for higher limits.",
            status_code=429,
        )
    if response.status_code != 200:
        raise GitHubFetchError(
            f"GitHub API returned status {response.status_code}.",
            status_code=response.status_code,
        )

    return response.json()


# ── Public API ────────────────────────────────────────────────────────


async def fetch_repo_metadata(
    client: httpx.AsyncClient, owner: str, repo: str
) -> dict:
    """
    Fetch basic repository metadata.

    Returns a dict with keys:
      name, owner, url, description, default_branch, language, stars, topics
    """
    data = await _github_get(client, f"/repos/{owner}/{repo}")

    return {
        "name": data.get("name", repo),
        "owner": data.get("owner", {}).get("login", owner),
        "url": data.get("html_url", f"https://github.com/{owner}/{repo}"),
        "description": data.get("description") or "",
        "default_branch": data.get("default_branch", "main"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count", 0),
        "topics": data.get("topics", []),
    }


async def fetch_file_tree(
    client: httpx.AsyncClient, owner: str, repo: str, branch: str
) -> list[dict]:
    """
    Fetch the full recursive file tree for the repository.

    Returns a list of dicts, each with keys:
      path, type ("blob" or "tree"), size (bytes, only for blobs)
    """
    data = await _github_get(
        client, f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    )

    if data.get("truncated", False):
        # GitHub truncates trees with >100K entries — still usable, just incomplete
        pass

    tree = []
    for item in data.get("tree", []):
        entry = {
            "path": item["path"],
            "type": item["type"],  # "blob" or "tree"
        }
        if item["type"] == "blob":
            entry["size"] = item.get("size", 0)
        tree.append(entry)

    return tree


async def fetch_file_content(
    client: httpx.AsyncClient, owner: str, repo: str, branch: str, file_path: str
) -> str | None:
    """
    Fetch the raw content of a single file from the repository.

    Returns the file content as a string, or None if the file is too large,
    binary, or cannot be fetched.
    """
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"

    try:
        response = await client.get(
            raw_url,
            timeout=GITHUB_REQUEST_TIMEOUT,
            headers={"User-Agent": "github-repo-summarizer/1.0"},
            follow_redirects=True,
        )
    except (httpx.TimeoutException, httpx.RequestError):
        return None

    if response.status_code != 200:
        return None

    # Skip files that are too large
    content_length = response.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE_BYTES:
        return None

    # Try to decode as text — skip binary files
    try:
        text = response.text
    except (UnicodeDecodeError, ValueError):
        return None

    # Quick binary content check (null bytes are a giveaway)
    if "\x00" in text[:8192]:
        return None

    return text


async def fetch_repo_data(
    owner: str, repo: str
) -> tuple[dict, list[dict]]:
    """
    High-level convenience function: fetch repo metadata + file tree.

    Returns (metadata_dict, tree_list).
    """
    async with httpx.AsyncClient() as client:
        metadata = await fetch_repo_metadata(client, owner, repo)
        tree = await fetch_file_tree(
            client, owner, repo, metadata["default_branch"]
        )
    return metadata, tree


async def fetch_files_content(
    owner: str,
    repo: str,
    branch: str,
    file_paths: list[str],
) -> dict[str, str]:
    """
    Fetch content for multiple files concurrently.

    Returns a dict mapping file_path → content (only for successfully fetched files).
    """
    import asyncio

    results: dict[str, str] = {}

    async with httpx.AsyncClient() as client:
        # Fetch in batches of 10 to be polite to GitHub
        batch_size = 10
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i : i + batch_size]
            tasks = [
                fetch_file_content(client, owner, repo, branch, fp)
                for fp in batch
            ]
            contents = await asyncio.gather(*tasks)
            for fp, content in zip(batch, contents):
                if content is not None:
                    results[fp] = content

    return results
