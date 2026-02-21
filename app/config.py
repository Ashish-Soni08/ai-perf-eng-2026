"""
Application configuration loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Nebius Token Factory ──────────────────────────────────────────────
NEBIUS_API_KEY: str = os.environ.get("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL: str = "https://api.tokenfactory.eu-west1.nebius.com/v1/"

# Model to use for summarization — will be set after reviewing available models
LLM_MODEL: str = "moonshotai/Kimi-K2.5"

LLM_TEMPERATURE: float = 0.3  # Low temperature for consistent structured output
LLM_MAX_TOKENS: int = 8192    # Reasoning models need headroom for thinking + answer
LLM_TIMEOUT: int = 120        # Seconds to wait for LLM response

# ── GitHub API ────────────────────────────────────────────────────────
GITHUB_TOKEN: str | None = os.environ.get("GITHUB_TOKEN")  # Optional, for higher rate limits
GITHUB_API_BASE: str = "https://api.github.com"
GITHUB_REQUEST_TIMEOUT: int = 30  # Seconds per GitHub API request

# ── Content Filtering ────────────────────────────────────────────────
# Approximate character budget for the LLM context window.
# 1 token ≈ 4 chars — for a 128K token model, ~240K chars is safe,
# but we leave room for the system prompt + response.
MAX_CONTEXT_CHARS: int = 200_000

# Max lines to include from the directory tree listing
MAX_TREE_LINES: int = 500

# Max lines to include per individual source file
MAX_FILE_LINES: int = 300

# Max individual file size (bytes) to even attempt fetching
MAX_FILE_SIZE_BYTES: int = 512_000  # 500 KB
