import { Summarizer } from "@/components/summarizer";
import { GitBranch, Cpu } from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Hero */}
        <header className="mb-12 flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 text-accent">
              <GitBranch size={20} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground text-balance">
              GitHub Repo Summarizer
            </h1>
          </div>
          <p className="max-w-xl text-base leading-relaxed text-muted-foreground text-pretty">
            Paste any public GitHub repository URL and get an AI-powered analysis
            of what it does, its tech stack, and how the project is organized.
          </p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Cpu size={14} className="text-accent/60" />
            <span className="font-mono">Powered by Kimi-K2.5 via Nebius</span>
          </div>
        </header>

        {/* App */}
        <Summarizer />

        {/* Footer */}
        <footer className="mt-16 border-t border-border pt-6">
          <p className="text-xs text-muted-foreground">
            {"Built with Next.js, FastAPI, and "}
            <a
              href="https://github.com/vercel-labs/json-render"
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent hover:underline"
            >
              json-render
            </a>
            {" for generative UI. Open source on "}
            <a
              href="https://github.com/Ashish-Soni08/ai-perf-eng-2026"
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent hover:underline"
            >
              GitHub
            </a>
            .
          </p>
        </footer>
      </div>
    </main>
  );
}
