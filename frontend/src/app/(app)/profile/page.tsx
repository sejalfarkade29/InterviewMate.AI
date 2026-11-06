"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import type { Profile } from "@/types";
import { getLocalProfile, saveLocalProfile } from "@/lib/localStore";

const LEVELS = ["student", "fresher", "0-2 years", "2-5 years", "5+ years"];

type Form = {
  full_name: string; education: string; college: string; degree: string; branch: string;
  graduation_year: string; skills: string; experience_level: string; career_interests: string; preferred_roles: string;
};

const toForm = (p: Profile): Form => ({
  full_name: p.full_name, education: p.education ?? "", college: p.college ?? "", degree: p.degree ?? "",
  branch: p.branch ?? "", graduation_year: p.graduation_year?.toString() ?? "", skills: p.skills.join(", "),
  experience_level: p.experience_level ?? "", career_interests: p.career_interests ?? "",
  preferred_roles: p.preferred_roles.join(", "),
});

const splitList = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
const orNull = (s: string) => (s.trim() ? s.trim() : null);

export default function ProfilePage() {
  const { user, setUserName } = useAuth();
  const [form, setForm] = useState<Form | null>(null);
  const [email, setEmail] = useState("");
  const [completeness, setCompleteness] = useState(0);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Profile>("/profile")
      .then((p) => { setForm(toForm(p)); setEmail(p.email); setCompleteness(p.completeness); })
      .catch(() => { const p = getLocalProfile() ?? { email: user?.email ?? "", full_name: user?.full_name ?? "", education: null, college: null, degree: null, branch: null, graduation_year: null, skills: [], experience_level: null, career_interests: null, preferred_roles: [], completeness: 0 }; setForm(toForm(p)); setEmail(p.email); setCompleteness(p.completeness); });
  }, [user]);

  const set = (k: keyof Form) => (e: { target: { value: string } }) => {
    setSaved(false);
    setForm((f) => (f ? { ...f, [k]: e.target.value } : f));
  };

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form) return;
    setError(""); setSaved(false); setBusy(true);
    try {
      const p = await api<Profile>("/profile", {
        method: "PUT",
        body: JSON.stringify({
          full_name: form.full_name,
          education: orNull(form.education), college: orNull(form.college),
          degree: orNull(form.degree), branch: orNull(form.branch),
          graduation_year: form.graduation_year ? Number(form.graduation_year) : null,
          skills: splitList(form.skills), experience_level: orNull(form.experience_level),
          career_interests: orNull(form.career_interests), preferred_roles: splitList(form.preferred_roles),
        }),
      });
      setForm(toForm(p)); setCompleteness(p.completeness); setUserName(p.full_name); setSaved(true);
    } catch {
      const next: Profile = { email, full_name: form.full_name, education: orNull(form.education), college: orNull(form.college), degree: orNull(form.degree), branch: orNull(form.branch), graduation_year: form.graduation_year ? Number(form.graduation_year) : null, skills: splitList(form.skills), experience_level: orNull(form.experience_level), career_interests: orNull(form.career_interests), preferred_roles: splitList(form.preferred_roles), completeness: [form.education, form.college, form.degree, form.branch, form.graduation_year, form.skills, form.experience_level, form.career_interests, form.preferred_roles].filter(Boolean).length * 100 / 9 };
      saveLocalProfile(next); setForm(toForm(next)); setCompleteness(next.completeness); setUserName(next.full_name); setSaved(true);
    } finally {
      setBusy(false);
    }
  }

  if (!form) {
    return error
      ? <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      : <p className="text-sm text-ink-500">Loading profile…</p>;
  }

  return (
    <form onSubmit={onSubmit} className="space-y-10" noValidate>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Profile</h1>
          <p className="mt-1 text-sm text-ink-500">{email} · {completeness}% complete</p>
        </div>
        <button type="submit" className="btn-primary" disabled={busy}>{busy ? "Saving…" : "Save changes"}</button>
      </div>

      {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {saved && <p role="status" className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">Profile saved.</p>}

      <fieldset className="grid gap-5 sm:grid-cols-2">
        <legend className="mb-4 font-medium">Personal and education</legend>
        <div className="sm:col-span-2">
          <label htmlFor="full_name" className="label">Full name</label>
          <input id="full_name" className="input" value={form.full_name} onChange={set("full_name")} />
        </div>
        <div>
          <label htmlFor="education" className="label">Education level</label>
          <input id="education" className="input" placeholder="e.g. Bachelor's" value={form.education} onChange={set("education")} />
        </div>
        <div>
          <label htmlFor="college" className="label">College or university</label>
          <input id="college" className="input" value={form.college} onChange={set("college")} />
        </div>
        <div>
          <label htmlFor="degree" className="label">Degree</label>
          <input id="degree" className="input" placeholder="e.g. B.Tech" value={form.degree} onChange={set("degree")} />
        </div>
        <div>
          <label htmlFor="branch" className="label">Branch</label>
          <input id="branch" className="input" placeholder="e.g. Computer Science" value={form.branch} onChange={set("branch")} />
        </div>
        <div>
          <label htmlFor="graduation_year" className="label">Graduation year</label>
          <input id="graduation_year" inputMode="numeric" className="input" placeholder="e.g. 2027" value={form.graduation_year} onChange={set("graduation_year")} />
        </div>
      </fieldset>

      <fieldset className="grid gap-5 sm:grid-cols-2">
        <legend className="mb-4 font-medium">Career</legend>
        <div>
          <label htmlFor="experience_level" className="label">Experience level</label>
          <select id="experience_level" className="input" value={form.experience_level} onChange={set("experience_level")}>
            <option value="">Select…</option>
            {LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="preferred_roles" className="label">Preferred job roles</label>
          <input id="preferred_roles" className="input" placeholder="AI Engineer, Backend Developer" value={form.preferred_roles} onChange={set("preferred_roles")} />
          <p className="hint">Separate roles with commas.</p>
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="skills" className="label">Skills</label>
          <input id="skills" className="input" placeholder="Python, SQL, FastAPI" value={form.skills} onChange={set("skills")} />
          <p className="hint">Separate skills with commas. List only skills you can discuss in an interview.</p>
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="career_interests" className="label">Career interests</label>
          <textarea id="career_interests" rows={3} className="input" value={form.career_interests} onChange={set("career_interests")} />
        </div>
      </fieldset>
    </form>
  );
}
