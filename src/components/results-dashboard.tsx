"use client";

import { Renderer } from "@json-render/react";
import { registry } from "@/lib/registry";
import type { Spec } from "@json-render/core";

interface ResultsDashboardProps {
  spec: Spec;
  loading?: boolean;
}

/**
 * Renders a json-render Spec using the shadcn component registry.
 * This is the heart of the generative UI -- any valid Spec becomes
 * a fully styled dashboard without additional component code.
 */
export function ResultsDashboard({ spec, loading }: ResultsDashboardProps) {
  return (
    <div className="animate-[fadeSlideIn_0.5s_ease-out]">
      <Renderer spec={spec} registry={registry} loading={loading} />
    </div>
  );
}
