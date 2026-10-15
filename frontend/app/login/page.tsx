"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { login } from "@/lib/auth";
import { useLang } from "@/lib/i18n";

const C = {
  title: { en: "Log in", hi: "लॉग इन करें" },
  email: { en: "Email", hi: "ईमेल" },
  password: { en: "Password", hi: "पासवर्ड" },
  submit: { en: "Log in", hi: "लॉग इन" },
  busy: { en: "Logging in...", hi: "लॉग इन हो रहा है..." },
  new: { en: "New here?", hi: "नए हैं?" },
  signup: { en: "Create an account", hi: "अकाउंट बनाएं" },
};

export default function Login() {
  const { lang } = useLang();
  const L = (x: { en: string; hi: string }) => x[lang];
  const router = useRouter();
  const [f, setF] = useState({ email: "", password: "" });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await login(f);
      router.push("/");
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : "Something went wrong. Please try again.");
      setBusy(false);
    }
  }

  return (
    <div className="wrap" style={{ paddingTop: 40, maxWidth: 520 }}>
      <h1 className="display" style={{ fontSize: "clamp(34px, 6vw, 52px)" }}>{L(C.title)}</h1>
      <form onSubmit={submit} className="stack" style={{ marginTop: 24 }} noValidate>
        <label className="field">
          <span className="label">{L(C.email)}</span>
          <input className="input" type="email" autoComplete="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        </label>
        <label className="field">
          <span className="label">{L(C.password)}</span>
          <input className="input" type="password" autoComplete="current-password" required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
        </label>
        {err && <p className="err" role="alert">{err}</p>}
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? L(C.busy) : L(C.submit)}</button>
        <p className="note">{L(C.new)} <Link href="/signup">{L(C.signup)}</Link></p>
      </form>
    </div>
  );
}