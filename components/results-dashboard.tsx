"use client";

import {
  Star,
  GitBranch,
  Code2,
  ExternalLink,
  FolderTree,
  Info,
  Cpu,
} from "lucide-react";
import type { SummarizeResponse } from "@/lib/api";
import { formatStars } from "@/lib/api";

interface ResultsDashboardProps {
  data: SummarizeResponse;
}

export function ResultsDashboard({ data }: ResultsDashboardProps) {
  const { repo_metadata: meta } = data;

  return (
    <div className="animate-[fadeSlideIn_0.5s_ease-out] flex flex-col gap-5">
      {/* Header Card */}
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-semibold text-foreground text-balance">
              {meta.owner}
              <span className="text-muted-foreground font-normal">{"/"}</span>
              {meta.name}
            </h2>
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <Star size={14} className="text-amber-400" />
                {formatStars(meta.stars)}
              </span>
              {meta.language && (
                <span className="flex items-center gap-1.5">
                  <Code2 size={14} />
                  {meta.language}
                </span>
              )}
              <span className="flex items-center gap-1.5">
                <GitBranch size={14} />
                {meta.default_branch}
              </span>
            </div>
          </div>
          <a
            href={meta.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex shrink-0 items-center gap-1.5 rounded-md border border-border bg-muted/50 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:border-accent/50"
          >
            View on GitHub
            <ExternalLink size={12} />
          </a>
        </div>
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {/* Summary Card */}
        <DashboardCard icon={<Info size={16} />} title="Summary">
          <p className="text-sm leading-relaxed text-muted-foreground">
            {data.summary}
          </p>
        </DashboardCard>

        {/* Technologies Card */}
        <DashboardCard icon={<Cpu size={16} />} title="Technologies">
          <div className="flex flex-wrap gap-2">
            {data.technologies.map((tech) => (
              <span
                key={tech}
                className="rounded-full border border-border bg-muted/60 px-2.5 py-0.5 text-xs font-medium text-foreground"
              >
                {tech}
              </span>
            ))}
          </div>
        </DashboardCard>

        {/* Structure Card - spans full width */}
        <DashboardCard
          icon={<FolderTree size={16} />}
          title="Project Structure"
          className="md:col-span-2"
        >
          <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-muted-foreground">
            {data.structure}
          </pre>
        </DashboardCard>
      </div>
    </div>
  );
}

/** Skeleton loading state matching the dashboard layout */
export function ResultsSkeleton() {
  return (
    <div className="flex flex-col gap-5">
      {/* Header Skeleton */}
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex flex-col gap-3">
          <div className="h-6 w-48 animate-pulse rounded bg-muted" />
          <div className="h-4 w-64 animate-pulse rounded bg-muted" />
        </div>
      </div>

      {/* Grid Skeleton */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <SkeletonCard lines={4} />
        <SkeletonCard lines={2} badges />
        <div className="md:col-span-2">
          <SkeletonCard lines={6} />
        </div>
      </div>
    </div>
  );
}

// -- Internal Components -----------------------------------------------

function DashboardCard({
  icon,
  title,
  children,
  className = "",
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-lg border border-border bg-card p-5 ${className}`}
    >
      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-foreground">
        <span className="text-accent">{icon}</span>
        {title}
      </div>
      {children}
    </div>
  );
}

function SkeletonCard({
  lines,
  badges,
}: {
  lines: number;
  badges?: boolean;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <div className="mb-3 h-5 w-32 animate-pulse rounded bg-muted" />
      {badges ? (
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="h-6 animate-pulse rounded-full bg-muted"
              style={{ width: `${60 + Math.random() * 40}px` }}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {Array.from({ length: lines }).map((_, i) => (
            <div
              key={i}
              className="h-3.5 animate-pulse rounded bg-muted"
              style={{ width: `${70 + Math.random() * 30}%` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
