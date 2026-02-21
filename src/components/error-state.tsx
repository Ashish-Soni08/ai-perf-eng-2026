"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="animate-[fadeSlideIn_0.3s_ease-out] rounded-lg border border-destructive/30 bg-destructive/5 p-6">
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive/10">
          <AlertTriangle size={20} className="text-destructive" />
        </div>
        <div className="flex flex-1 flex-col gap-3">
          <div>
            <h3 className="text-sm font-medium text-foreground">
              Analysis Failed
            </h3>
            <p className="mt-1 text-sm text-muted-foreground leading-relaxed">
              {message}
            </p>
          </div>
          <div>
            <button
              onClick={onRetry}
              className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted focus:outline-none focus:ring-2 focus:ring-accent/50"
            >
              <RotateCcw size={12} />
              Try Again
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
