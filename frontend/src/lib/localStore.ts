import type { Attempt, Profile, User } from "@/types";

const KEYS = { session: "interviewmate:session", profile: "interviewmate:profile", attempts: "interviewmate:attempts", roadmap: "interviewmate:roadmap", daily: "interviewmate:daily", questionState: "interviewmate:question-state" } as const;
type StoredSession = User & { email: string };
type DailyState = { completedOn: string | null; streak: number };
type QuestionState = Record<string, string[]>;
function read<T>(key: string, fallback: T): T { if (typeof window === "undefined") return fallback; try { return JSON.parse(localStorage.getItem(key) || "null") ?? fallback; } catch { return fallback; } }
function write<T>(key: string, value: T) { if (typeof window !== "undefined") localStorage.setItem(key, JSON.stringify(value)); }
export function getLocalSession(): StoredSession | null { return read<StoredSession | null>(KEYS.session, null); }
export function saveLocalSession(user: StoredSession) { write(KEYS.session, user); }
export function clearLocalSession() { if (typeof window !== "undefined") localStorage.removeItem(KEYS.session); }
export function getLocalProfile(): Profile | null { return read<Profile | null>(KEYS.profile, null); }
export function saveLocalProfile(profile: Profile): Profile { write(KEYS.profile, profile); const session = getLocalSession(); if (session) saveLocalSession({ ...session, full_name: profile.full_name }); return profile; }
export function getAttempts(): Attempt[] { return read<Attempt[]>(KEYS.attempts, []).sort((a, b) => b.createdAt.localeCompare(a.createdAt)); }
export function saveAttempt(input: Omit<Attempt, "id" | "createdAt">): Attempt { const attempt = { ...input, id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, createdAt: new Date().toISOString() }; write(KEYS.attempts, [attempt, ...getAttempts()].slice(0, 200)); window.dispatchEvent(new Event("interviewmate:attempts")); return attempt; }
export function replaceAttempts(attempts: Attempt[]) { write(KEYS.attempts, attempts); window.dispatchEvent(new Event("interviewmate:attempts")); }
export function clearAttempts() { write(KEYS.attempts, []); window.dispatchEvent(new Event("interviewmate:attempts")); }
export function getQuestionState(): QuestionState { return read<QuestionState>(KEYS.questionState, {}); }
export function reserveQuestion(module: string, ids: string[]) { const state = getQuestionState(); const used = new Set(state[module] || []); const attempts = getAttempts().filter((a) => a.module === module); const available = ids.filter((id) => !used.has(id)); const id = available[0] || ids[attempts.length % Math.max(ids.length, 1)] || "generated"; write(KEYS.questionState, { ...state, [module]: [...(state[module] || []), id].slice(-200) }); return { id, level: Math.min(5, 1 + Math.floor(attempts.length / 2)) }; }
export function getRoadmap(): Record<string, boolean> { return read<Record<string, boolean>>(KEYS.roadmap, {}); }
export function setRoadmapItem(id: string, value: boolean) { const next = { ...getRoadmap(), [id]: value }; write(KEYS.roadmap, next); return next; }
export function getDailyState(): DailyState { return read<DailyState>(KEYS.daily, { completedOn: null, streak: 0 }); }
export function completeDaily(): DailyState { const today = new Date().toISOString().slice(0, 10); const current = getDailyState(); if (current.completedOn === today) return current; const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10); const next = { completedOn: today, streak: current.completedOn === yesterday ? current.streak + 1 : 1 }; write(KEYS.daily, next); return next; }
