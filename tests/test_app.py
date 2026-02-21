"""
Tests for the GitHub Repository Summarizer API.

These tests verify:
  - URL parsing and validation
  - Content filtering logic
  - API endpoint behaviour (health, error cases)
  - LLM response parsing

Tests that don't require network access or API keys are marked to run
without external dependencies. Integration tests that hit the real GitHub
API are separated.
"""

import pytest
import json

from app.github_fetcher import parse_github_url, GitHubFetchError
from app.content_filter import (
    select_files,
    format_tree,
    build_context,
    truncate_file_content,
    _should_skip,
    _get_tier,
)
from app.llm_client import _extract_json, _validate_response, LLMError
from app.models import SummarizeRequest, SummarizeResponse, RepoMetadata, ErrorResponse


# ═══════════════════════════════════════════════════════════════════════
#  URL Parsing Tests
# ═══════════════════════════════════════════════════════════════════════


class TestParseGitHubUrl:
    """Test parse_github_url with various URL formats."""

    def test_standard_url(self):
        owner, repo = parse_github_url("https://github.com/psf/requests")
        assert owner == "psf"
        assert repo == "requests"

    def test_url_with_trailing_slash(self):
        owner, repo = parse_github_url("https://github.com/psf/requests/")
        assert owner == "psf"
        assert repo == "requests"

    def test_url_with_git_suffix(self):
        owner, repo = parse_github_url("https://github.com/psf/requests.git")
        assert owner == "psf"
        assert repo == "requests"

    def test_http_url(self):
        owner, repo = parse_github_url("http://github.com/psf/requests")
        assert owner == "psf"
        assert repo == "requests"

    def test_url_with_whitespace(self):
        owner, repo = parse_github_url("  https://github.com/psf/requests  ")
        assert owner == "psf"
        assert repo == "requests"

    def test_url_with_subpath(self):
        """URLs with extra path segments should still extract owner/repo."""
        owner, repo = parse_github_url("https://github.com/psf/requests/tree/main")
        assert owner == "psf"
        assert repo == "requests"

    def test_hyphenated_names(self):
        owner, repo = parse_github_url("https://github.com/my-org/my-repo")
        assert owner == "my-org"
        assert repo == "my-repo"

    def test_dotted_names(self):
        owner, repo = parse_github_url("https://github.com/owner/repo.js")
        assert owner == "owner"
        assert repo == "repo.js"

    def test_invalid_url_not_github(self):
        with pytest.raises(GitHubFetchError, match="github.com"):
            parse_github_url("https://gitlab.com/owner/repo")

    def test_invalid_url_no_repo(self):
        with pytest.raises(GitHubFetchError, match="owner/repo"):
            parse_github_url("https://github.com/onlyowner")

    def test_invalid_url_empty(self):
        with pytest.raises(GitHubFetchError):
            parse_github_url("")

    def test_invalid_url_random_string(self):
        with pytest.raises(GitHubFetchError):
            parse_github_url("not-a-url-at-all")


# ═══════════════════════════════════════════════════════════════════════
#  Content Filter Tests
# ═══════════════════════════════════════════════════════════════════════


class TestShouldSkip:
    """Test file/directory skipping logic."""

    def test_skip_node_modules(self):
        assert _should_skip("node_modules/lodash/index.js") is True

    def test_skip_pycache(self):
        assert _should_skip("src/__pycache__/main.cpython-312.pyc") is True

    def test_skip_binary_extension(self):
        assert _should_skip("assets/logo.png") is True
        assert _should_skip("fonts/arial.woff2") is True
        assert _should_skip("build/output.exe") is True

    def test_skip_lock_file(self):
        assert _should_skip("package-lock.json") is True
        assert _should_skip("yarn.lock") is True
        assert _should_skip("poetry.lock") is True

    def test_keep_source_files(self):
        assert _should_skip("src/main.py") is False
        assert _should_skip("app/index.ts") is False
        assert _should_skip("lib/utils.go") is False

    def test_keep_readme(self):
        assert _should_skip("README.md") is False

    def test_keep_package_json(self):
        assert _should_skip("package.json") is False

    def test_keep_dockerfile(self):
        assert _should_skip("Dockerfile") is False

    def test_skip_dot_git(self):
        assert _should_skip(".git/config") is True

    def test_skip_venv(self):
        assert _should_skip(".venv/lib/python3.12/site.py") is True


class TestGetTier:
    """Test file priority tier assignment."""

    def test_readme_is_tier_1(self):
        assert _get_tier("README.md", 1000) == 1
        assert _get_tier("readme.rst", 1000) == 1

    def test_package_json_is_tier_2(self):
        assert _get_tier("package.json", 5000) == 2

    def test_pyproject_toml_is_tier_2(self):
        assert _get_tier("pyproject.toml", 3000) == 2

    def test_dockerfile_is_tier_3(self):
        assert _get_tier("Dockerfile", 500) == 3

    def test_main_py_is_tier_4(self):
        assert _get_tier("main.py", 2000) == 4
        assert _get_tier("src/app.js", 3000) == 4

    def test_source_file_is_tier_5(self):
        assert _get_tier("src/utils.py", 1000) == 5
        assert _get_tier("lib/helper.ts", 1500) == 5

    def test_license_is_tier_6(self):
        assert _get_tier("LICENSE", 1000) == 6
        assert _get_tier("CONTRIBUTING.md", 2000) == 6

    def test_unknown_file_is_tier_99(self):
        assert _get_tier("data.csv", 50000) == 99
        assert _get_tier("random.xyz", 100) == 99


class TestSelectFiles:
    """Test file selection and prioritisation."""

    def test_selects_readme_first(self):
        tree = [
            {"path": "src/utils.py", "type": "blob", "size": 1000},
            {"path": "README.md", "type": "blob", "size": 5000},
            {"path": "package.json", "type": "blob", "size": 2000},
        ]
        selected = select_files(tree)
        assert selected[0]["path"] == "README.md"
        assert selected[0]["tier"] == 1

    def test_skips_binary_files(self):
        tree = [
            {"path": "README.md", "type": "blob", "size": 1000},
            {"path": "logo.png", "type": "blob", "size": 50000},
            {"path": "app.exe", "type": "blob", "size": 100000},
        ]
        selected = select_files(tree)
        paths = [f["path"] for f in selected]
        assert "logo.png" not in paths
        assert "app.exe" not in paths

    def test_skips_directories(self):
        tree = [
            {"path": "src", "type": "tree"},
            {"path": "src/main.py", "type": "blob", "size": 1000},
        ]
        selected = select_files(tree)
        assert len(selected) == 1
        assert selected[0]["path"] == "src/main.py"

    def test_skips_lock_files(self):
        tree = [
            {"path": "package.json", "type": "blob", "size": 2000},
            {"path": "package-lock.json", "type": "blob", "size": 500000},
        ]
        selected = select_files(tree)
        paths = [f["path"] for f in selected]
        assert "package-lock.json" not in paths

    def test_empty_tree(self):
        selected = select_files([])
        assert selected == []


class TestFormatTree:
    """Test directory tree formatting."""

    def test_basic_tree(self):
        tree = [
            {"path": "src", "type": "tree"},
            {"path": "src/main.py", "type": "blob", "size": 1500},
            {"path": "README.md", "type": "blob", "size": 3000},
        ]
        result = format_tree(tree)
        assert "src/" in result
        assert "main.py" in result
        assert "README.md" in result

    def test_skips_node_modules_in_tree(self):
        tree = [
            {"path": "node_modules", "type": "tree"},
            {"path": "node_modules/lodash/index.js", "type": "blob", "size": 1000},
            {"path": "src/main.py", "type": "blob", "size": 1500},
        ]
        result = format_tree(tree)
        assert "lodash" not in result
        assert "main.py" in result

    def test_empty_tree(self):
        result = format_tree([])
        assert result == ""


class TestTruncateFileContent:
    """Test file content truncation."""

    def test_short_content_unchanged(self):
        content = "line1\nline2\nline3"
        assert truncate_file_content(content, max_lines=10) == content

    def test_long_content_truncated(self):
        content = "\n".join(f"line {i}" for i in range(100))
        result = truncate_file_content(content, max_lines=10)
        assert "line 0" in result
        assert "line 9" in result
        assert "line 10" not in result
        assert "truncated" in result

    def test_exact_limit_not_truncated(self):
        content = "\n".join(f"line {i}" for i in range(10))
        result = truncate_file_content(content, max_lines=10)
        assert "truncated" not in result


class TestBuildContext:
    """Test context string building."""

    def test_includes_metadata(self):
        metadata = {
            "name": "test-repo",
            "owner": "test-user",
            "description": "A test repository",
            "language": "Python",
            "topics": ["testing"],
            "stars": 42,
        }
        tree = [{"path": "README.md", "type": "blob", "size": 100}]
        file_contents = {"README.md": "# Test Repo"}
        selected = [{"path": "README.md", "size": 100, "tier": 1}]

        context = build_context(metadata, tree, file_contents, selected)
        assert "test-repo" in context
        assert "test-user" in context
        assert "A test repository" in context
        assert "Python" in context

    def test_includes_file_contents(self):
        metadata = {"name": "repo", "owner": "owner", "stars": 0}
        tree = [{"path": "main.py", "type": "blob", "size": 100}]
        file_contents = {"main.py": "print('hello')"}
        selected = [{"path": "main.py", "size": 100, "tier": 4}]

        context = build_context(metadata, tree, file_contents, selected)
        assert "main.py" in context
        assert "print('hello')" in context


# ═══════════════════════════════════════════════════════════════════════
#  LLM Response Parsing Tests
# ═══════════════════════════════════════════════════════════════════════


class TestExtractJson:
    """Test JSON extraction from LLM responses."""

    def test_clean_json(self):
        text = '{"summary": "A test project", "technologies": ["Python"], "structure": "Simple layout"}'
        result = _extract_json(text)
        assert result["summary"] == "A test project"
        assert result["technologies"] == ["Python"]

    def test_json_with_markdown_fences(self):
        text = '```json\n{"summary": "A project", "technologies": ["Go"], "structure": "Standard"}\n```'
        result = _extract_json(text)
        assert result["summary"] == "A project"

    def test_json_with_surrounding_text(self):
        text = 'Here is the analysis:\n{"summary": "Test", "technologies": [], "structure": "Flat"}\nEnd.'
        result = _extract_json(text)
        assert result["summary"] == "Test"

    def test_invalid_json_raises(self):
        with pytest.raises(LLMError, match="parsed as JSON"):
            _extract_json("This is not JSON at all")

    def test_json_with_whitespace(self):
        text = '  \n  {"summary": "Spaced", "technologies": ["Rust"], "structure": "Cargo"}  \n  '
        result = _extract_json(text)
        assert result["summary"] == "Spaced"


class TestValidateResponse:
    """Test LLM response validation."""

    def test_valid_response(self):
        data = {
            "summary": "A great project",
            "technologies": ["Python", "FastAPI"],
            "structure": "Standard layout",
        }
        result = _validate_response(data)
        assert result["summary"] == "A great project"
        assert len(result["technologies"]) == 2
        assert result["structure"] == "Standard layout"

    def test_missing_summary(self):
        with pytest.raises(LLMError, match="summary"):
            _validate_response({"technologies": [], "structure": "Flat"})

    def test_missing_technologies(self):
        with pytest.raises(LLMError, match="technologies"):
            _validate_response({"summary": "Test", "structure": "Flat"})

    def test_missing_structure(self):
        with pytest.raises(LLMError, match="structure"):
            _validate_response({"summary": "Test", "technologies": []})

    def test_empty_summary(self):
        with pytest.raises(LLMError, match="summary"):
            _validate_response({"summary": "", "technologies": [], "structure": "Flat"})

    def test_filters_empty_technologies(self):
        data = {
            "summary": "Project",
            "technologies": ["Python", "", None, "FastAPI"],
            "structure": "Layout",
        }
        result = _validate_response(data)
        assert result["technologies"] == ["Python", "FastAPI"]


# ═══════════════════════════════════════════════════════════════════════
#  Pydantic Model Tests
# ═══════════════════════════════════════════════════════════════════════


class TestSummarizeRequest:
    """Test request model validation."""

    def test_valid_url(self):
        req = SummarizeRequest(github_url="https://github.com/psf/requests")
        assert req.github_url == "https://github.com/psf/requests"

    def test_valid_url_with_trailing_slash(self):
        req = SummarizeRequest(github_url="https://github.com/psf/requests/")
        assert req.github_url == "https://github.com/psf/requests"

    def test_invalid_url(self):
        with pytest.raises(Exception):  # ValidationError
            SummarizeRequest(github_url="not-a-url")

    def test_non_github_url(self):
        with pytest.raises(Exception):
            SummarizeRequest(github_url="https://gitlab.com/owner/repo")


class TestErrorResponse:
    """Test error response model."""

    def test_default_status(self):
        err = ErrorResponse(message="Something went wrong")
        assert err.status == "error"
        assert err.message == "Something went wrong"

    def test_serialization(self):
        err = ErrorResponse(message="Not found")
        data = err.model_dump()
        assert data == {"status": "error", "message": "Not found"}


# ═══════════════════════════════════════════════════════════════════════
#  API Endpoint Tests (using FastAPI TestClient)
# ═══════════════════════════════════════════════════════════════════════


class TestAPIEndpoints:
    """Test API endpoints using FastAPI's TestClient (no real server needed)."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_summarize_invalid_url(self):
        response = self.client.post(
            "/summarize",
            json={"github_url": "not-a-url"},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["status"] == "error"
        assert "Validation error" in data["message"]

    def test_summarize_missing_field(self):
        response = self.client.post("/summarize", json={})
        assert response.status_code == 422
        data = response.json()
        assert data["status"] == "error"
        assert "required" in data["message"].lower()

    def test_summarize_empty_body(self):
        response = self.client.post(
            "/summarize",
            content="",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_summarize_non_github_url(self):
        response = self.client.post(
            "/summarize",
            json={"github_url": "https://gitlab.com/owner/repo"},
        )
        assert response.status_code == 422

    def test_summarize_nonexistent_repo(self):
        """This test hits the real GitHub API."""
        response = self.client.post(
            "/summarize",
            json={"github_url": "https://github.com/nonexistent-xyz-99/fake-repo"},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "error"
        assert "not found" in data["message"].lower()

    def test_cors_headers(self):
        """Verify CORS headers are present."""
        response = self.client.options(
            "/summarize",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # Starlette CORS echoes the request Origin when allow_origins=["*"]
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] in (
            "*", "http://localhost:3000"
        )

    def test_openapi_docs(self):
        """Verify OpenAPI docs are accessible."""
        response = self.client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json(self):
        """Verify OpenAPI JSON schema is accessible."""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/summarize" in schema["paths"]
        assert "/health" in schema["paths"]
