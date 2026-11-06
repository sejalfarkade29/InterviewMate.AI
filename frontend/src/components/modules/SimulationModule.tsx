"use client";

import { useEffect, useRef, useState } from "react";
import { post, ApiError } from "@/lib/api";
import { announceReward, type Reward } from "@/lib/rewards";
import type { ModuleInfo } from "@/lib/modules";
import { Bar, Chip, EvaluationCard, Header, List, Notice, Panel, Ring, Spinner, fmtTime, type Evaluation } from "@/components/ui";

type Question = { id: string; question: string; topic?: string; difficulty?: number; type: "mcq" | "text"; options?: string[]; hints?: string[]; time_limit_sec?: number };
type AnswerResponse = { record_id: number; result: Evaluation; reward: Reward };
type Report = {
  readiness_score: number; verdict: string; summary: string; per_round: { round: string; questions: number; avg: number }[];
  strengths: string[]; weaknesses: string[]; next_steps: string[]; source: string;
};

const ROUND_LABELS: Record<string, string> = { aptitude: "Aptitude", technical: "Technical", dsa: "DSA", hr: "HR", project: "Project" };
const ALL_ROUNDS = Object.keys(ROUND_LABELS);

type Phase = "setup" | "loading" | "question" | "result" | "report";

export function SimulationModule({ module }: { module: ModuleInfo }) {
  const [role, setRole] = useState("Software Engineer (fresher)");
  const [rounds, setRounds] = useState<string[]>(["aptitude", "technical", "hr"]);
  const [perRound, setPerRound] = useState(2);
  const [phase, setPhase] = useState<Phase>("setup");
  const [plan, setPlan] = useState<string[]>([]);       // one entry per planned question (the round name)
  const [index, setIndex] = useState(0);
  const [question, setQuestion] = useState<Question | null>(null);
  const [choice, setChoice] = useState<number | null>(null);
  const [answer, setAnswer] = useState("");
  const [hints, setHints] = useState(false);
  const [result, setResult] = useState<Evaluation | null>(null);
  const [recordIds, setRecordIds] = useState<number[]>([]);
  const [notices, setNotices] = useState<string[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const started = useRef(0);
  const planRef = useRef<string[]>([]);

  useEffect(() => {
    if (phase !== "question") return;
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - started.current) / 1000)), 1000);
    return () => clearInterval(t);
  }, [phase, question?.id]);

  const toggleRound = (r: string) => setRounds((cur) => (cur.includes(r) ? cur.filter((x) => x !== r) : ALL_ROUNDS.filter((x) => cur.includes(x) || x === r)));

  /** Fetch the question at position i. A round the backend refuses (for example project without a resume) is dropped. */
  async function loadQuestion(i: number): Promise<void> {
    setPhase("loading"); setError("");
    let list = planRef.current;
    let pos = i;
    while (pos < list.length) {
      const kind = list[pos];
      try {
        const q = await post<Question>("/practice/question", { module: "simulation", kind });
        setQuestion(q); setIndex(pos); setChoice(null); setAnswer(""); setHints(false); setResult(null); setElapsed(0);
        started.current = Date.now();
        setPlan(list); setPhase("question");
        return;
      } catch (e) {
        if (e instanceof ApiError && e.status === 422) {
          setNotices((n) => [...n, `${ROUND_LABELS[kind] ?? kind} round skipped: ${e.message}`]);
          list = list.filter((r) => r !== kind);
          planRef.current = list;
          continue;
        }
        setError(e instanceof ApiError ? e.message : "Could not load the next question");
        setPlan(list); setPhase(question ? "question" : "setup");
        return;
      }
    }
    setPlan(list);
    await finish();
  }

  async function start() {
    const list = ALL_ROUNDS.filter((r) => rounds.includes(r)).flatMap((r) => Array(perRound).fill(r) as string[]);
    planRef.current = list; setPlan(list);
    setRecordIds([]); setNotices([]); setReport(null); setQuestion(null);
    await loadQuestion(0);
  }

  async function submitAnswer() {
    if (!question || busy) return;
    setBusy(true); setError("");
    try {
      const body = question.type === "mcq"
        ? { question_id: question.id, choice, time_spent_sec: elapsed }
        : { question_id: question.id, answer, time_spent_sec: elapsed };
      const r = await post<AnswerResponse>("/practice/answer", body);
      setResult(r.result); setRecordIds((ids) => [...ids, r.record_id]);
      announceReward(r.reward);
      setPhase("result");
    } catch (e) { setError(e instanceof ApiError ? e.message : "Could not submit the answer"); }
    finally { setBusy(false); }
  }

  async function finish(ids?: number[]) {
    const all = ids ?? recordIds;
    if (!all.length) { setPhase("setup"); setError("No questions were answered, so there is no report to build."); return; }
    setPhase("loading");
    try {
      const r = await post<{ report: Report; reward: Reward }>("/simulation/report", { role, record_ids: all });
      setReport(r.report); announceReward(r.reward); setPhase("report");
    } catch (e) { setError(e instanceof ApiError ? e.message : "Could not build the report"); setPhase("result"); }
  }

  const last = index >= plan.length - 1;
  const next = () => (last ? finish() : loadQuestion(index + 1));
  const canSubmit = question?.type === "mcq" ? choice !== null : answer.trim().length >= 3;

  return (
    <div className="space-y-6">
      <Header module={module} />
      {error && <Notice tone="red">{error}</Notice>}
      {notices.map((n, i) => <Notice key={i} tone="amber">{n}</Notice>)}

      {phase === "setup" && (
        <Panel className="space-y-5">
          <div>
            <label className="label" htmlFor="sim-role">Role you are interviewing for</label>
            <input id="sim-role" className="input max-w-md" value={role} onChange={(e) => setRole(e.target.value)} />
          </div>
          <fieldset>
            <legend className="label">Rounds</legend>
            <div className="flex flex-wrap gap-2">
              {ALL_ROUNDS.map((r) => (
                <label key={r} className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm ${rounds.includes(r) ? "border-brand-600 bg-brand-50" : "border-slate-200"}`}>
                  <input type="checkbox" checked={rounds.includes(r)} onChange={() => toggleRound(r)} />{ROUND_LABELS[r]}
                </label>
              ))}
            </div>
            <p className="hint">The Project round uses your analyzed resume; it is skipped if you have not analyzed one.</p>
          </fieldset>
          <div>
            <label className="label" htmlFor="per-round">Questions per round: {perRound}</label>
            <input id="per-round" type="range" min={1} max={3} value={perRound} onChange={(e) => setPerRound(Number(e.target.value))} />
          </div>
          <div className="flex items-center gap-3">
            <button type="button" className="btn-primary" disabled={!rounds.length || role.trim().length < 2} onClick={start}>Start simulation</button>
            <span className="text-sm text-ink-500">{rounds.length * perRound} questions</span>
          </div>
        </Panel>
      )}

      {phase === "loading" && <Panel><Spinner label="Preparing…" /></Panel>}

      {(phase === "question" || phase === "result") && question && (
        <>
          <div>
            <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-sm text-ink-700">
              <span>Question {index + 1} of {plan.length} · <strong>{ROUND_LABELS[plan[index]] ?? plan[index]}</strong> round</span>
              {phase === "question" && <span className="tabular-nums text-ink-500">{fmtTime(elapsed)}{question.time_limit_sec ? ` / ${fmtTime(question.time_limit_sec)}` : ""}</span>}
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={index + (phase === "result" ? 1 : 0)} aria-valuemin={0} aria-valuemax={plan.length}>
              <div className="h-full rounded-full bg-brand-600" style={{ width: `${((index + (phase === "result" ? 1 : 0)) / plan.length) * 100}%` }} />
            </div>
          </div>
          <Panel className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">{question.topic && <Chip tone="blue">{question.topic}</Chip>}{question.difficulty && <Chip>Level {question.difficulty}</Chip>}</div>
            <h2 className="whitespace-pre-wrap text-lg font-medium leading-relaxed">{question.question}</h2>
            {question.type === "mcq" ? (
              <div className="grid gap-2 sm:grid-cols-2">
                {question.options?.map((o, i) => {
                  const done = phase === "result";
                  const correct = done && result?.correct_index === i;
                  const wrong = done && choice === i && !result?.correct;
                  return (
                    <label key={i} className={`flex cursor-pointer gap-3 rounded-md border px-3 py-2.5 text-sm ${correct ? "border-green-500 bg-green-50" : wrong ? "border-red-400 bg-red-50" : choice === i ? "border-brand-600 bg-brand-50" : "border-slate-200"}`}>
                      <input type="radio" name="sim-choice" disabled={done} checked={choice === i} onChange={() => setChoice(i)} />{o}
                    </label>
                  );
                })}
              </div>
            ) : (
              <textarea className="input" rows={9} aria-label="Your answer" disabled={phase === "result"} value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Type your answer." />
            )}
            {phase === "question" && question.hints && question.hints.length > 0 && (
              <div>
                <button type="button" className="text-sm text-brand-700 underline" onClick={() => setHints((h) => !h)}>{hints ? "Hide hints" : "Show hints"}</button>
                {hints && <div className="mt-2"><List items={question.hints} /></div>}
              </div>
            )}
            {phase === "question" && (
              <div className="flex flex-wrap items-center gap-3">
                <button type="button" className="btn-primary" disabled={!canSubmit || busy} onClick={submitAnswer}>{busy ? "Scoring…" : "Submit answer"}</button>
                <button type="button" className="btn-secondary" disabled={busy} onClick={next}>{last ? "Skip & finish" : "Skip"}</button>
                {busy && <Spinner label="Evaluating your answer…" />}
              </div>
            )}
          </Panel>
          {phase === "result" && result && (
            <Panel className="space-y-5">
              <EvaluationCard result={result} />
              <button type="button" className="btn-primary" onClick={next}>{last ? "Finish & get report" : "Next question"}</button>
            </Panel>
          )}
        </>
      )}

      {phase === "report" && report && (
        <Panel className="space-y-6">
          <div className="flex flex-wrap items-center gap-6">
            <Ring value={report.readiness_score} label="Readiness" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2"><h2 className="text-xl font-semibold">{report.verdict}</h2>{report.source === "offline" && <Chip tone="amber">Offline summary</Chip>}</div>
              <p className="mt-1 text-sm text-ink-700">{report.summary}</p>
            </div>
          </div>
          {report.per_round.length > 0 && (
            <div><p className="mb-3 text-sm font-medium">Round by round</p>
              <div className="grid gap-3 sm:grid-cols-2">{report.per_round.map((p) => <Bar key={p.round} label={`${ROUND_LABELS[p.round] ?? p.round} (${p.questions} q)`} value={p.avg} />)}</div>
            </div>
          )}
          <div className="grid gap-6 sm:grid-cols-2">
            {report.strengths.length > 0 && <div><p className="mb-2 text-sm font-medium">Strengths</p><List tone="good" items={report.strengths} /></div>}
            {report.weaknesses.length > 0 && <div><p className="mb-2 text-sm font-medium">To work on</p><List tone="bad" items={report.weaknesses} /></div>}
          </div>
          {report.next_steps.length > 0 && <div><p className="mb-2 text-sm font-medium">Next steps</p><List items={report.next_steps} /></div>}
          <button type="button" className="btn-primary" onClick={() => { setPhase("setup"); setReport(null); setQuestion(null); }}>Start again</button>
        </Panel>
      )}
    </div>
  );
}
