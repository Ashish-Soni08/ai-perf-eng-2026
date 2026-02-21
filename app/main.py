"""
FastAPI application — GitHub Repository Summarizer API.

Endpoints:
  GET  /health     → health check
  POST /summarize  → analyze a GitHub repo and return LLM-generated summary

Features:
  - CORS enabled for frontend integration
  - Consistent error response shape across all failure modes
  - Structured logging
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models import (
    SummarizeRequest,
    SummarizeResponse,
    RepoMetadata,
    ErrorResponse,
)
from app.github_fetcher import (
    parse_github_url,
    fetch_repo_data,
    fetch_files_content,
    GitHubFetchError,
)
from app.content_filter import select_files, build_context
from app.llm_client import generate_summary, LLMError


# ── Logging ───────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("app")


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info("🚀 GitHub Repo Summarizer API starting up")
    yield
    logger.info("👋 Shutting down")


# ── App Instance ──────────────────────────────────────────────────────

app = FastAPI(
    title="GitHub Repository Summarizer",
    description=(
        "Analyze a public GitHub repository and return a structured summary "
        "of what it does, its technologies, and project structure."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins by default for easy frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Error Handlers ────────────────────────────────────────────────────


@app.exception_handler(GitHubFetchError)
async def github_error_handler(request: Request, exc: GitHubFetchError):
    """Handle GitHub API errors with consistent error shape."""
    logger.warning("GitHub error: %s (status=%d)", exc.message, exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=exc.message).model_dump(),
    )


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    """Handle LLM errors with consistent error shape."""
    logger.error("LLM error: %s (status=%d)", exc.message, exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=exc.message).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with consistent error shape."""
    messages = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
        for e in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(message=f"Validation error: {messages}").model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    """Wrap FastAPI HTTPExceptions in our consistent error shape."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=str(exc.detail)).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Catch-all for unexpected errors."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="An unexpected error occurred. Please try again."
        ).model_dump(),
    )


# ── Endpoints ─────────────────────────────────────────────────────────


@app.get("/health")
async def health_check():
    """Simple health check for frontend connectivity testing."""
    return {"status": "ok"}


@app.post(
    "/summarize",
    response_model=SummarizeResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Repository not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        502: {"model": ErrorResponse, "description": "LLM service error"},
        504: {"model": ErrorResponse, "description": "Timeout"},
    },
)
async def summarize_repo(body: SummarizeRequest):
    """
    Analyze a public GitHub repository and return a structured summary.

    Pipeline:
      1. Parse the GitHub URL → extract owner/repo
      2. Fetch repository metadata and file tree from GitHub API
      3. Filter and prioritise files for LLM context
      4. Fetch selected file contents from GitHub
      5. Build context string and send to LLM
      6. Return structured response with repo metadata
    """
    # Step 1: Parse URL
    owner, repo = parse_github_url(body.github_url)
    logger.info("Summarizing %s/%s", owner, repo)

    # Step 2: Fetch repo metadata and file tree
    metadata, tree = await fetch_repo_data(owner, repo)
    logger.info(
        "Fetched metadata and tree: %d entries, branch=%s",
        len(tree),
        metadata["default_branch"],
    )

    # Check for empty repo
    if not tree:
        raise GitHubFetchError(
            "Repository appears to be empty (no files found).",
            status_code=422,
        )

    # Step 3: Filter and prioritise files
    selected = select_files(tree)
    file_paths = [f["path"] for f in selected]
    logger.info(
        "Selected %d files for context (from %d total tree entries)",
        len(selected),
        len(tree),
    )

    # Step 4: Fetch file contents
    file_contents = await fetch_files_content(
        owner, repo, metadata["default_branch"], file_paths
    )
    logger.info("Fetched content for %d files", len(file_contents))

    # Step 5: Build context and call LLM
    context = build_context(metadata, tree, file_contents, selected)
    logger.info("Built context: %d chars", len(context))

    llm_result = await generate_summary(context)

    # Step 6: Build response with repo metadata
    repo_metadata = RepoMetadata(
        name=metadata["name"],
        owner=metadata["owner"],
        url=metadata["url"],
        stars=metadata["stars"],
        language=metadata.get("language"),
        default_branch=metadata["default_branch"],
    )

    return SummarizeResponse(
        summary=llm_result["summary"],
        technologies=llm_result["technologies"],
        structure=llm_result["structure"],
        repo_metadata=repo_metadata,
    )
