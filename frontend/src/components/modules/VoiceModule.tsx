"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, post, wsUrl } from "@/lib/api";
import { announceReward, type Reward } from "@/lib/rewards";
import { listen, speak, stopSpeaking, supportsRecognition, type Listener } from "@/lib/speech";
import type { ModuleInfo } from "@/lib/modules";
import { Bar, Chip, Header, List, Notice, Panel, Ring, Spinner, Tabs, fmtTime } from "@/components/ui";

type Mode = "voice" | "hr";
type Style = "friendly" | "neutral" | "strict";
type Config = { mode: Mode; role: string; style: Style; minutes: number };
type Turn = { role: "user" | "ai"; text: string; closed?: boolean };
type Feedback = {
  overall_score: number; verdict: string; summary: string; scores: Record<string, number>; strengths: string[]; improvements: string[];
  per_question: { question: string; answer_summary: string; score: number; comment: string; better_answer: string }[];
  filler_words?: { count?: number; examples?: string[] }; tips: string[]; stats?: { answers: number; words: number; duration_sec: number }; source: string;
};
type Finished = { feedback: Feedback; reward?: Reward | null };

// ---------------------------------------------------------------- audio helpers
const WORKLET_SRC = `class PcmCapture extends AudioWorkletProcessor {
  process(inputs) { const ch = inputs[0] && inputs[0][0]; if (ch) this.port.postMessage(ch.slice(0)); return true; }
}
registerProcessor('pcm-capture', PcmCapture);`;

/** Average-downsample float samples from `from` Hz to 16 kHz and convert to little-endian PCM16. */
function toPcm16(input: Float32Array, from: number): Int16Array {
  const ratio = from / 16000;
  const n = Math.floor(input.length / ratio);
  const out = new Int16Array(n);
  for (let i = 0; i < n; i++) {
    const start = Math.floor(i * ratio), end = Math.min(input.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end; j++) sum += input[j];
    const v = Math.max(-1, Math.min(1, sum / Math.max(1, end - start)));
    out[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
  }
  return out;
}

function micError(e: unknown): string {
  const name = (e as { name?: string })?.name;
  if (name === "NotAllowedError" || name === "SecurityError") return "Microphone access was blocked. Allow the microphone for this site in your browser settings, then try again.";
  if (name === "NotFoundError") return "No microphone was found. Connect one and try again.";
  if (name === "NotReadableError") return "Your microphone is being used by another application. Close it and try again.";
  return "Could not start the microphone. Check your browser permissions and try again.";
}

const ORB = {
  connecting: { label: "Connecting…", cls: "bg-slate-300 animate-pulse" },
  listening: { label: "Listening — speak whenever you are ready", cls: "bg-green-500" },
  speaking: { label: "Interviewer is speaking", cls: "bg-brand-600 animate-pulse" },
  muted: { label: "Microphone muted", cls: "bg-slate-400" },
  ending: { label: "Preparing your feedback…", cls: "bg-amber-500 animate-pulse" },
  thinking: { label: "Thinking…", cls: "bg-brand-100 animate-pulse" },
} as const;
type OrbState = keyof typeof ORB;

function Orb({ state }: { state: OrbState }) {
  const o = ORB[state];
  return (
    <div className="flex flex-col items-center gap-3 py-4" aria-live="polite">
      <div className="relative flex h-36 w-36 items-center justify-center">
        {(state === "listening" || state === "speaking") && <span className={`absolute inset-0 rounded-full opacity-25 animate-ping ${o.cls.split(" ")[0]}`} />}
        <span className={`relative h-28 w-28 rounded-full shadow-lg transition-colors ${o.cls}`} />
      </div>
      <p className="text-sm font-medium text-ink-700">{o.label}</p>
    </div>
  );
}

function TranscriptList({ turns, interim }: { turns: Turn[]; interim?: string }) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [turns, interim]);
  return (
    <div className="max-h-72 space-y-3 overflow-y-auto rounded-md border border-slate-200 p-4" aria-label="Transcript">
      {turns.length === 0 && !interim && <p className="text-sm text-ink-500">The conversation will appear here.</p>}
      {turns.map((t, i) => (
        <div key={i} className={`flex ${t.role === "user" ? "justify-end" : ""}`}>
          <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${t.role === "user" ? "bg-brand-50 text-ink-900" : "bg-slate-100 text-ink-900"}`}>
            <p className="mb-0.5 text-xs font-medium text-ink-500">{t.role === "user" ? "You" : "Interviewer"}</p>{t.text}
          </div>
        </div>
      ))}
      {interim && <div className="flex justify-end"><div className="max-w-[85%] rounded-lg bg-brand-50/60 px-3 py-2 text-sm italic text-ink-700">{interim}</div></div>}
      <div ref={end} />
    </div>
  );
}

// ---------------------------------------------------------------- feedback
function FeedbackPanel({ done, onAgain }: { done: Finished; onAgain: () => void }) {
  const f = done.feedback;
  const fillers = f.filler_words;
  return (
    <div className="space-y-6">
      <Panel>
        <div className="flex flex-wrap items-center gap-6">
          <Ring value={f.overall_score} label="Overall" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-semibold">{f.verdict || "Interview complete"}</h2>{f.source !== "gemini" && <Chip tone="amber">Offline estimate</Chip>}</div>
            <p className="mt-1 text-sm text-ink-700">{f.summary}</p>
            {f.stats && <p className="mt-2 text-xs text-ink-500">{f.stats.answers} answers · {f.stats.words} words · {fmtTime(f.stats.duration_sec)}</p>}
            {done.reward && <p className="mt-2 text-sm font-medium text-green-700">+{done.reward.xp_gained} XP{done.reward.level_up ? ` · Level up! You are now level ${done.reward.level}` : ""}</p>}
          </div>
        </div>
      </Panel>
      {Object.keys(f.scores || {}).length > 0 && (
        <Panel><h3 className="mb-3 font-medium">Skill breakdown</h3><div className="grid gap-4 sm:grid-cols-2">{Object.entries(f.scores).map(([k, v]) => <Bar key={k} label={k[0].toUpperCase() + k.slice(1)} value={v} />)}</div></Panel>
      )}
      <div className="grid gap-6 sm:grid-cols-2">
        {f.strengths?.length > 0 && <Panel><h3 className="mb-2 font-medium">Strengths</h3><List tone="good" items={f.strengths} /></Panel>}
        {f.improvements?.length > 0 && <Panel><h3 className="mb-2 font-medium">To improve</h3><List tone="bad" items={f.improvements} /></Panel>}
      </div>
      {f.per_question?.length > 0 && (
        <Panel>
          <h3 className="mb-3 font-medium">Question by question</h3>
          <div className="divide-y divide-slate-200">
            {f.per_question.map((q, i) => (
              <article key={i} className="py-4 first:pt-0 last:pb-0">
                <div className="flex items-start justify-between gap-3"><p className="text-sm font-medium">{q.question}</p><Chip tone={q.score >= 75 ? "green" : q.score >= 50 ? "amber" : "red"}>{q.score}/100</Chip></div>
                {q.answer_summary && <p className="mt-1 text-sm text-ink-500">You said: {q.answer_summary}</p>}
                {q.comment && <p className="mt-1 text-sm text-ink-700">{q.comment}</p>}
                {q.better_answer && <p className="mt-2 rounded-md bg-slate-50 p-3 text-sm text-ink-700"><span className="font-medium">Stronger version: </span>{q.better_answer}</p>}
              </article>
            ))}
          </div>
        </Panel>
      )}
      {(fillers?.count !== undefined || f.tips?.length > 0) && (
        <Panel>
          {fillers?.count !== undefined && <p className="mb-3 text-sm text-ink-700">Filler words: <strong>{fillers.count}</strong>{fillers.examples?.length ? ` (${fillers.examples.join(", ")})` : ""}</p>}
          {f.tips?.length > 0 && <><h3 className="mb-2 font-medium">Practice tips</h3><List items={f.tips} /></>}
        </Panel>
      )}
      <button type="button" className="btn-primary" onClick={onAgain}>Start another interview</button>
    </div>
  );
}

// ---------------------------------------------------------------- live (Gemini Live over the backend WebSocket)
type LiveProps = { cfg: Config; session: { token: string; path: string }; onDone: (d: Finished) => void; onFallback: (why: string) => void; onCancel: () => void };

function LiveSession({ cfg, session, onDone, onFallback, onCancel }: LiveProps) {
  const [status, setStatus] = useState<"connecting" | "live" | "ending">("connecting");
  const [speaking, setSpeaking] = useState(false);
  const [muted, setMuted] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [typed, setTyped] = useState("");
  const [elapsed, setElapsed] = useState(0);

  const ws = useRef<WebSocket | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const micCtx = useRef<AudioContext | null>(null);
  const playCtx = useRef<AudioContext | null>(null);
  const sources = useRef<Set<AudioBufferSourceNode>>(new Set());
  const nextTime = useRef(0);
  const readyRef = useRef(false);
  const mutedRef = useRef(false);
  const finished = useRef(false);
  const ending = useRef(false);
  const endTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cb = useRef({ onDone, onFallback });
  cb.current = { onDone, onFallback };

  const teardown = useCallback(() => {
    readyRef.current = false;
    if (endTimer.current) clearTimeout(endTimer.current);
    sources.current.forEach((s) => { try { s.stop(); } catch { /* already stopped */ } });
    sources.current.clear();
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    micCtx.current?.close().catch(() => undefined); micCtx.current = null;
    playCtx.current?.close().catch(() => undefined); playCtx.current = null;
    const sock = ws.current;
    ws.current = null;
    if (sock) { sock.onmessage = null; sock.onclose = null; sock.onerror = null; try { sock.close(); } catch { /* ignore */ } }
  }, []);

  const stopPlayback = () => {
    sources.current.forEach((s) => { try { s.stop(); } catch { /* ignore */ } });
    sources.current.clear();
    nextTime.current = 0;
    setSpeaking(false);
  };

  const playChunk = useCallback((buf: ArrayBuffer) => {
    const ctx = playCtx.current;
    if (!ctx || buf.byteLength < 2) return;
    const pcm = new Int16Array(buf.slice(0, buf.byteLength - (buf.byteLength % 2)));
    const audio = ctx.createBuffer(1, pcm.length, 24000);
    const ch = audio.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) ch[i] = pcm[i] / 0x8000;
    const src = ctx.createBufferSource();
    src.buffer = audio;
    src.connect(ctx.destination);
    const at = Math.max(ctx.currentTime + 0.02, nextTime.current);
    src.start(at);
    nextTime.current = at + audio.duration;
    sources.current.add(src);
    setSpeaking(true);
    src.onended = () => {
      sources.current.delete(src);
      if (sources.current.size === 0) setSpeaking(false);
    };
  }, []);

  const addText = useCallback((role: "user" | "ai", text: string) => {
    setTurns((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === role && !last.closed) return [...prev.slice(0, -1), { ...last, text: last.text + text }];
      return [...prev, { role, text }];
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const media = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
        if (cancelled) { media.getTracks().forEach((t) => t.stop()); return; }
        stream.current = media;
        const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        const mic = new AC();
        micCtx.current = mic;
        await mic.resume().catch(() => undefined);
        const url = URL.createObjectURL(new Blob([WORKLET_SRC], { type: "application/javascript" }));
        await mic.audioWorklet.addModule(url);
        URL.revokeObjectURL(url);
        const node = new AudioWorkletNode(mic, "pcm-capture");
        const source = mic.createMediaStreamSource(media);
        const mute = mic.createGain();
        mute.gain.value = 0; // keeps the graph alive without playing the mic back
        source.connect(node); node.connect(mute); mute.connect(mic.destination);
        const play = new AC({ sampleRate: 24000 });
        playCtx.current = play;
        await play.resume().catch(() => undefined);

        let carry = new Float32Array(0);
        const chunkIn = Math.round(mic.sampleRate * 0.1); // ~100 ms of input
        node.port.onmessage = (e: MessageEvent<Float32Array>) => {
          if (!readyRef.current || mutedRef.current || ws.current?.readyState !== WebSocket.OPEN) return;
          const merged = new Float32Array(carry.length + e.data.length);
          merged.set(carry); merged.set(e.data, carry.length);
          let offset = 0;
          while (merged.length - offset >= chunkIn) {
            const pcm = toPcm16(merged.subarray(offset, offset + chunkIn), mic.sampleRate);
            ws.current.send(pcm.buffer);
            offset += chunkIn;
          }
          carry = merged.slice(offset);
        };

        const sock = new WebSocket(wsUrl(session.path, session.token));
        sock.binaryType = "arraybuffer";
        ws.current = sock;
        sock.onerror = () => { if (!finished.current && !readyRef.current) { finished.current = true; teardown(); cb.current.onFallback("Could not open the live voice connection. Is the backend running on port 8000?"); } };
        sock.onclose = () => {
          if (finished.current) return;
          finished.current = true;
          teardown();
          if (!readyRef.current && !ending.current) cb.current.onFallback("The live voice connection closed before it started.");
          else setError("The live connection was closed. If you spoke for a while, check History for saved results.");
        };
        sock.onmessage = (ev) => {
          if (ev.data instanceof ArrayBuffer) { playChunk(ev.data); return; }
          let msg: { type?: string; [k: string]: unknown };
          try { msg = JSON.parse(ev.data as string); } catch { return; }
          switch (msg.type) {
            case "ready": readyRef.current = true; setStatus("live"); break;
            case "transcript": addText(msg.role === "user" ? "user" : "ai", String(msg.text ?? "")); break;
            case "interrupted": stopPlayback(); break;
            case "turn_complete": setTurns((p) => p.map((t) => ({ ...t, closed: true }))); break;
            case "notice": setNotice(String(msg.message ?? "")); break;
            case "error": {
              finished.current = true;
              const code = String(msg.code ?? "");
              const text = String(msg.message ?? "Live voice is unavailable.");
              teardown();
              if (code === "no_key" || code === "live_unavailable") cb.current.onFallback(text);
              else setError(text);
              break;
            }
            case "feedback": {
              finished.current = true;
              cb.current.onDone({ feedback: msg.feedback as Feedback, reward: (msg.reward as Reward) ?? null });
              teardown();
              break;
            }
          }
        };
      } catch (e) {
        if (!cancelled) setError(micError(e));
        teardown();
      }
    })();
    return () => { cancelled = true; finished.current = true; teardown(); };
  }, [session.path, session.token, teardown, playChunk, addText]);

  useEffect(() => {
    if (status !== "live") return;
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [status]);

  const send = (obj: object) => { if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(obj)); };
  const toggleMute = () => { mutedRef.current = !mutedRef.current; setMuted(mutedRef.current); };
  const next = () => { stopPlayback(); send({ type: "next" }); };
  const sendTyped = () => { const t = typed.trim(); if (!t) return; addText("user", t); setTurns((p) => p.map((x) => ({ ...x, closed: true }))); send({ type: "text", text: t }); setTyped(""); };
  const end = () => {
    ending.current = true;
    setStatus("ending");
    stopPlayback();
    send({ type: "end" });
    endTimer.current = setTimeout(() => { setError("Feedback is taking too long. Please try again in a moment."); finished.current = true; teardown(); }, 75000);
  };

  const orb: OrbState = status === "connecting" ? "connecting" : status === "ending" ? "ending" : speaking ? "speaking" : muted ? "muted" : "listening";

  if (error) return (
    <Panel className="space-y-4">
      <Notice tone="red">{error}</Notice>
      <div className="flex gap-3">
        <button type="button" className="btn-primary" onClick={() => onFallback("Switched to browser voice mode.")}>Use browser voice instead</button>
        <button type="button" className="btn-secondary" onClick={onCancel}>Back</button>
      </div>
    </Panel>
  );

  return (
    <div className="space-y-5">
      <Panel>
        <div className="flex items-center justify-between text-sm text-ink-500"><span>Live voice · {cfg.mode === "hr" ? "HR round" : "Interview"} · {cfg.role}</span><span className="tabular-nums">{fmtTime(elapsed)} / {cfg.minutes}:00</span></div>
        <Orb state={orb} />
        {notice && <Notice tone="amber">{notice}</Notice>}
        <div className="mt-4 flex flex-wrap justify-center gap-3">
          <button type="button" className="btn-secondary" onClick={toggleMute} disabled={status !== "live"}>{muted ? "Unmute microphone" : "Mute microphone"}</button>
          <button type="button" className="btn-secondary" onClick={next} disabled={status !== "live"}>Next question</button>
          <button type="button" className="btn-primary" onClick={end} disabled={status !== "live"}>End &amp; get feedback</button>
        </div>
        {status === "ending" && <p className="mt-4 text-center"><Spinner label="Evaluating your interview…" /></p>}
        {status === "connecting" && <p className="mt-4 text-center"><Spinner label="Starting live session…" /></p>}
      </Panel>
      <Panel className="space-y-3">
        <TranscriptList turns={turns} />
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); sendTyped(); }}>
          <input className="input" value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="Or type a message to the interviewer" disabled={status !== "live"} aria-label="Type a message" />
          <button type="submit" className="btn-secondary" disabled={status !== "live" || !typed.trim()}>Send</button>
        </form>
      </Panel>
    </div>
  );
}

// ---------------------------------------------------------------- browser fallback (SpeechRecognition + speechSynthesis)
type BrowserProps = { cfg: Config; why: string; onDone: (d: Finished) => void; onCancel: () => void };

function BrowserSession({ cfg, why, onDone, onCancel }: BrowserProps) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [phase, setPhase] = useState<"starting" | "thinking" | "speaking" | "listening" | "idle" | "ending">("starting");
  const [interim, setInterim] = useState("");
  const [typed, setTyped] = useState("");
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const history = useRef<Turn[]>([]);
  const alive = useRef(true);
  const busy = useRef(false);
  const listener = useRef<Listener | null>(null);
  const started = useRef(Date.now());
  const canListen = supportsRecognition();

  const startListening = useCallback(async () => {
    if (!alive.current || !canListen) { setPhase("idle"); return; }
    setPhase("listening"); setInterim("");
    const l = listen(setInterim);
    listener.current = l;
    const text = await l.done;
    listener.current = null;
    if (!alive.current || busy.current) return;
    setInterim("");
    if (text.trim()) void runTurn(text.trim());
    else void startListening();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canListen]);

  const runTurn = useCallback(async (userText: string) => {
    if (busy.current || !alive.current) return;
    busy.current = true;
    setPhase("thinking");
    try {
      const sent = history.current.map((t) => ({ role: t.role, text: t.text }));
      const res = await post<{ reply: string }>("/voice/turn", { ...cfg, history: sent, user_text: userText });
      if (!alive.current) return;
      if (userText) history.current.push({ role: "user", text: userText });
      history.current.push({ role: "ai", text: res.reply });
      setTurns([...history.current]);
      setPhase("speaking");
      await speak(res.reply);
    } catch (e) {
      if (alive.current) setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      busy.current = false;
    }
    if (alive.current && !error) { if (canListen) void startListening(); else setPhase("idle"); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cfg, canListen, startListening]);

  useEffect(() => {
    alive.current = true;
    void runTurn("");
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - started.current) / 1000)), 1000);
    return () => { alive.current = false; clearInterval(t); listener.current?.stop(); stopSpeaking(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const interrupt = () => { listener.current?.stop(); stopSpeaking(); };
  const sendTyped = () => {
    const t = typed.trim();
    if (!t || busy.current) return;
    setTyped("");
    interrupt();
    setTimeout(() => void runTurn(t), 50);
  };
  const next = () => { if (busy.current) { stopSpeaking(); return; } interrupt(); setTimeout(() => void runTurn("Next question please."), 50); };
  const end = async () => {
    alive.current = false; listener.current?.stop(); stopSpeaking();
    setPhase("ending");
    try {
      const res = await post<{ feedback: Feedback; reward?: Reward }>("/voice/feedback", { mode: cfg.mode, role: cfg.role, transcript: history.current.map((t) => ({ role: t.role, text: t.text })), duration_sec: Math.floor((Date.now() - started.current) / 1000) });
      onDone({ feedback: res.feedback, reward: res.reward ?? null });
    } catch (e) {
      alive.current = true;
      setPhase("idle");
      setError(e instanceof ApiError ? e.message : "Could not get feedback. Please try again.");
    }
  };

  const orb: OrbState = phase === "speaking" ? "speaking" : phase === "listening" ? "listening" : phase === "ending" ? "ending" : phase === "idle" ? "muted" : "thinking";

  return (
    <div className="space-y-5">
      <Notice tone="amber">{why || "Using browser voice mode."} {canListen ? "Your browser listens and speaks for you." : "Your browser cannot listen, so type your answers (Chrome or Edge support speaking them)."}</Notice>
      {error && <Notice tone="red">{error}</Notice>}
      <Panel>
        <div className="flex items-center justify-between text-sm text-ink-500"><span>Browser voice · {cfg.mode === "hr" ? "HR round" : "Interview"} · {cfg.role}</span><span className="tabular-nums">{fmtTime(elapsed)} / {cfg.minutes}:00</span></div>
        <Orb state={orb} />
        {interim && <p className="text-center text-sm italic text-ink-700">{interim}</p>}
        <div className="mt-4 flex flex-wrap justify-center gap-3">
          {canListen && phase === "listening" && <button type="button" className="btn-secondary" onClick={() => listener.current?.stop()}>I&apos;m done answering</button>}
          {canListen && phase === "idle" && <button type="button" className="btn-secondary" onClick={() => void startListening()}>Start speaking</button>}
          <button type="button" className="btn-secondary" onClick={next} disabled={phase === "ending" || phase === "starting"}>Next question</button>
          <button type="button" className="btn-primary" onClick={() => void end()} disabled={phase === "ending" || turns.length === 0}>End &amp; get feedback</button>
          <button type="button" className="btn-secondary" onClick={() => { alive.current = false; interrupt(); onCancel(); }}>Cancel</button>
        </div>
        {phase === "ending" && <p className="mt-4 text-center"><Spinner label="Evaluating your interview…" /></p>}
      </Panel>
      <Panel className="space-y-3">
        <TranscriptList turns={turns} />
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); sendTyped(); }}>
          <input className="input" value={typed} onChange={(e) => setTyped(e.target.value)} placeholder={canListen ? "Or type your answer" : "Type your answer"} aria-label="Type your answer" />
          <button type="submit" className="btn-secondary" disabled={!typed.trim() || phase === "thinking" || phase === "ending"}>Send</button>
        </form>
      </Panel>
    </div>
  );
}

// ---------------------------------------------------------------- page
export function VoiceModule({ module, mode }: { module: ModuleInfo; mode: Mode }) {
  const [cfg, setCfg] = useState<Config>({ mode, role: mode === "hr" ? "Software Engineer (fresher)" : "Software Engineer (fresher)", style: "neutral", minutes: 10 });
  const [stage, setStage] = useState<"setup" | "live" | "browser" | "feedback">("setup");
  const [session, setSession] = useState<{ token: string; path: string } | null>(null);
  const [why, setWhy] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState<Finished | null>(null);
  const [engine, setEngine] = useState<"live" | "browser">("live");

  const start = async (force?: "browser") => {
    setError(""); setBusy(true);
    try {
      if (force === "browser" || engine === "browser") { setWhy("Browser voice mode selected."); setStage("browser"); return; }
      const s = await post<{ token: string; path: string; live_available: boolean }>("/voice/session", cfg);
      if (s.live_available) { setSession({ token: s.token, path: s.path }); setStage("live"); }
      else { setWhy("Live voice needs a Gemini API key on the server, so browser voice mode is used."); setStage("browser"); }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not start the interview.");
    } finally { setBusy(false); }
  };
  const finish = (d: Finished) => { announceReward(d.reward); setDone(d); setStage("feedback"); };
  const reset = () => { setStage("setup"); setDone(null); setSession(null); };

  return (
    <div className="space-y-8">
      <Header module={module} />
      {stage === "setup" && (
        <Panel className="space-y-5">
          <Notice>Use headphones. Without them the microphone can pick up the interviewer&apos;s voice and cause echo. Your latest analyzed resume is used automatically to personalise questions.</Notice>
          {error && <Notice tone="red">{error}</Notice>}
          <div>
            <label className="label" htmlFor="v-role">Role you are interviewing for</label>
            <input id="v-role" className="input" value={cfg.role} maxLength={120} onChange={(e) => setCfg({ ...cfg, role: e.target.value })} />
          </div>
          <div>
            <p className="label">Interviewer style</p>
            <Tabs<Style> value={cfg.style} onChange={(style) => setCfg({ ...cfg, style })} items={[{ id: "friendly", label: "Friendly" }, { id: "neutral", label: "Neutral" }, { id: "strict", label: "Strict" }]} />
          </div>
          <div>
            <label className="label" htmlFor="v-min">Length: {cfg.minutes} minutes</label>
            <input id="v-min" type="range" min={3} max={20} value={cfg.minutes} onChange={(e) => setCfg({ ...cfg, minutes: Number(e.target.value) })} className="w-full max-w-sm" />
          </div>
          <div>
            <p className="label">Voice engine</p>
            <Tabs<"live" | "browser"> value={engine} onChange={setEngine} items={[{ id: "live", label: "Live AI voice (Gemini)" }, { id: "browser", label: "Browser voice" }]} />
            <p className="hint">Live AI voice is a real-time conversation. Browser voice is the fallback and is used automatically if live voice is unavailable.</p>
          </div>
          <button type="button" className="btn-primary" disabled={busy || !cfg.role.trim()} onClick={() => void start()}>{busy ? "Starting…" : mode === "hr" ? "Start HR voice interview" : "Start voice interview"}</button>
        </Panel>
      )}
      {stage === "live" && session && (
        <LiveSession cfg={cfg} session={session} onDone={finish} onCancel={reset} onFallback={(w) => { setWhy(w); setStage("browser"); }} />
      )}
      {stage === "browser" && <BrowserSession cfg={cfg} why={why} onDone={finish} onCancel={reset} />}
      {stage === "feedback" && done && <FeedbackPanel done={done} onAgain={reset} />}
    </div>
  );
}
