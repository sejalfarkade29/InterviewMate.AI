"use client";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { post } from "@/lib/api";
import { announceReward, type Reward } from "@/lib/rewards";
import { Chip, EvaluationCard, Notice, Panel, Spinner, fmtTime, type Evaluation } from "@/components/ui";

export type Question = {
  id: string; topic: string; difficulty: number; question: string; hints: string[]; type: "mcq" | "text"; options?: string[];
  time_limit_sec: number; source: string; kind: string; module: string;
};
type Answered = { record_id: number; result: Evaluation; reward: Reward };
const LEVELS = ["", "Beginner", "Easy", "Medium", "Hard", "Very hard"];

/**
 * One question at a time: question → answer box → submit → score and feedback → **Next question**.
 * `load` fetches a fresh question; it is called on mount, on Next, and whenever `reloadKey` changes.
 */
export function QuestionRunner({ load, reloadKey, placeholder, onAnswered, extraTop, nextLabel = "Next question" }: {
  load: () => Promise<Question>; reloadKey?: string; placeholder?: string; onAnswered?: (a: Answered) => void; extraTop?: ReactNode; nextLabel?: string;
}) {
  const [q, setQ] = useState<Question | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [choice, setChoice] = useState<number | null>(null);
  const [answer, setAnswer] = useState("");
  const [hints, setHints] = useState(0);
  const [done, setDone] = useState<Answered | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [stats, setStats] = useState({ n: 0, total: 0 });
  const started = useRef(Date.now());
  const seq = useRef(0);

  const next = useCallback(async () => {
    const mine = ++seq.current;
    setLoading(true); setError(""); setDone(null); setChoice(null); setAnswer(""); setHints(0);
    try {
      const nq = await load();
      if (mine !== seq.current) return;
      setQ(nq); started.current = Date.now(); setElapsed(0);
    } catch (e) { if (mine === seq.current) { setQ(null); setError(e instanceof Error ? e.message : "Could not load a question"); } }
    finally { if (mine === seq.current) setLoading(false); }
  }, [load]);

  useEffect(() => { void next(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [reloadKey]);
  useEffect(() => {
    if (!q || done) return;
    const t = setInterval(() => setElapsed(Math.round((Date.now() - started.current) / 1000)), 1000);
    return () => clearInterval(t);
  }, [q, done]);

  const submit = async () => {
    if (!q) return;
    setSubmitting(true); setError("");
    try {
      const body = q.type === "mcq" ? { question_id: q.id, choice, time_spent_sec: elapsed } : { question_id: q.id, answer, time_spent_sec: elapsed };
      const res = await post<Answered>("/practice/answer", body);
      setDone(res); announceReward(res.reward);
      setStats((s) => ({ n: s.n + 1, total: s.total + res.result.score }));
      onAnswered?.(res);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not submit"); }
    finally { setSubmitting(false); }
  };
  const canSubmit = q?.type === "mcq" ? choice !== null : answer.trim().length >= 3;
  const overtime = q ? elapsed > q.time_limit_sec : false;

  return (
    <div className="space-y-6">
      {extraTop}
      {stats.n > 0 && <p className="text-sm text-ink-500">This session: {stats.n} answered · average {Math.round(stats.total / stats.n)}%</p>}
      {loading && <Panel><Spinner label="Preparing a fresh question…" /></Panel>}
      {error && <Notice tone="red">{error}</Notice>}
      {!loading && !q && error && <button className="btn-secondary" onClick={() => void next()}>Try again</button>}
      {q && !loading && (
        <Panel>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone="blue">{LEVELS[q.difficulty] || "Medium"}</Chip>
              {q.topic && <Chip>{q.topic}</Chip>}
              {q.kind && q.kind !== q.module && <Chip>{q.kind}</Chip>}
              {q.source === "offline" && <Chip tone="amber">Built-in question</Chip>}
            </div>
            {!done && <span className={`text-sm tabular-nums ${overtime ? "text-amber-700" : "text-ink-500"}`} aria-label="Time spent">{fmtTime(elapsed)} / {fmtTime(q.time_limit_sec)}</span>}
          </div>
          <h2 className="mt-4 whitespace-pre-wrap text-lg font-medium leading-relaxed">{q.question}</h2>

          {q.type === "mcq" ? (
            <div className="mt-5 grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Answer options">
              {q.options?.map((o, i) => {
                const correct = done?.result.correct_index === i, wrong = done && choice === i && !done.result.correct;
                return (
                  <label key={i} className={`flex cursor-pointer items-start gap-3 rounded-md border px-3 py-2.5 text-sm ${correct ? "border-green-500 bg-green-50" : wrong ? "border-red-400 bg-red-50" : choice === i ? "border-brand-600 bg-brand-50" : "border-slate-200 hover:bg-slate-50"}`}>
                    <input type="radio" name="mcq" className="mt-0.5" checked={choice === i} disabled={!!done} onChange={() => setChoice(i)} />
                    <span>{o}</span>
                  </label>
                );
              })}
            </div>
          ) : (
            <div className="mt-5">
              <label className="label" htmlFor="answer-box">Your answer</label>
              <textarea id="answer-box" className="input font-sans" rows={9} value={answer} disabled={!!done} onChange={(e) => setAnswer(e.target.value)}
                placeholder={placeholder || "Type your answer here. Explain your reasoning and add an example."} />
              <p className="hint">{answer.trim() ? `${answer.trim().split(/\s+/).length} words` : "Write a few sentences. Short or vague answers score low."}</p>
            </div>
          )}

          {!done && q.hints?.length > 0 && (
            <div className="mt-4 text-sm">
              {hints > 0 && <ul className="mb-2 space-y-1 rounded-md bg-amber-50 p-3 text-amber-900">{q.hints.slice(0, hints).map((h, i) => <li key={i}>💡 {h}</li>)}</ul>}
              {hints < q.hints.length && <button type="button" className="text-brand-700 hover:underline" onClick={() => setHints((h) => h + 1)}>{hints ? "Show another hint" : "Need a hint?"}</button>}
            </div>
          )}

          <div className="mt-5 flex flex-wrap items-center gap-3">
            {!done ? (
              <>
                <button className="btn-primary" disabled={!canSubmit || submitting} onClick={submit}>{submitting ? "Evaluating…" : "Submit answer"}</button>
                <button className="btn-secondary" disabled={submitting} onClick={() => void next()}>Skip →</button>
                {submitting && <Spinner label="Evaluating your answer…" />}
              </>
            ) : (
              <button className="btn-primary" onClick={() => void next()} autoFocus>{nextLabel} →</button>
            )}
          </div>
        </Panel>
      )}
      {done && <Panel><EvaluationCard result={done.result} /></Panel>}
    </div>
  );
}
