import Link from "next/link";
import { Logo } from "@/components/Logo";
import { ROUNDS } from "@/lib/modules";

export default function Landing() {
  return (
    <div className="bg-white">
      <header className="border-b border-slate-200">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Logo />
          <nav className="flex items-center gap-2 text-sm">
            <a href="#rounds" className="hidden px-3 py-2 text-ink-700 hover:text-ink-900 sm:inline">Rounds</a>
            <a href="#features" className="hidden px-3 py-2 text-ink-700 hover:text-ink-900 sm:inline">Features</a>
            <Link href="/login" className="btn-secondary">Sign in</Link>
            <Link href="/register" className="btn-primary">Create account</Link>
          </nav>
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl gap-12 px-6 py-16 lg:grid-cols-2 lg:gap-16 lg:py-24">
        <div>
          <h1 className="text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            Rehearse the whole hiring process before it counts.
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-ink-700">
            InterviewMate takes you through aptitude, technical, coding, group discussion and HR rounds in the
            order companies run them, then shows where to focus next.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/register" className="btn-primary px-5 py-2.5">Create a free account</Link>
            <Link href="/login" className="btn-secondary px-5 py-2.5">Sign in</Link>
          </div>
          <p className="mt-6 max-w-md text-sm text-ink-500">
            Every workspace module is active today, with local progress saving, adaptive practice, and optional AI prompts.
          </p>
        </div>

        <div id="rounds" className="scroll-mt-24 rounded-lg border border-slate-200">
          <div className="border-b border-slate-200 px-5 py-3.5">
            <h2 className="text-sm font-semibold">A complete recruitment process</h2>
          </div>
          <ol className="divide-y divide-slate-200">
            {ROUNDS.map((r, i) => (
              <li key={r.name} className="flex gap-4 px-5 py-3.5">
                <span className="w-5 pt-0.5 text-sm tabular-nums text-ink-500">{i + 1}</span>
                <div>
                  <p className="text-sm font-medium">{r.name}</p>
                  <p className="text-sm text-ink-500">{r.note}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="features" className="scroll-mt-16 border-t border-slate-200 bg-slate-50">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <h2 className="max-w-2xl text-2xl font-semibold tracking-tight">Preparation that responds to your results</h2>
          <div className="mt-10 grid gap-10 md:grid-cols-3">
            <div>
              <h3 className="font-medium">Start from your resume</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-700">
                Upload your resume and a job description. See which required skills you already show and which you
                still need to build.
              </p>
            </div>
            <div>
              <h3 className="font-medium">Practice in realistic conditions</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-700">
                Timed tests, follow-up questions, real code execution against test cases, and spoken interviews.
              </p>
            </div>
            <div>
              <h3 className="font-medium">See progress you can trust</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-700">
                Every chart comes from your saved attempts. Scores are estimates to guide practice, not a prediction
                of a hiring decision.
              </p>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-slate-200">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-8 text-sm text-ink-500 sm:flex-row sm:justify-between">
          <span>© 2026 InterviewMate</span>
          <span>Practice questions are AI-generated and are not real company interview questions.</span>
        </div>
      </footer>
    </div>
  );
}
