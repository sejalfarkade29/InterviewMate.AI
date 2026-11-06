"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { AuthShell } from "@/components/AuthShell";
import { useAuth } from "@/hooks/useAuth";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      setError("Password must be at least 8 characters and include a letter and a number.");
      return;
    }
    setBusy(true);
    try {
      await register(name, email, password);
      router.push("/profile");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the account");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Create your account" subtitle="It takes a minute. You can finish your profile afterwards.">
      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <div>
          <label htmlFor="name" className="label">Full name</label>
          <input id="name" autoComplete="name" required className="input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label htmlFor="email" className="label">Email</label>
          <input id="email" type="email" autoComplete="email" required className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label htmlFor="password" className="label">Password</label>
          <input id="password" type="password" autoComplete="new-password" required className="input" value={password} onChange={(e) => setPassword(e.target.value)} />
          <p className="hint">At least 8 characters, with a letter and a number.</p>
        </div>
        <button type="submit" className="btn-primary w-full" disabled={busy || !name || !email || !password}>
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="mt-6 text-sm text-ink-500">
        Already registered? <Link href="/login" className="font-medium text-brand-600 hover:underline">Sign in</Link>
      </p>
    </AuthShell>
  );
}
