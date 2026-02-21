"use client";

import { useState, useCallback } from "react";
import { Github, ArrowRight, Loader2 } from "lucide-react";
import { isValidGitHubUrl } from "@/lib/api";

const EXAMPLE_REPOS = [
  "https://github.com/vercel/next.js",
  "https://github.com/psf/requests",
  "https://github.com/expressjs/express",
];

interface UrlInputProps {
  onSubmit: (url: string) => void;
  isLoading: boolean;
}

export function UrlInput({ onSubmit, isLoading }: UrlInputProps) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = url.trim();

      if (!trimmed) {
        setError("Please enter a GitHub repository URL.");
        return;
      }

      if (!isValidGitHubUrl(trimmed)) {
        setError(
          "Invalid URL. Expected format: https://github.com/owner/repo",
        );
        return;
      }

      setError(null);
      onSubmit(trimmed);
    },
    [url, onSubmit],
  );

  const handleExampleClick = useCallback(
    (exampleUrl: string) => {
      setUrl(exampleUrl);
      setError(null);
      onSubmit(exampleUrl);
    },
    [onSubmit],
  );

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Github
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
              size={18}
            />
            <input
              type="url"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                if (error) setError(null);
              }}
              placeholder="https://github.com/owner/repo"
              disabled={isLoading}
              className="w-full rounded-lg border border-border bg-card py-3 pl-10 pr-4 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent disabled:opacity-50"
              aria-label="GitHub repository URL"
              aria-invalid={!!error}
              aria-describedby={error ? "url-error" : undefined}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center gap-2 rounded-lg bg-accent px-5 py-3 text-sm font-medium text-accent-foreground hover:bg-accent/90 focus:outline-none focus:ring-2 focus:ring-accent/50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <span>Analyze</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
        {error && (
          <p id="url-error" className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
      </form>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">Try:</span>
        {EXAMPLE_REPOS.map((repo) => {
          const shortName = repo.replace("https://github.com/", "");
          return (
            <button
              key={repo}
              onClick={() => handleExampleClick(repo)}
              disabled={isLoading}
              className="rounded-md border border-border bg-muted/50 px-2.5 py-1 font-mono text-xs text-muted-foreground hover:text-foreground hover:border-accent/50 focus:outline-none focus:ring-1 focus:ring-accent/50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {shortName}
            </button>
          );
        })}
      </div>
    </div>
  );
}
