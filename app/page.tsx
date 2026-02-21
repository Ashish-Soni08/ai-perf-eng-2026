import { Github } from "lucide-react";
import { Summarizer } from "@/components/summarizer";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-4 py-12 sm:py-20">
      {/* Hero */}
      <header className="mb-10 flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 text-accent">
            <Github size={22} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl text-balance">
            Repo Summarizer
          </h1>
        </div>
        <p className="max-w-lg text-sm leading-relaxed text-muted-foreground text-pretty">
          Paste any public GitHub repository URL and get an AI-powered breakdown
          of what it does, the technologies it uses, and how the project is
          structured.
        </p>
      </header>

      {/* App */}
      <Summarizer />

      {/* Footer */}
      <footer className="mt-auto pt-16 text-center text-xs text-muted-foreground/60">
        Built with FastAPI + Next.js
      </footer>
    </main>
  );
}
