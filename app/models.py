"""
Pydantic models for API request / response schemas.

Designed for easy frontend integration:
- SummarizeResponse includes repo metadata so the UI can display
  repo info alongside the LLM summary without extra API calls.
- ErrorResponse uses a consistent shape across all failure modes.
"""

from pydantic import BaseModel, Field, field_validator
import re


# ── Request ───────────────────────────────────────────────────────────

class SummarizeRequest(BaseModel):
    """POST /summarize request body."""

    github_url: str = Field(
        ...,
        description="Full URL of a public GitHub repository",
        examples=["https://github.com/psf/requests"],
    )

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        """Ensure the URL looks like a valid GitHub repository URL."""
        pattern = r"^https?://github\.com/[\w.\-]+/[\w.\-]+/?$"
        if not re.match(pattern, v.strip()):
            raise ValueError(
                "Invalid GitHub repository URL. "
                "Expected format: https://github.com/{owner}/{repo}"
            )
        return v.strip().rstrip("/")


# ── Response ──────────────────────────────────────────────────────────

class RepoMetadata(BaseModel):
    """Basic repository metadata for frontend display."""

    name: str = Field(..., description="Repository name")
    owner: str = Field(..., description="Repository owner / organisation")
    url: str = Field(..., description="Canonical GitHub URL")
    stars: int = Field(0, description="Star count")
    language: str | None = Field(None, description="Primary language detected by GitHub")
    default_branch: str = Field("main", description="Default branch name")


class SummarizeResponse(BaseModel):
    """POST /summarize success response."""

    summary: str = Field(
        ...,
        description="Human-readable description of what the project does",
    )
    technologies: list[str] = Field(
        ...,
        description="Main technologies, languages, and frameworks used",
    )
    structure: str = Field(
        ...,
        description="Brief description of the project's directory structure",
    )
    repo_metadata: RepoMetadata = Field(
        ...,
        description="Basic repository info for frontend display",
    )


# ── Error ─────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Uniform error response — frontend can always check status == 'error'."""

    status: str = Field(default="error", description="Always 'error' for error responses")
    message: str = Field(..., description="Human-readable error description")
