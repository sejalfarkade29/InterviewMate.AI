"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, post } from "@/lib/api";
import { announceReward, type Reward } from "@/lib/rewards";
import { listen, speak, stopSpeaking, supportsRecognition, type Listener } from "@/lib/speech";
import type { ModuleInfo } from "@/lib/modules";
import { Bar, Chip, Header, List, Notice, Panel, Ring, Spinner, Tabs, fmtTime } from "@/components/ui";

type Persona = { name: string; style: string; voice: "male" | "female" };
type Msg = { speaker: string; text: string };
type Feedback = {
  overall_score: number; verdict: string; summary: string; scores: Record<string, number>; strengths: string[]; improvements: string[];
  best_moment?: string; missed_opportunity?: string; model_contribution?: string;
  stats: { turns: number; words: number; talk_share_percent: number; duration_sec: number }; source: string;
};

const USER = "You";
const SILENCE_MS = 25000;
const VOICE_FX: Record<string, { gender: "male" | "female"; voiceIndex: number; pitch: number; rate: number }> = {
  Arjun: { gender: "male", voiceIndex: 0, pitch: 0.95, rate: 1.05 },
  Meera: { gender: "female", voiceIndex: 0, pitch: 1.1, rate: 1 },
  Kabir: { gender: "male", voiceIndex: 1, pitch: 0.8, rate: 0.95 },
  Moderator: { gender: "female", voiceIndex: 1, pitch: 0.95, rate: 0.95 },
};
const FALLBACK_PERSONAS: Persona[] = [
  { name: "Arjun", style: "assertive", voice: "male" }, { name: "Meera", style: "analytical", voice: "female" }, { name: "Kabir", style: "devil's advocate", voice: "male" },
];

export function GroupDiscussionModule({ module }: { module: ModuleInfo }) {
  const [stage, setStage] = useState<"pick" | "room" | "feedback">("pick");
  const [topics, setTopics] = useState<string[]>([]);
  const [personas, setPersonas] = useState<Persona[]>(FALLBACK_PERSONAS);
  const [topic, setTopic] = useState("");
  const [custom, setCustom] = useState("");
  const [voice, setVoice] = useState(false);
  const [loadingTopics, setLoadingTopics] = useState(false);
  const [error, setError] = useState("");

  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [typed, setTyped] = useState("");
  const [thinking, setThinking] = useState(false);
  const [speaker, setSpeaker] = useState<string | null>(null);
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [finishing, setFinishing] = useState(false);
  const [result, setResult] = useState<{ feedback: Feedback; reward?: Reward | null } | null>(null);

  const transcript = useRef<Msg[]>([]);
  const busy = useRef(false);
  const alive = useRef(false);
  const voiceRef = useRef(false);
  const topicRef = useRef("");
  const startedAt = useRef(0);
  const listener = useRef<Listener | null>(null);
  const chatEnd = useRef<HTMLDivElement>(null);
  const voiceOk = supportsRecognition();

  useEffect(() => { chatEnd.current?.scrollIntoView({ block: "end" }); }, [msgs, interim, thinking]);

  const loadTopics = useCallback(async () => {
    setLoadingTopics(true); setError("");
    try {
      const r = await api<{ topics: string[]; participants: Persona[] }>("/gd/topics");
      setTopics(r.topics);
      if (r.participants?.length) setPersonas(r.participants);
    } catch (e) { setError(e instanceof ApiError ? e.message : "Could not load topics."); }
    finally { setLoadingTopics(false); }
  }, []);
  useEffect(() => { void loadTopics(); }, [loadTopics]);

  const stopAll = useCallback(() => { alive.current = false; listener.current?.stop(); listener.current = null; stopSpeaking(); }, []);
  useEffect(() => stopAll, [stopAll]);

  useEffect(() => {
    if (stage !== "room") return;
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt.current) / 1000)), 1000);
    return () => clearInterval(t);
  }, [stage]);

  const push = (m: Msg) => { transcript.current = [...transcript.current, m]; setMsgs(transcript.current); };

  // Listen for the user's turn. Empty results re-listen until ~25 s of silence, then the others continue.
  const startListening = useCallback(async () => {
    if (!alive.current || !voiceRef.current || busy.current || listener.current) return;
    const began = Date.now();
    setListening(true); setInterim("");
    const l = listen(setInterim);
    listener.current = l;
    const nudge = setTimeout(() => l.stop(), SILENCE_MS);
    const text = await l.done;
    clearTimeout(nudge);
    listener.current = null;
    setListening(false); setInterim("");
    if (!alive.current || busy.current) return;
    if (text.trim()) { void submit(text.trim()); return; }
    if (Date.now() - began >= SILENCE_MS - 1500) void turn(false);
    else void startListening();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const turn = useCallback(async (userSpoke: boolean) => {
    if (busy.current || !alive.current) return;
    busy.current = true;
    listener.current?.stop();
    setThinking(true); setError("");
    try {
      const res = await post<{ messages: Msg[] }>("/gd/turn", {
        topic: topicRef.current, transcript: transcript.current, user_name: USER, voice: voiceRef.current,
        user_spoke: userSpoke, elapsed_sec: Math.floor((Date.now() - startedAt.current) / 1000),
      });
      setThinking(false);
      for (const m of res.messages) {
        if (!alive.current) break;
        push(m);
        setSpeaker(m.speaker);
        if (voiceRef.current) { const fx = VOICE_FX[m.speaker] ?? VOICE_FX.Moderator; await speak(m.text, fx); }
        else await new Promise((r) => setTimeout(r, 700));
        setSpeaker(null);
      }
    } catch (e) {
      setThinking(false);
      if (alive.current) setError(e instanceof ApiError ? e.message : "The discussion could not continue. Try again.");
    } finally {
      busy.current = false;
      setSpeaker(null);
    }
    if (alive.current && voiceRef.current) void startListening();
  }, [startListening]);

  const submit = useCallback(async (text: string) => {
    if (!text.trim() || busy.current) return;
    push({ speaker: USER, text: text.trim().slice(0, 1800) });
    await turn(true);
  }, [turn]);

  const begin = async () => {
    const t = (custom.trim() || topic).trim();
    if (t.length < 3) { setError("Choose a topic or type your own."); return; }
    stopAll();
    transcript.current = []; setMsgs([]); setResult(null); setElapsed(0); setError("");
    topicRef.current = t; voiceRef.current = voice; alive.current = true; busy.current = false;
    startedAt.current = Date.now();
    setStage("room");
    void turn(false);
  };

  const toggleMic = () => {
    if (listening) { listener.current?.stop(); return; }
    if (!busy.current) { stopSpeaking(); void startListening(); }
  };
  const letOthers = () => { if (!busy.current) void turn(false); };
  const nextTopic = () => {
    if (!window.confirm("Leave this discussion without feedback and pick a new topic?")) return;
    stopAll(); setStage("pick"); setTopic(""); setCustom(""); void loadTopics();
  };
  const finish = async () => {
    stopAll(); busy.current = false;
    setFinishing(true); setError("");
    try {
      const r = await post<{ feedback: Feedback; reward?: Reward }>("/gd/finish", {
        topic: topicRef.current, transcript: transcript.current, user_name: USER,
        duration_sec: Math.floor((Date.now() - startedAt.current) / 1000), voice: voiceRef.current,
      });
      announceReward(r.reward);
      setResult({ feedback: r.feedback, reward: r.reward ?? null });
      setStage("feedback");
    } catch (e) {
      alive.current = true;
      setError(e instanceof ApiError ? e.message : "Could not get feedback. Please try again.");
    } finally { setFinishing(false); }
  };

  const tiles = [{ name: USER, sub: voice ? (listening ? "Listening…" : "Your turn") : "Your turn" }, ...personas.map((p) => ({ name: p.name, sub: p.style.split(",")[0].slice(0, 40) })), { name: "Moderator", sub: "Keeps time" }];

  return (
    <div className="space-y-8">
      <Header module={module} />
      {error && <Notice tone="red">{error}</Notice>}

      {stage === "pick" && (
        <Panel className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-medium">Choose a topic</h2>
            <button type="button" className="btn-secondary" onClick={() => void loadTopics()} disabled={loadingTopics}>{loadingTopics ? "Loading…" : "New topics"}</button>
          </div>
          {loadingTopics && !topics.length ? <Spinner label="Fetching topics…" /> : (
            <div className="grid gap-2 sm:grid-cols-2">
              {topics.map((t) => (
                <label key={t} className={`flex cursor-pointer gap-3 rounded-md border px-3 py-2.5 text-sm ${topic === t && !custom ? "border-brand-600 bg-brand-50" : "border-slate-200"}`}>
                  <input type="radio" name="gd-topic" checked={topic === t && !custom} onChange={() => { setTopic(t); setCustom(""); }} />{t}
                </label>
              ))}
            </div>
          )}
          <div>
            <label className="label" htmlFor="gd-custom">Or write your own topic</label>
            <input id="gd-custom" className="input" value={custom} maxLength={300} onChange={(e) => setCustom(e.target.value)} placeholder="e.g. Should companies hire based on skills instead of degrees?" />
          </div>
          <div>
            <p className="label">How do you want to take part?</p>
            <Tabs<"text" | "voice"> value={voice ? "voice" : "text"} onChange={(v) => setVoice(v === "voice")} items={[{ id: "text", label: "Text" }, { id: "voice", label: "Voice" }]} />
            {voice && <p className="hint">{voiceOk ? "Speak naturally. The AI participants talk back out loud, and the room listens for you automatically. Headphones help avoid echo." : "Your browser cannot listen to speech (use Chrome or Edge). You will hear the participants but need to type your replies."}</p>}
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm text-ink-500">Participants: {personas.map((p) => <Chip key={p.name} tone="blue">{p.name}</Chip>)}<Chip>Moderator</Chip></div>
          <button type="button" className="btn-primary" disabled={!(custom.trim() || topic)} onClick={() => void begin()}>Start discussion</button>
        </Panel>
      )}

      {stage === "room" && (
        <div className="space-y-5">
          <Panel>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0"><p className="text-xs font-medium uppercase tracking-wide text-ink-500">Topic</p><h2 className="font-medium">{topicRef.current}</h2></div>
              <span className="rounded-md bg-slate-100 px-3 py-1 text-sm tabular-nums">{fmtTime(elapsed)}</span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
              {tiles.map((t) => {
                const active = t.name === USER ? listening : speaker === t.name;
                return (
                  <div key={t.name} className={`rounded-lg border p-3 text-center transition-all ${active ? "border-brand-600 bg-brand-50 ring-2 ring-brand-600/40" : "border-slate-200"}`} aria-current={active}>
                    <div className={`mx-auto flex h-12 w-12 items-center justify-center rounded-full text-lg font-semibold ${active ? "bg-brand-600 text-white animate-pulse" : "bg-slate-100 text-ink-700"}`}>{t.name[0]}</div>
                    <p className="mt-2 text-sm font-medium">{t.name}</p>
                    <p className="truncate text-xs text-ink-500">{active ? (t.name === USER ? "Listening…" : "Speaking…") : t.sub}</p>
                  </div>
                );
              })}
            </div>
          </Panel>

          <Panel className="space-y-4">
            <div className="max-h-96 space-y-3 overflow-y-auto" aria-label="Discussion transcript" aria-live="polite">
              {msgs.map((m, i) => (
                <div key={i} className={`flex ${m.speaker === USER ? "justify-end" : ""}`}>
                  <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${m.speaker === USER ? "bg-brand-50" : m.speaker === "Moderator" ? "bg-amber-50" : "bg-slate-100"}`}>
                    <p className="mb-0.5 text-xs font-medium text-ink-500">{m.speaker}</p>{m.text}
                  </div>
                </div>
              ))}
              {interim && <div className="flex justify-end"><div className="max-w-[85%] rounded-lg bg-brand-50/60 px-3 py-2 text-sm italic text-ink-700">{interim}</div></div>}
              {thinking && <p className="text-sm text-ink-500"><Spinner label="Others are thinking…" /></p>}
              <div ref={chatEnd} />
            </div>

            {voice && voiceOk && (
              <div className="flex items-center gap-3">
                <button type="button" className={listening ? "btn-primary" : "btn-secondary"} onClick={toggleMic} disabled={thinking || finishing}>{listening ? "Stop & send" : "Speak"}</button>
                <p className="text-sm text-ink-500">{listening ? "Listening — pause for two seconds when you finish." : "The room listens for you after each reply."}</p>
              </div>
            )}
            {(!voice || !voiceOk) && (
              <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); const t = typed; setTyped(""); void submit(t); }}>
                <label className="label" htmlFor="gd-msg">Your contribution</label>
                <textarea id="gd-msg" rows={3} className="input" value={typed} maxLength={1800} onChange={(e) => setTyped(e.target.value)} placeholder="Add your point, respond to someone by name, or ask a question." disabled={thinking || finishing} />
                <button type="submit" className="btn-primary" disabled={!typed.trim() || thinking || finishing}>Send</button>
              </form>
            )}

            <div className="flex flex-wrap gap-3 border-t border-slate-200 pt-4">
              <button type="button" className="btn-secondary" onClick={letOthers} disabled={thinking || finishing}>Let others continue</button>
              <button type="button" className="btn-secondary" onClick={nextTopic} disabled={finishing}>Next topic</button>
              <button type="button" className="btn-primary" onClick={() => void finish()} disabled={finishing || thinking || !msgs.some((m) => m.speaker === USER)}>{finishing ? "Evaluating…" : "End & get feedback"}</button>
            </div>
            {!msgs.some((m) => m.speaker === USER) && <p className="hint">Make at least one contribution to unlock feedback.</p>}
          </Panel>
        </div>
      )}

      {stage === "feedback" && result && (
        <div className="space-y-6">
          <Panel>
            <div className="flex flex-wrap items-center gap-6">
              <Ring value={result.feedback.overall_score} label="Overall" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-semibold">{result.feedback.verdict}</h2>{result.feedback.source !== "gemini" && <Chip tone="amber">Offline estimate</Chip>}</div>
                <p className="mt-1 text-sm text-ink-700">{result.feedback.summary}</p>
                <p className="mt-2 text-xs text-ink-500">{result.feedback.stats.turns} contributions · {result.feedback.stats.words} words · {result.feedback.stats.talk_share_percent}% talk share · {fmtTime(result.feedback.stats.duration_sec)}</p>
                {result.reward && <p className="mt-2 text-sm font-medium text-green-700">+{result.reward.xp_gained} XP{result.reward.level_up ? ` · Level up! You are now level ${result.reward.level}` : ""}</p>}
              </div>
            </div>
          </Panel>
          {Object.keys(result.feedback.scores || {}).length > 0 && (
            <Panel><h3 className="mb-3 font-medium">Skill breakdown</h3><div className="grid gap-4 sm:grid-cols-2">{Object.entries(result.feedback.scores).map(([k, v]) => <Bar key={k} label={k[0].toUpperCase() + k.slice(1)} value={v} />)}</div></Panel>
          )}
          <div className="grid gap-6 sm:grid-cols-2">
            {result.feedback.strengths?.length > 0 && <Panel><h3 className="mb-2 font-medium">Strengths</h3><List tone="good" items={result.feedback.strengths} /></Panel>}
            {result.feedback.improvements?.length > 0 && <Panel><h3 className="mb-2 font-medium">To improve</h3><List tone="bad" items={result.feedback.improvements} /></Panel>}
          </div>
          {(result.feedback.best_moment || result.feedback.missed_opportunity || result.feedback.model_contribution) && (
            <Panel className="space-y-3 text-sm text-ink-700">
              {result.feedback.best_moment && <p><span className="font-medium">Best moment: </span>{result.feedback.best_moment}</p>}
              {result.feedback.missed_opportunity && <p><span className="font-medium">Missed opportunity: </span>{result.feedback.missed_opportunity}</p>}
              {result.feedback.model_contribution && <p className="rounded-md bg-slate-50 p-3"><span className="font-medium">A contribution you could have made: </span>{result.feedback.model_contribution}</p>}
            </Panel>
          )}
          <div className="flex gap-3">
            <button type="button" className="btn-primary" onClick={() => { setStage("pick"); setTopic(""); setCustom(""); void loadTopics(); }}>Start another topic</button>
          </div>
        </div>
      )}
    </div>
  );
}
