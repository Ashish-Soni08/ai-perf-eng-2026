"use client";

import { useState, useCallback, useRef } from "react";
import { UrlInput } from "./url-input";
import { ResultsDashboard, ResultsSkeleton } from "./results-dashboard";
import { ErrorState } from "./error-state";
import { summarizeRepo, ApiError, type SummarizeResponse } from "@/lib/api";

type AppState =
  | { kind: "idle" }
  | { kind: "loading"; url: string }
  | { kind: "success"; url: string; data: SummarizeResponse }
  | { kind: "error"; url: string; message: string };

/**
 * Orchestrator component managing the state machine:
 *   idle -> loading -> success | error
 */
export function Summarizer() {
  const [state, setState] = useState<AppState>({ kind: "idle" });
  const abortRef = useRef<AbortController | null>(null);

  const handleSubmit = useCallback(async (url: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ kind: "loading", url });

    try {
      const data = await summarizeRepo(url);
      if (controller.signal.aborted) return;
      setState({ kind: "success", url, data });
    } catch (err) {
      if (controller.signal.aborted) return;
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "An unexpected error occurred. Please try again.";
      setState({ kind: "error", url, message });
    }
  }, []);

  const handleRetry = useCallback(() => {
    if (state.kind === "error") {
      handleSubmit(state.url);
    }
  }, [state, handleSubmit]);

  return (
    <div className="flex flex-col gap-8">
      <UrlInput onSubmit={handleSubmit} isLoading={state.kind === "loading"} />

      {state.kind === "loading" && (
        <div>
          <p className="mb-4 text-sm text-muted-foreground">
            {"Analyzing "}
            <span className="font-mono text-foreground">
              {state.url.replace("https://github.com/", "")}
            </span>
            {"... This typically takes 15\u201330 seconds."}
          </p>
          <ResultsSkeleton />
        </div>
      )}

      {state.kind === "success" && <ResultsDashboard data={state.data} />}

      {state.kind === "error" && (
        <ErrorState message={state.message} onRetry={handleRetry} />
      )}
    </div>
  );
}
