// Small wrappers around the browser's built-in speech recognition (listening) and speech synthesis (speaking).
type RecResult = { isFinal: boolean; 0: { transcript: string } };
type Rec = {
  lang: string; continuous: boolean; interimResults: boolean; start: () => void; stop: () => void; abort: () => void;
  onresult: ((e: { resultIndex: number; results: ArrayLike<RecResult> }) => void) | null;
  onend: (() => void) | null; onerror: ((e: { error: string }) => void) | null;
};
type RecCtor = new () => Rec;

export function recognitionCtor(): RecCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: RecCtor; webkitSpeechRecognition?: RecCtor };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}
export const supportsRecognition = () => recognitionCtor() !== null;
export const supportsSynthesis = () => typeof window !== "undefined" && "speechSynthesis" in window;

export type Listener = { stop: () => void; done: Promise<string> };

/** Listen for one spoken answer. Resolves with the final transcript when the person stops talking (or stop() is called). */
export function listen(onInterim?: (text: string) => void, lang = "en-US"): Listener {
  const Ctor = recognitionCtor();
  if (!Ctor) return { stop: () => undefined, done: Promise.resolve("") };
  const rec = new Ctor();
  rec.lang = lang; rec.continuous = true; rec.interimResults = true;
  let finalText = "";
  let interim = "";
  let resolve!: (t: string) => void;
  const done = new Promise<string>((r) => (resolve = r));
  let silence: ReturnType<typeof setTimeout> | null = null;
  const bump = () => { if (silence) clearTimeout(silence); silence = setTimeout(() => { try { rec.stop(); } catch { /* ignore */ } }, 2200); };
  rec.onresult = (e) => {
    interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const r = e.results[i];
      if (r.isFinal) finalText += r[0].transcript + " "; else interim += r[0].transcript;
    }
    onInterim?.((finalText + interim).trim());
    bump();
  };
  rec.onerror = () => { /* "no-speech" and "aborted" just end the session */ };
  rec.onend = () => { if (silence) clearTimeout(silence); resolve((finalText + interim).trim()); };
  try { rec.start(); } catch { resolve(""); }
  return { stop: () => { if (silence) clearTimeout(silence); try { rec.stop(); } catch { /* ignore */ } }, done };
}

let voicesCache: SpeechSynthesisVoice[] = [];
function loadVoices(): SpeechSynthesisVoice[] {
  if (!supportsSynthesis()) return [];
  if (!voicesCache.length) voicesCache = window.speechSynthesis.getVoices();
  return voicesCache;
}
if (supportsSynthesis()) window.speechSynthesis.onvoiceschanged = () => { voicesCache = window.speechSynthesis.getVoices(); };

const MALE = /(male|david|mark|george|james|daniel|alex|fred|ravi|rishi|google uk english male)/i;
const FEMALE = /(female|zira|samantha|victoria|susan|karen|heera|veena|moira|tessa|google us english|google uk english female)/i;

export function pickVoice(gender?: "male" | "female", index = 0): SpeechSynthesisVoice | null {
  const en = loadVoices().filter((v) => /^en/i.test(v.lang));
  if (!en.length) return null;
  const pool = gender === "male" ? en.filter((v) => MALE.test(v.name)) : gender === "female" ? en.filter((v) => FEMALE.test(v.name)) : [];
  const list = pool.length ? pool : en;
  return list[index % list.length];
}

export type SpeakOptions = { gender?: "male" | "female"; voiceIndex?: number; pitch?: number; rate?: number };

/** Speak text aloud; the promise resolves when the speech ends (or immediately if speech is unsupported). */
export function speak(text: string, opts: SpeakOptions = {}): Promise<void> {
  return new Promise((resolve) => {
    if (!supportsSynthesis() || !text.trim()) return resolve();
    const u = new SpeechSynthesisUtterance(text);
    const v = pickVoice(opts.gender, opts.voiceIndex ?? 0);
    if (v) u.voice = v;
    u.lang = v?.lang || "en-US";
    u.pitch = opts.pitch ?? 1;
    u.rate = opts.rate ?? 1;
    u.onend = () => resolve();
    u.onerror = () => resolve();
    window.speechSynthesis.speak(u);
  });
}
export function stopSpeaking() { if (supportsSynthesis()) window.speechSynthesis.cancel(); }
