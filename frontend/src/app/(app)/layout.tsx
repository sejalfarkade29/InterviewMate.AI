"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Logo } from "@/components/Logo";
import { useAuth } from "@/hooks/useAuth";
import { GROUPS, MODULES } from "@/lib/modules";
import { api } from "@/lib/api";
import type { Reward } from "@/lib/rewards";

type Summary = { xp: number; level: number; title: string; progress: number; streak: number };

/** Header chip (level, XP, streak) plus a toast whenever any module reports earned XP, a level-up or a new badge. */
function RewardHud() {
  const [sum, setSum] = useState<Summary | null>(null);
  const [toast, setToast] = useState<Reward | null>(null);
  useEffect(() => {
    const load = () => api<Summary>("/rewards").then(setSum).catch(() => undefined);
    void load();
    let timer: ReturnType<typeof setTimeout>;
    const onReward = (e: Event) => {
      const r = (e as CustomEvent<Reward>).detail;
      setSum((cur) => ({ xp: r.xp, level: r.level, title: r.title, progress: r.progress, streak: r.streak ?? cur?.streak ?? 0 }));
      if (r.xp_gained > 0 || r.level_up) { setToast(r); clearTimeout(timer); timer = setTimeout(() => setToast(null), r.level_up ? 7000 : 4000); }
    };
    window.addEventListener("im:reward", onReward);
    return () => { window.removeEventListener("im:reward", onReward); clearTimeout(timer); };
  }, []);
  return (
    <>
      {sum && (
        <Link href="/rewards" className="hidden items-center gap-2 rounded-full border border-slate-200 px-3 py-1 text-xs hover:bg-slate-50 sm:flex" title={`${sum.title} · ${sum.xp} XP`}>
          <span className="font-semibold text-brand-700">Level {sum.level}</span>
          <span className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100"><span className="block h-full rounded-full bg-brand-600" style={{ width: `${Math.max(4, sum.progress)}%` }} /></span>
          <span className="tabular-nums text-ink-500">{sum.xp} XP</span>
          {sum.streak > 0 && <span aria-label={`${sum.streak} day streak`}>🔥 {sum.streak}</span>}
        </Link>
      )}
      {toast && (
        <div role="status" className={`fixed bottom-5 right-5 z-50 max-w-xs rounded-lg border px-4 py-3 text-sm shadow-lg ${toast.level_up ? "border-amber-300 bg-amber-50" : "border-green-200 bg-green-50"}`}>
          {toast.level_up ? <p className="font-semibold">🎉 Level up! You are now level {toast.level} · {toast.title}</p> : <p className="font-semibold">+{toast.xp_gained} XP</p>}
          {toast.level_up && toast.xp_gained > 0 && <p className="text-ink-700">+{toast.xp_gained} XP earned</p>}
          {toast.new_badges?.map((b) => <p key={b.id} className="mt-1 text-ink-700">🏅 New badge: {b.name}</p>)}
        </div>
      )}
    </>
  );
}

function NavLink({ href, label }: { href: string; label: string }) {
  const active = usePathname() === href;
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`flex items-center justify-between rounded-md px-3 py-1.5 text-sm ${
        active ? "bg-brand-50 font-medium text-brand-700" : "text-ink-700 hover:bg-slate-100"
      }`}
    >
      <span>{label}</span>
    </Link>
  );
}

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => { if (!loading && !user) router.replace("/login"); }, [loading, user, router]);
  useEffect(() => setOpen(false), [pathname]);

  if (loading || !user) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-ink-500">Loading…</div>;
  }

  const sidebar = (
    <nav aria-label="Main" className="flex h-full flex-col gap-6 overflow-y-auto px-3 py-5">
      <div className="space-y-0.5">
        <NavLink href="/dashboard" label="Dashboard" />
        <NavLink href="/profile" label="Profile" />
      </div>
      {GROUPS.map((g) => (
        <div key={g}>
          <p className="mb-1 px-3 text-xs font-medium text-ink-500">{g}</p>
          <div className="space-y-0.5">
            {MODULES.filter((m) => m.group === g).map((m) => (
              <NavLink key={m.slug} href={`/${m.slug}`} label={m.title} />
            ))}
          </div>
        </div>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-200 bg-white px-4">
        <div className="flex items-center gap-3">
          <button className="btn-secondary px-2.5 py-1.5 lg:hidden" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-label="Toggle navigation">
            Menu
          </button>
          <Logo href="/dashboard" />
        </div>
        <div className="flex items-center gap-4 text-sm">
          <RewardHud />
          <span className="hidden text-ink-700 sm:inline">{user.full_name}</span>
          <button className="btn-secondary py-1.5" onClick={async () => { await logout(); router.push("/"); }}>
            Sign out
          </button>
        </div>
      </header>
      <div className="flex">
        <aside className="sticky top-14 hidden h-[calc(100vh-3.5rem)] w-60 shrink-0 border-r border-slate-200 lg:block">{sidebar}</aside>
        {open && (
          <aside className="fixed inset-x-0 bottom-0 top-14 z-20 w-full max-w-xs border-r border-slate-200 bg-white lg:hidden">{sidebar}</aside>
        )}
        <main className="min-w-0 flex-1 px-4 py-8 sm:px-8 lg:px-12">
          <div className="mx-auto max-w-4xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
