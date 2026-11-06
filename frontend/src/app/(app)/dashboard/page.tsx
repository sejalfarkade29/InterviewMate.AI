"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { MODULES } from "@/lib/modules";
import type { Profile } from "@/types";

type Rewards = { xp: number; level: number; title: string; progress: number; xp_into_level: number; xp_for_next: number; streak: number; total_activities: number };
type Analytics = { total: number; average: number; weakest: { module: string; topic: string; avg: number }[] };

export default function Dashboard() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [rewards, setRewards] = useState<Rewards | null>(null);
  const [stats, setStats] = useState<Analytics | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Profile>("/profile").then(setProfile).catch((e) => setError(e.message));
    api<Rewards>("/rewards").then(setRewards).catch(() => undefined);
    api<Analytics>("/analytics").then(setStats).catch(() => undefined);
  }, []);

  const featured = ["resume", "daily", "voice", "coding"].map((s) => MODULES.find((m) => m.slug === s)!).filter(Boolean);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Welcome, {user?.full_name.split(" ")[0]}</h1>
        <p className="mt-1 text-sm text-ink-500">Your preparation overview.</p>
      </div>

      {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <section aria-labelledby="level-h" className="rounded-lg border border-slate-200 p-5">
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex h-20 w-20 shrink-0 flex-col items-center justify-center rounded-full bg-brand-600 text-white"><span className="text-[10px] uppercase tracking-wide opacity-80">Level</span><span className="text-2xl font-semibold leading-none">{rewards?.level ?? 1}</span></div>
          <div className="min-w-[200px] flex-1">
            <h2 id="level-h" className="font-medium">{rewards?.title ?? "Beginner"}</h2>
            <p className="text-sm text-ink-500">{rewards ? `${rewards.xp} XP · ${rewards.xp_into_level}/${rewards.xp_for_next} to level ${rewards.level + 1}` : "Answer questions to earn XP."}</p>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={rewards?.progress ?? 0} aria-valuemin={0} aria-valuemax={100} aria-label="Progress to next level"><div className="h-full rounded-full bg-brand-600" style={{ width: `${Math.max(3, rewards?.progress ?? 0)}%` }} /></div>
          </div>
          <div className="flex gap-6 text-sm">
            <div><p className="text-xs uppercase tracking-wide text-ink-500">Streak</p><p className="text-xl font-semibold">🔥 {rewards?.streak ?? 0}</p></div>
            <div><p className="text-xs uppercase tracking-wide text-ink-500">Average</p><p className="text-xl font-semibold">{stats?.average ?? 0}%</p></div>
            <div><p className="text-xs uppercase tracking-wide text-ink-500">Activities</p><p className="text-xl font-semibold">{stats?.total ?? 0}</p></div>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-3 text-sm"><Link href="/rewards" className="text-brand-700 hover:underline">Rewards &amp; badges →</Link><Link href="/history" className="text-brand-700 hover:underline">History →</Link><Link href="/analytics" className="text-brand-700 hover:underline">Analytics →</Link></div>
      </section>

      <section aria-labelledby="profile-h" className="rounded-lg border border-slate-200 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="profile-h" className="font-medium">Profile completeness</h2>
            <p className="mt-0.5 text-sm text-ink-500">A complete profile lets questions be tailored to your background.</p>
          </div>
          <Link href="/profile" className="btn-secondary">{profile && profile.completeness === 100 ? "View profile" : "Complete profile"}</Link>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={profile?.completeness ?? 0} aria-valuemin={0} aria-valuemax={100} aria-label="Profile completeness">
            <div className="h-full rounded-full bg-brand-600" style={{ width: `${profile?.completeness ?? 0}%` }} />
          </div>
          <span className="w-10 text-right text-sm tabular-nums">{profile ? `${profile.completeness}%` : "–"}</span>
        </div>
      </section>

      {stats && stats.weakest.length > 0 && (
        <section className="rounded-lg border border-slate-200 p-5">
          <h2 className="font-medium">Focus next</h2>
          <ul className="mt-3 space-y-1.5 text-sm">{stats.weakest.slice(0, 3).map((w, i) => <li key={i} className="flex justify-between"><span>{w.topic}</span><span className="text-ink-500">{w.avg}% average</span></li>)}</ul>
        </section>
      )}

      <section aria-labelledby="next-h">
        <h2 id="next-h" className="font-medium">Start here</h2>
        <ul className="mt-4 divide-y divide-slate-200 rounded-lg border border-slate-200">
          {featured.map((m) => (
            <li key={m.slug}>
              <Link href={`/${m.slug}`} className="flex items-center justify-between gap-4 px-5 py-3.5 hover:bg-slate-50">
                <div><p className="text-sm font-medium">{m.title}</p><p className="text-sm text-ink-500">{m.summary}</p></div>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
