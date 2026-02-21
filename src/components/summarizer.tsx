"use client";

import { useState, useCallback, useRef } from "react";
import { UrlInput } from "./url-input";
import { ResultsDashboard } from "./results-dashboard";
import { ErrorState } from "./error-state";
import {
  summarizeRepo,
  buildResultsSpec,
  buildLoadingSpec,
  ApiError,
  type SummarizeResponse,
} from "@/lib/api";
import type { Spec } from "@json-render/core";

type AppState =
  | { kind: "idle" }
  | { kind: "loading"; url: string }
  | { kind: "success"; url: string; data: SummarizeResponse; spec: Spec }
  | { kind: "error"; url: string; message: string };

/**
 * Orchestrator component managing the state machine:
 *   idle -> loading -> success | error
 *
 * Each state renders a different view through the same layout,
 * with the loading state using a json-render skeleton spec.
 */
export function Summarizer() {
  const [state, setState] = useState<AppState>({ kind: "idle" });
  const abortRef = useRef<AbortController | null>(null);

  const handleSubmit = useCallback(async (url: string) => {
    // Cancel any in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ kind: "loading", url });

    try {
      const data = await summarizeRepo(url);

      // Check if this request was aborted
      if (controller.signal.aborted) return;

      const spec = buildResultsSpec(data);
      setState({ kind: "success", url, data, spec });
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

  const loadingSpec = buildLoadingSpec();

  return (
    <div className="flex flex-col gap-8">
      <UrlInput
        onSubmit={handleSubmit}
        isLoading={state.kind === "loading"}
      />

      {state.kind === "loading" && (
        <div>
          <p className="mb-4 text-sm text-muted-foreground">
            {"Analyzing "}
            <span className="font-mono text-foreground">{state.url.replace("https://github.com/", "")}</span>
            {"... This typically takes 15-30 seconds."}
          </p>
          <ResultsDashboard spec={loadingSpec} loading />
        </div>
      )}

      {state.kind === "success" && (
        <ResultsDashboard spec={state.spec} />
      )}

      {state.kind === "error" && (
        <ErrorState message={state.message} onRetry={handleRetry} />
      )}
    </div>
  );
}
