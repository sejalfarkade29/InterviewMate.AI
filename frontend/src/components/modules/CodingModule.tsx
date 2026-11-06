"use client";

import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { api, post, ApiError } from "@/lib/api";
import { announceReward, type Reward } from "@/lib/rewards";
import type { ModuleInfo } from "@/lib/modules";
import { Chip, Header, List, Notice, Panel, Spinner, Tabs } from "@/components/ui";

type Analysis = {
  verdict: "works" | "correct" | "error" | "incorrect"; headline: string; explanation: string;
  errors: { line: number | null; message: string; fix: string }[];
  time_complexity: string; space_complexity: string; complexity_explanation: string;
  suggestions: string[]; improved_code: string; source: string;
};
type Run = { stdout: string; stderr: string; exit_code: number | null; timed_out: boolean; duration_ms: number; phase: string; unavailable: string };
type RunResponse = { run: Run; analysis: Analysis | null };
type Problem = {
  id: string; title: string; topic: string; difficulty: number; statement: string; input_format?: string; output_format?: string;
  constraints?: string; examples?: { input: string; output: string; explanation?: string }[];
};
type TestResult = { index: number; passed: boolean; hidden: boolean; time_ms: number; input?: string; expected?: string; actual?: string; error?: string };
type SubmitResponse = { passed: number; total: number; score: number; results: TestResult[]; analysis: Analysis; reward: Reward | null; already_scored: boolean };
type Languages = { available: Record<string, boolean>; labels: Record<string, string>; starters: Record<string, string> };

const TOPICS = ["Any topic", "Arrays", "Strings", "Hashing", "Dynamic programming", "Sorting and searching", "Stacks and queues", "Linked lists", "Trees", "Graphs", "Recursion and backtracking", "Two pointers", "Binary search"];
const good = (v: string) => v === "works" || v === "correct";

function Editor({ value, onChange, onRun, errorLines }: { value: string; onChange: (v: string) => void; onRun: () => void; errorLines: number[] }) {
  const gutter = useRef<HTMLDivElement>(null);
  const area = useRef<HTMLTextAreaElement>(null);
  const lines = value.split("\n").length;

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    const ta = e.currentTarget;
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); onRun(); return; }
    if (e.key !== "Tab") return;
    e.preventDefault();
    const { selectionStart: s, selectionEnd: en } = ta;
    const setSel = (a: number, b: number) => requestAnimationFrame(() => { ta.selectionStart = a; ta.selectionEnd = b; });
    if (e.shiftKey || s !== en) {
      const start = value.lastIndexOf("\n", s - 1) + 1;
      const block = value.slice(start, en);
      const next = e.shiftKey ? block.replace(/^( {1,4}|\t)/gm, "") : block.replace(/^/gm, "    ");
      onChange(value.slice(0, start) + next + value.slice(en));
      setSel(e.shiftKey ? Math.max(start, s - (block.length - next.length > 0 ? Math.min(4, block.length - next.length) : 0)) : s + 4, en + next.length - block.length);
    } else {
      onChange(value.slice(0, s) + "    " + value.slice(en));
      setSel(s + 4, s + 4);
    }
  };

  return (
    <div className="flex h-[380px] overflow-hidden rounded-md border border-slate-700 bg-slate-950 font-mono text-sm leading-6">
      <div ref={gutter} aria-hidden className="select-none overflow-hidden bg-slate-900 py-3 pl-3 pr-2 text-right text-slate-500">
        {Array.from({ length: lines }, (_, i) => (
          <div key={i} className={errorLines.includes(i + 1) ? "rounded bg-red-900/60 px-1 text-red-200" : "px-1"}>{i + 1}</div>
        ))}
      </div>
      <div className="relative min-w-0 flex-1">
        <textarea
          ref={area} aria-label="Code editor" spellCheck={false} wrap="off" value={value}
          onChange={(e) => onChange(e.target.value)} onKeyDown={onKey}
          onScroll={(e) => { if (gutter.current) gutter.current.scrollTop = e.currentTarget.scrollTop; }}
          className="h-full w-full resize-none overflow-auto whitespace-pre bg-transparent py-3 pl-3 pr-3 text-slate-100 outline-none"
        />
      </div>
    </div>
  );
}

function AnalysisView({ a, onUse }: { a: Analysis; onUse: (code: string) => void }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Chip tone={good(a.verdict) ? "green" : "red"}>{a.verdict}</Chip>
        <span className="font-medium">{a.headline}</span>
        {a.source === "offline" && <Chip tone="amber">Offline estimate</Chip>}
      </div>
      <p className="text-sm text-ink-700">{a.explanation}</p>
      {a.errors.length > 0 && (
        <div className="space-y-2">
          {a.errors.map((e, i) => (
            <div key={i} className="rounded-md border border-red-200 bg-red-50 p-3 text-sm">
              <p className="font-medium text-red-800">{e.line ? `Line ${e.line}: ` : ""}{e.message}</p>
              {e.fix && <p className="mt-1 text-red-700">Fix: {e.fix}</p>}
            </div>
          ))}
        </div>
      )}
      <div>
        <p className="mb-2 text-sm font-medium">Complexity</p>
        <div className="flex flex-wrap gap-2"><Chip tone="blue">Time: {a.time_complexity}</Chip><Chip tone="blue">Space: {a.space_complexity}</Chip></div>
        {a.complexity_explanation && <p className="mt-2 text-sm text-ink-500">{a.complexity_explanation}</p>}
      </div>
      {a.suggestions.length > 0 && <div><p className="mb-2 text-sm font-medium">Suggestions</p><List items={a.suggestions} /></div>}
      {a.improved_code && (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium">Improved version</p>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary px-3 py-1" onClick={() => { void navigator.clipboard?.writeText(a.improved_code); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>{copied ? "Copied" : "Copy"}</button>
              <button type="button" className="btn-secondary px-3 py-1" onClick={() => onUse(a.improved_code)}>Use this code</button>
            </div>
          </div>
          <pre className="max-h-72 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">{a.improved_code}</pre>
        </div>
      )}
    </div>
  );
}

function RunView({ run }: { run: Run }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Chip tone={run.exit_code === 0 ? "green" : "red"}>Exit code: {run.exit_code === null ? "none" : run.exit_code}</Chip>
        <Chip>{run.duration_ms} ms</Chip>
        {run.timed_out && <Chip tone="red">Time limit exceeded</Chip>}
        {run.phase === "compile" && <Chip tone="red">Compile error</Chip>}
      </div>
      <div>
        <p className="mb-1 text-sm font-medium">Output</p>
        <pre className="max-h-60 min-h-[2.5rem] overflow-auto whitespace-pre-wrap rounded-md bg-slate-950 p-3 text-xs text-slate-100">{run.stdout || <span className="text-slate-500">(no output)</span>}</pre>
      </div>
      {run.stderr && (
        <div>
          <p className="mb-1 text-sm font-medium text-red-700">Errors</p>
          <pre className="max-h-60 overflow-auto whitespace-pre-wrap rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-800">{run.stderr}</pre>
        </div>
      )}
    </div>
  );
}

export function CodingModule({ module }: { module: ModuleInfo }) {
  const [langs, setLangs] = useState<Languages | null>(null);
  const [language, setLanguage] = useState("python");
  const [codes, setCodes] = useState<Record<string, string>>({});
  const [stdin, setStdin] = useState("");
  const [mode, setMode] = useState<"playground" | "challenge">("playground");
  const [problem, setProblem] = useState<Problem | null>(null);
  const [topic, setTopic] = useState(TOPICS[0]);
  const [busy, setBusy] = useState<"" | "run" | "submit" | "problem">("");
  const [error, setError] = useState("");
  const [runRes, setRunRes] = useState<RunResponse | null>(null);
  const [submitRes, setSubmitRes] = useState<SubmitResponse | null>(null);

  useEffect(() => {
    api<Languages>("/code/languages").then((l) => {
      setLangs(l);
      setCodes(l.starters);
      if (l.available.python === false) { const first = Object.keys(l.available).find((k) => l.available[k]); if (first) setLanguage(first); }
    }).catch((e) => setError(e instanceof ApiError ? e.message : "Could not load languages"));
  }, []);

  const code = codes[language] ?? "";
  const setCode = (v: string) => setCodes((c) => ({ ...c, [language]: v }));
  const analysis = submitRes?.analysis ?? runRes?.analysis ?? null;
  const errorLines = (analysis?.errors ?? []).map((e) => e.line).filter((n): n is number => typeof n === "number");

  const run = useCallback(async () => {
    if (busy || !code.trim()) return;
    setBusy("run"); setError(""); setSubmitRes(null);
    try {
      setRunRes(await post<RunResponse>("/code/run", { language, code, stdin, problem_id: mode === "challenge" && problem ? problem.id : undefined }));
    } catch (e) { setError(e instanceof ApiError ? e.message : "Run failed"); }
    finally { setBusy(""); }
  }, [busy, code, language, stdin, mode, problem]);

  const submit = async () => {
    if (busy || !problem) return;
    setBusy("submit"); setError(""); setRunRes(null);
    try {
      const r = await post<SubmitResponse>("/code/submit", { problem_id: problem.id, language, code });
      setSubmitRes(r);
      announceReward(r.reward);
    } catch (e) { setError(e instanceof ApiError ? e.message : "Submit failed"); }
    finally { setBusy(""); }
  };

  const nextProblem = async () => {
    setBusy("problem"); setError(""); setRunRes(null); setSubmitRes(null);
    try {
      const p = await post<Problem>("/code/problem", { topic: topic === TOPICS[0] ? "" : topic });
      setProblem(p);
      if (langs) setCodes(langs.starters);
      setStdin(p.examples?.[0]?.input ?? "");
    } catch (e) { setError(e instanceof ApiError ? e.message : "Could not load a problem"); }
    finally { setBusy(""); }
  };

  const switchMode = (m: "playground" | "challenge") => {
    setMode(m); setRunRes(null); setSubmitRes(null); setError("");
    if (m === "challenge" && !problem) void nextProblem();
  };

  const unavailable = runRes?.run.unavailable;

  return (
    <div className="space-y-6">
      <Header module={module} right={<Tabs value={mode} onChange={switchMode} items={[{ id: "playground", label: "Playground" }, { id: "challenge", label: "Challenge" }]} />} />
      {error && <Notice tone="red">{error}</Notice>}

      {mode === "challenge" && (
        <Panel>
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <label className="text-sm font-medium" htmlFor="topic">Topic</label>
            <select id="topic" className="input max-w-xs" value={topic} onChange={(e) => setTopic(e.target.value)}>{TOPICS.map((t) => <option key={t}>{t}</option>)}</select>
            <button type="button" className="btn-secondary" disabled={busy !== ""} onClick={nextProblem}>{problem ? "Next problem" : "Get a problem"}</button>
            {busy === "problem" && <Spinner label="Preparing a problem…" />}
          </div>
          {problem ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-semibold">{problem.title}</h2><Chip tone="blue">{problem.topic}</Chip><Chip>Level {problem.difficulty}</Chip></div>
              <p className="whitespace-pre-wrap text-sm text-ink-700">{problem.statement}</p>
              <div className="grid gap-3 text-sm sm:grid-cols-2">
                {problem.input_format && <div><p className="font-medium">Input</p><p className="text-ink-700">{problem.input_format}</p></div>}
                {problem.output_format && <div><p className="font-medium">Output</p><p className="text-ink-700">{problem.output_format}</p></div>}
              </div>
              {problem.constraints && <p className="text-sm text-ink-500">Constraints: {problem.constraints}</p>}
              {problem.examples?.map((ex, i) => (
                <div key={i} className="grid gap-2 sm:grid-cols-2">
                  <div><p className="mb-1 text-xs font-medium text-ink-500">Example {i + 1} input</p><pre className="rounded-md bg-slate-100 p-2 text-xs">{ex.input}</pre></div>
                  <div><p className="mb-1 text-xs font-medium text-ink-500">Output</p><pre className="rounded-md bg-slate-100 p-2 text-xs">{ex.output}</pre></div>
                  {ex.explanation && <p className="text-xs text-ink-500 sm:col-span-2">{ex.explanation}</p>}
                </div>
              ))}
            </div>
          ) : busy !== "problem" && <p className="text-sm text-ink-500">Choose a topic and get a problem to solve.</p>}
        </Panel>
      )}

      {(mode === "playground" || problem) && (
        <Panel>
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <label className="text-sm font-medium" htmlFor="lang">Language</label>
            <select id="lang" className="input max-w-[220px]" value={language} onChange={(e) => setLanguage(e.target.value)}>
              {Object.entries(langs?.labels ?? { python: "Python" }).map(([k, label]) => {
                const off = langs ? langs.available[k] === false : false;
                return <option key={k} value={k} disabled={off}>{label}{off ? " (not installed)" : ""}</option>;
              })}
            </select>
            <button type="button" className="btn-secondary" onClick={() => langs && setCode(langs.starters[language] ?? "")}>Reset to starter</button>
            <span className="hint ml-auto hidden sm:block">Ctrl/Cmd + Enter to run</span>
          </div>
          <Editor value={code} onChange={setCode} onRun={run} errorLines={errorLines} />
          <label className="label mt-4" htmlFor="stdin">Input (stdin, optional)</label>
          <textarea id="stdin" rows={3} className="input font-mono" value={stdin} onChange={(e) => setStdin(e.target.value)} placeholder="Text your program reads from standard input" />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" className="btn-primary" disabled={busy !== "" || !code.trim()} onClick={run}>{busy === "run" ? "Running…" : "Run"}</button>
            {mode === "challenge" && <button type="button" className="btn-secondary" disabled={busy !== "" || !code.trim()} onClick={submit}>{busy === "submit" ? "Judging…" : "Submit"}</button>}
            {busy === "run" && <Spinner label="Running your code…" />}
            {busy === "submit" && <Spinner label="Running all tests…" />}
          </div>
        </Panel>
      )}

      {unavailable && <Notice tone="amber">{unavailable}</Notice>}

      {runRes && !unavailable && (
        <Panel className="space-y-5">
          <h2 className="font-medium">Result</h2>
          <RunView run={runRes.run} />
          {runRes.analysis && <AnalysisView a={runRes.analysis} onUse={setCode} />}
        </Panel>
      )}

      {submitRes && (
        <Panel className="space-y-5">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="font-medium">Submission</h2>
            <Chip tone={submitRes.passed === submitRes.total ? "green" : "red"}>{submitRes.passed}/{submitRes.total} tests passed</Chip>
            <Chip tone="blue">Score {submitRes.score}</Chip>
          </div>
          {submitRes.already_scored && <Notice>You already submitted this problem, so this attempt earns no extra XP. Use Next problem for more.</Notice>}
          <div className="space-y-2">
            {submitRes.results.map((r) => (
              <div key={r.index} className={`rounded-md border p-3 text-sm ${r.passed ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">Test {r.index}</span>
                  <Chip tone={r.passed ? "green" : "red"}>{r.passed ? "Passed" : "Failed"}</Chip>
                  {r.hidden && <Chip>Hidden</Chip>}
                  <span className="text-xs text-ink-500">{r.time_ms} ms</span>
                </div>
                {!r.passed && r.input !== undefined && (
                  <div className="mt-2 grid gap-2 sm:grid-cols-3">
                    <div><p className="text-xs font-medium">Input</p><pre className="overflow-auto rounded bg-white p-2 text-xs">{r.input}</pre></div>
                    <div><p className="text-xs font-medium">Expected</p><pre className="overflow-auto rounded bg-white p-2 text-xs">{r.expected}</pre></div>
                    <div><p className="text-xs font-medium">Your output</p><pre className="overflow-auto rounded bg-white p-2 text-xs">{r.actual || "(empty)"}</pre></div>
                  </div>
                )}
                {!r.passed && r.error && <pre className="mt-2 overflow-auto whitespace-pre-wrap text-xs text-red-800">{r.error}</pre>}
              </div>
            ))}
          </div>
          <AnalysisView a={submitRes.analysis} onUse={setCode} />
          <button type="button" className="btn-primary" disabled={busy !== ""} onClick={nextProblem}>Next problem</button>
        </Panel>
      )}
    </div>
  );
}
