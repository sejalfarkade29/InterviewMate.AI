"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, del, post, upload } from "@/lib/api";
import { announceReward, type Reward } from "@/lib/rewards";
import type { ModuleInfo } from "@/lib/modules";
import { Bar, Chip, Header, List, Notice, Panel, Ring, Spinner, Tabs } from "@/components/ui";

type Analysis = {
  candidate: { name: string; email: string; phone: string; location: string; links: string[] };
  summary: string;
  skills: { technical: string[]; tools: string[]; soft: string[] };
  education: { degree?: string; institution?: string; year?: string; score?: string }[];
  experience: { role?: string; company?: string; duration?: string; highlights?: string[] }[];
  projects: { name?: string; description?: string; technologies?: string[] }[];
  certifications: string[]; achievements: string[];
  overall_score: number; verdict: string; section_scores: Record<string, number>;
  strengths: string[]; weaknesses: string[]; suggestions: { section: string; issue: string; fix: string }[];
  ai_generated: { percent: number; confidence: string; note: string; sections: { section: string; likelihood: number; evidence: string; excerpt: string; verified_excerpt?: boolean }[] };
  source: string;
};
type Detail = { id: number; filename: string; score: number; ai_percent: number; analysis: Analysis; text: string; created_at: string; reward?: Reward };
type Row = { id: number; filename: string; score: number; ai_percent: number; created_at: string };

const verdictTone = (v: string) => (v === "Excellent" || v === "Good" ? "green" : v === "Average" ? "amber" : "red") as "green" | "amber" | "red";
const aiLabel = (p: number) => (p >= 60 ? "Mostly reads as AI-written" : p >= 30 ? "Partly reads as AI-written" : "Mostly reads as human-written");

export function ResumeModule({ module }: { module: ModuleInfo }) {
  const [mode, setMode] = useState<"file" | "text">("file");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Detail | null>(null);
  const [history, setHistory] = useState<Row[]>([]);
  const input = useRef<HTMLInputElement>(null);

  const refresh = useCallback(() => api<Row[]>("/resume").then(setHistory).catch(() => undefined), []);
  useEffect(() => { void refresh(); }, [refresh]);

  const pick = (f: File | undefined) => {
    setError("");
    if (!f) return;
    if (!/\.(pdf|docx|txt|md)$/i.test(f.name)) return setError("Unsupported file type. Upload a PDF, DOCX or TXT resume.");
    if (f.size > 5 * 1024 * 1024) return setError("File is too large. The limit is 5 MB.");
    setFile(f);
  };
  const run = async () => {
    setBusy(true); setError("");
    try {
      let r: Detail;
      if (mode === "file" && file) { const fd = new FormData(); fd.append("file", file); r = await upload<Detail>("/resume/analyze", fd); }
      else r = await post<Detail>("/resume/analyze-text", { text, name: "Pasted resume" });
      setResult(r); announceReward(r.reward); void refresh();
      setTimeout(() => document.getElementById("resume-result")?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch (e) { setError(e instanceof Error ? e.message : "Analysis failed"); }
    finally { setBusy(false); }
  };
  const open = async (id: number) => { setBusy(true); try { setResult(await api<Detail>(`/resume/${id}`)); } catch (e) { setError(e instanceof Error ? e.message : "Could not open"); } finally { setBusy(false); } };
  const remove = async (id: number) => { await del(`/resume/${id}`).catch(() => undefined); if (result?.id === id) setResult(null); void refresh(); };
  const ready = mode === "file" ? !!file : text.trim().length >= 80;

  return (
    <div className="space-y-8">
      <Header module={module} />
      <Panel>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-medium">Upload your resume</h2>
          <Tabs value={mode} onChange={setMode} items={[{ id: "file", label: "Upload file" }, { id: "text", label: "Paste text" }]} />
        </div>
        {mode === "file" ? (
          <div className="mt-4">
            <div role="button" tabIndex={0} onClick={() => input.current?.click()} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
              onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
              className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${drag ? "border-brand-600 bg-brand-50" : "border-slate-300 hover:bg-slate-50"}`}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.6" aria-hidden><path d="M12 16V4m0 0l-4 4m4-4l4 4M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3" strokeLinecap="round" strokeLinejoin="round" /></svg>
              {file ? <p className="mt-3 text-sm font-medium">{file.name} <span className="font-normal text-ink-500">({Math.max(1, Math.round(file.size / 1024))} KB)</span></p>
                : <p className="mt-3 text-sm"><span className="font-medium text-brand-700">Click to choose a file</span> or drag and drop it here</p>}
              <p className="mt-1 text-xs text-ink-500">PDF, DOCX or TXT · up to 5 MB · text-based files work best (not scanned images)</p>
            </div>
            <input ref={input} type="file" accept=".pdf,.docx,.txt,.md" className="sr-only" aria-label="Resume file" onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ""; }} />
          </div>
        ) : (
          <div className="mt-4">
            <label className="label" htmlFor="resume-text">Resume text</label>
            <textarea id="resume-text" rows={10} className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste the full text of your resume (at least a few lines)." />
          </div>
        )}
        {error && <div className="mt-4"><Notice tone="red">{error}</Notice></div>}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button type="button" className="btn-primary" disabled={!ready || busy} onClick={run}>{busy ? "Analyzing…" : "Analyze resume"}</button>
          {file && mode === "file" && !busy && <button type="button" className="btn-secondary" onClick={() => setFile(null)}>Remove file</button>}
          {busy && <Spinner label="Reading and analyzing your resume. This can take up to a minute." />}
        </div>
      </Panel>

      {result && <ResumeResult r={result} />}

      {history.length > 0 && (
        <Panel>
          <h2 className="font-medium">Your analyzed resumes</h2>
          <p className="mt-0.5 text-sm text-ink-500">Job match, project interviews and voice interviews use your most recent one.</p>
          <ul className="mt-3 divide-y divide-slate-200">
            {history.map((h) => (
              <li key={h.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div><p className="text-sm font-medium">{h.filename}</p><p className="text-xs text-ink-500">{new Date(h.created_at).toLocaleString()}</p></div>
                <div className="flex items-center gap-3"><Chip tone={h.score >= 70 ? "green" : h.score >= 50 ? "amber" : "red"}>Score {h.score}%</Chip><Chip>AI-written {h.ai_percent}%</Chip>
                  <button className="btn-secondary px-3 py-1.5" onClick={() => open(h.id)}>Open</button>
                  <button className="text-sm text-red-700 hover:underline" onClick={() => remove(h.id)}>Delete</button></div>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}

function Section({ title, children, empty }: { title: string; children?: React.ReactNode; empty?: boolean }) {
  return <div><h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-ink-500">{title}</h3>{empty ? <p className="text-sm text-ink-500">Not found in this resume.</p> : children}</div>;
}
const Tags = ({ items, tone = "slate" }: { items: string[]; tone?: "slate" | "blue" }) => <div className="flex flex-wrap gap-1.5">{items.map((s) => <Chip key={s} tone={tone}>{s}</Chip>)}</div>;

function ResumeResult({ r }: { r: Detail }) {
  const a = r.analysis;
  const ai = a.ai_generated;
  const skillCount = a.skills.technical.length + a.skills.tools.length;
  return (
    <div id="resume-result" className="space-y-6">
      <Panel>
        <div className="flex flex-wrap items-center gap-8">
          <Ring value={a.overall_score} label="Resume quality" size={128} />
          <div className="min-w-0 flex-1">
            <p className="text-sm text-ink-500">{r.filename}</p>
            <div className="mt-1 flex flex-wrap items-center gap-2"><h2 className="text-xl font-semibold">{a.overall_score}% good</h2><Chip tone={verdictTone(a.verdict)}>{a.verdict}</Chip>{a.source === "offline" && <Chip tone="amber">Offline analysis</Chip>}</div>
            <p className="mt-2 text-sm text-ink-700">{a.summary}</p>
            {a.source === "offline" && <p className="mt-2 text-xs text-ink-500">AI review was unavailable, so this uses built-in rules only. Check that GEMINI_API_KEY is set in backend/.env for a deeper review.</p>}
          </div>
          <Ring value={ai.percent} label="AI-written" size={128} invert />
        </div>
      </Panel>

      <Panel>
        <h2 className="font-medium">What your resume contains</h2>
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <Section title="Candidate">
            <dl className="space-y-1 text-sm">
              {([["Name", a.candidate.name], ["Email", a.candidate.email], ["Phone", a.candidate.phone], ["Location", a.candidate.location]] as const).map(([k, v]) => v ? <div key={k} className="flex gap-2"><dt className="w-16 text-ink-500">{k}</dt><dd>{v}</dd></div> : null)}
              {a.candidate.links?.length > 0 && <div className="flex gap-2"><dt className="w-16 text-ink-500">Links</dt><dd className="break-all">{a.candidate.links.join(", ")}</dd></div>}
            </dl>
          </Section>
          <Section title={`Skills (${skillCount})`} empty={!skillCount && !a.skills.soft.length}>
            <div className="space-y-2">{a.skills.technical.length > 0 && <Tags items={a.skills.technical} tone="blue" />}{a.skills.tools.length > 0 && <Tags items={a.skills.tools} />}{a.skills.soft.length > 0 && <Tags items={a.skills.soft} />}</div>
          </Section>
          <Section title="Education" empty={!a.education.length}>
            <ul className="space-y-2 text-sm">{a.education.map((e, i) => <li key={i}><p className="font-medium">{e.degree || "—"}</p><p className="text-ink-500">{[e.institution, e.year, e.score].filter(Boolean).join(" · ")}</p></li>)}</ul>
          </Section>
          <Section title="Experience" empty={!a.experience.length}>
            <ul className="space-y-3 text-sm">{a.experience.map((e, i) => <li key={i}><p className="font-medium">{[e.role, e.company].filter(Boolean).join(" at ") || "—"}</p>{e.duration && <p className="text-ink-500">{e.duration}</p>}{e.highlights && e.highlights.length > 0 && <div className="mt-1"><List items={e.highlights} /></div>}</li>)}</ul>
          </Section>
          <Section title="Projects" empty={!a.projects.length}>
            <ul className="space-y-3 text-sm">{a.projects.map((p, i) => <li key={i}><p className="font-medium">{p.name}</p><p className="text-ink-700">{p.description}</p>{p.technologies && p.technologies.length > 0 && <div className="mt-1"><Tags items={p.technologies} /></div>}</li>)}</ul>
          </Section>
          <div className="space-y-6">
            <Section title="Certifications" empty={!a.certifications.length}><List items={a.certifications} /></Section>
            <Section title="Achievements" empty={!a.achievements.length}><List items={a.achievements} /></Section>
          </div>
        </div>
      </Panel>

      <Panel>
        <h2 className="font-medium">How good is it, section by section</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">{Object.entries(a.section_scores).map(([k, v]) => <Bar key={k} label={k} value={v} />)}</div>
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <div><p className="mb-2 text-sm font-medium">Strengths</p>{a.strengths.length ? <List tone="good" items={a.strengths} /> : <p className="text-sm text-ink-500">None stood out yet.</p>}</div>
          <div><p className="mb-2 text-sm font-medium">Weaknesses</p>{a.weaknesses.length ? <List tone="bad" items={a.weaknesses} /> : <p className="text-sm text-ink-500">No major weaknesses found.</p>}</div>
        </div>
        {a.suggestions.length > 0 && (
          <div className="mt-6"><p className="mb-2 text-sm font-medium">What to fix</p>
            <ul className="space-y-3">{a.suggestions.map((s, i) => <li key={i} className="rounded-md border border-slate-200 p-3 text-sm"><p><Chip tone="blue">{s.section}</Chip> <span className="ml-1 text-ink-700">{s.issue}</span></p><p className="mt-1.5 text-ink-900">→ {s.fix}</p></li>)}</ul></div>
        )}
      </Panel>

      <Panel>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><h2 className="font-medium">AI-written areas</h2><p className="mt-0.5 text-sm text-ink-500">{ai.percent}% — {aiLabel(ai.percent)} · confidence: {ai.confidence}</p></div>
        </div>
        <div className="mt-3"><Bar label="Estimated AI-written share" value={ai.percent} /></div>
        {ai.sections.length ? (
          <ul className="mt-4 space-y-3">
            {ai.sections.map((s, i) => (
              <li key={i} className="rounded-md border border-amber-200 bg-amber-50/50 p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2"><Chip tone="amber">{s.section || "Section"}</Chip><span className="text-xs text-ink-500">{s.likelihood}% likely AI-written</span></div>
                {s.excerpt && <blockquote className="mt-2 border-l-2 border-amber-400 pl-3 italic text-ink-900">“{s.excerpt}”</blockquote>}
                <p className="mt-2 text-ink-700"><span className="font-medium">Why:</span> {s.evidence}</p>
              </li>
            ))}
          </ul>
        ) : <p className="mt-4 text-sm text-ink-700">No specific passages were flagged. Your wording reads specific and personal.</p>}
        <p className="mt-4 text-xs text-ink-500">{ai.note || "AI-writing detection is an estimate, not proof."} Rewrite flagged lines with your own tools, numbers and context to make them sound like you.</p>
      </Panel>

      <div className="flex flex-wrap gap-3">
        <Link href="/job-match" className="btn-primary">Match this resume to a job</Link>
        <Link href="/project" className="btn-secondary">Practice a project interview</Link>
      </div>
    </div>
  );
}
