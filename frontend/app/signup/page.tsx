"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { signup } from "@/lib/auth";
import { useLang } from "@/lib/i18n";

const C = {
  title: { en: "Create your account", hi: "अपना अकाउंट बनाएं" },
  lede: {
    en: "One account to track your requests. We will send a welcome message to your WhatsApp.",
    hi: "अपने अनुरोधों पर नज़र रखने के लिए एक अकाउंट। हम आपके WhatsApp पर स्वागत संदेश भेजेंगे।",
  },
  name: { en: "Full name", hi: "पूरा नाम" },
  email: { en: "Email", hi: "ईमेल" },
  phone: { en: "WhatsApp number", hi: "WhatsApp नंबर" },
  phone_help: { en: "10-digit mobile number. This is where the welcome message goes.", hi: "10 अंकों का मोबाइल नंबर। स्वागत संदेश इसी पर आएगा।" },
  password: { en: "Password", hi: "पासवर्ड" },
  password_help: { en: "At least 8 characters.", hi: "कम से कम 8 अक्षर।" },
  consent: {
    en: "Yes, Rakt Doot may message me on WhatsApp. I can reply STOP at any time.",
    hi: "हाँ, रक्त दूत मुझे WhatsApp पर संदेश भेज सकता है। मैं कभी भी STOP भेज सकता/सकती हूँ।",
  },
  submit: { en: "Sign up", hi: "साइन अप करें" },
  busy: { en: "Creating account...", hi: "अकाउंट बन रहा है..." },
  have: { en: "Already have an account?", hi: "पहले से अकाउंट है?" },
  login: { en: "Log in", hi: "लॉग इन करें" },
  done_t: { en: "You are in.", hi: "आप जुड़ गए।" },
  done_wa: { en: "A welcome message is on its way to your WhatsApp.", hi: "आपके WhatsApp पर स्वागत संदेश भेजा जा रहा है।" },
  done_confirm: { en: "Almost there. We emailed you a link: confirm your email, then log in. Your WhatsApp welcome follows your first login.", hi: "बस थोड़ा और। हमने आपको एक लिंक ईमेल किया है: ईमेल कन्फर्म करें, फिर लॉग इन करें। WhatsApp स्वागत संदेश पहले लॉग इन के बाद आएगा।" },
  done_nowa: { en: "Your account is ready. You chose not to get WhatsApp messages.", hi: "आपका अकाउंट तैयार है। आपने WhatsApp संदेश नहीं चुने।" },
  go: { en: "Continue", hi: "आगे बढ़ें" },
};

export default function Signup() {
  const { lang } = useLang();
  const L = (x: { en: string; hi: string }) => x[lang];
  const router = useRouter();
  const [f, setF] = useState({ name: "", email: "", phone: "", password: "", consent: true });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<"wa" | "nowa" | "confirm" | null>(null); // null = still on the form

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const r = await signup({ name: f.name, email: f.email, phone: f.phone, password: f.password, whatsapp_consent: f.consent, language: lang });
      setDone(r.needsConfirm ? "confirm" : f.consent ? "wa" : "nowa");
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (done !== null) {
    return (
      <div className="wrap" style={{ paddingTop: 40, maxWidth: 520 }}>
        <h1 className="display" style={{ fontSize: "clamp(34px, 6vw, 52px)" }}>{L(C.done_t)}</h1>
        <p className="lede">{done === "confirm" ? L(C.done_confirm) : done === "wa" ? L(C.done_wa) : L(C.done_nowa)}</p>
        <div style={{ marginTop: 24 }}>
          <button className="btn btn-primary btn-block" onClick={() => router.push("/")}>{L(C.go)}</button>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap" style={{ paddingTop: 40, maxWidth: 520 }}>
      <h1 className="display" style={{ fontSize: "clamp(34px, 6vw, 52px)" }}>{L(C.title)}</h1>
      <p className="lede">{L(C.lede)}</p>
      <form onSubmit={submit} className="stack" style={{ marginTop: 24 }} noValidate>
        <label className="field">
          <span className="label">{L(C.name)}</span>
          <input className="input" autoComplete="name" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
        </label>
        <label className="field">
          <span className="label">{L(C.email)}</span>
          <input className="input" type="email" autoComplete="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        </label>
        <label className="field">
          <span className="label">{L(C.phone)}</span>
          <input className="input" type="tel" inputMode="tel" autoComplete="tel" required value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} />
          <span className="help">{L(C.phone_help)}</span>
        </label>
        <label className="field">
          <span className="label">{L(C.password)}</span>
          <input className="input" type="password" autoComplete="new-password" minLength={8} required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
          <span className="help">{L(C.password_help)}</span>
        </label>
        <label className="row" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
          <input type="checkbox" checked={f.consent} onChange={(e) => setF({ ...f, consent: e.target.checked })} style={{ marginTop: 5 }} />
          <span>{L(C.consent)}</span>
        </label>
        {err && <p className="err" role="alert">{err}</p>}
        <button className="btn btn-primary btn-block" disabled={busy}>{busy ? L(C.busy) : L(C.submit)}</button>
        <p className="note">{L(C.have)} <Link href="/login">{L(C.login)}</Link></p>
      </form>
    </div>
  );
}