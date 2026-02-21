/**
 * TypeScript types mirroring the Python Pydantic models in app/models.py,
 * plus the fetch wrapper.
 */

// -- Types (mirrors app/models.py) ------------------------------------

export interface RepoMetadata {
  name: string;
  owner: string;
  url: string;
  stars: number;
  language: string | null;
  default_branch: string;
}

export interface SummarizeResponse {
  summary: string;
  technologies: string[];
  structure: string;
  repo_metadata: RepoMetadata;
}

export interface ErrorResponse {
  status: "error";
  message: string;
}

// -- API Client -------------------------------------------------------

const API_BASE = "/api";

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function summarizeRepo(
  githubUrl: string,
): Promise<SummarizeResponse> {
  const res = await fetch(`${API_BASE}/summarize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl }),
  });

  if (!res.ok) {
    const error: ErrorResponse = await res.json().catch(() => ({
      status: "error" as const,
      message: `Request failed with status ${res.status}`,
    }));
    throw new ApiError(error.message, res.status);
  }

  return res.json();
}

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// -- GitHub URL Validation (client-side, mirrors Python model) --------

const GITHUB_URL_PATTERN =
  /^https?:\/\/github\.com\/[\w.\-]+\/[\w.\-]+\/?$/;

export function isValidGitHubUrl(url: string): boolean {
  return GITHUB_URL_PATTERN.test(url.trim());
}

// -- Utility ----------------------------------------------------------

export function formatStars(count: number): string {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}k`;
  }
  return count.toString();
}
