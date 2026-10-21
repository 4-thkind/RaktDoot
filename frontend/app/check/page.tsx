"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { show } from "@/lib/blood";
import { useLang, type Key } from "@/lib/i18n";

type Verdict = "looks_genuine" | "likely_stale" | "likely_fulfilled" | "unverified" | "possible_scam";
type Check = {
  id: string; verdict: Verdict; engine: string;
  reasons: { key: string; en: string; hi: string }[];
  fields: { patient_group: string | null; units: number | null; component: string | null; hospital: string | null; city: string | null; date: string | null; phone: string | null };
  offer: { hospital: string; donors: number } | null;
};

const TONE: Record<Verdict, string> = {
  looks_genuine: "var(--green)", likely_stale: "var(--ochre)", likely_fulfilled: "var(--muted)", unverified: "var(--ochre)", possible_scam: "var(--burgundy)",
};

/** F2 on the web: paste a forwarded plea, get a verdict with reasons, optionally alert donors with consent. */
export default function CheckForward() {
  const { t, lang } = useLang();
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<Check | null>(null);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [consent, setConsent] = useState(false);

  async function check(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setRes(null);
    try {
      setRes(await api<Check>("/api/forwards/check", { method: "POST", body: JSON.stringify({ text }) }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function alertDonors() {
    if (!res) return;
    setBusy(true);
    setError("");
    try {
      const r = await api<{ id: string; manage_token: string }>(`/api/forwards/${res.id}/alert`, {
        method: "POST", body: JSON.stringify({ name, phone, consent }),
      });
      router.push(`/request/${r.id}?t=${encodeURIComponent(r.manage_token)}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  const f = res?.fields;
  return (
    <div className="narrow stack" style={{ paddingTop: 32, ["--gap" as string]: "18px" }}>
      <h1 className="h1">{t("check_title")}</h1>
      <p className="muted" style={{ margin: "8px 0 0" }}>{t("check_body")}</p>
      <form className="stack" onSubmit={check}>
        <textarea className="input" rows={7} value={text} maxLength={4000} placeholder={t("check_ph")} onChange={(e) => setText(e.target.value)} />
        <button className="btn btn-primary btn-block" type="submit" disabled={busy || text.trim().length < 10}>{busy ? t("check_running") : t("check_btn")}</button>
      </form>
      {error && <p className="note" role="alert">{error}</p>}
      {res && (
        <section className="sheet stack" aria-live="polite" style={{ ["--gap" as string]: "12px", borderLeft: `4px solid ${TONE[res.verdict]}` }}>
          <h2 className="h2" style={{ color: TONE[res.verdict] }}>{t(`v_${res.verdict}` as Key)}</h2>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {res.reasons.map((r) => <li key={r.key}>{lang === "hi" ? r.hi : r.en}</li>)}
          </ul>
          {f && (
            <p className="small muted" style={{ margin: 0 }}>
              {t("check_read")}: {[f.patient_group && show(f.patient_group), f.units && `${f.units} unit(s)`, f.component && t(`comp_${f.component}` as Key),
                f.hospital, f.date, f.phone].filter(Boolean).join(" · ")}
            </p>
          )}
          {res.verdict !== "possible_scam" && <p className="small" style={{ margin: 0 }}>{t("check_dont")}</p>}
          {res.verdict === "looks_genuine" && res.offer && (
            <div className="pivot stack" style={{ ["--gap" as string]: "10px" }}>
              <h3 className="h3">{t("check_alert_title", { hospital: res.offer.hospital })}</h3>
              <p className="small" style={{ margin: 0 }}>{t("check_alert_body", { n: res.offer.donors })}</p>
              <input className="input" placeholder={t("your_name")} value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
              <input className="input num" type="tel" placeholder={t("your_phone")} value={phone} onChange={(e) => setPhone(e.target.value)} />
              <label className="small row" style={{ gap: 8, flexWrap: "nowrap", alignItems: "flex-start" }}>
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ marginTop: 5 }} />
                <span>{t("check_consent")}</span>
              </label>
              <button className="btn btn-primary" disabled={busy || !consent || !name.trim() || phone.replace(/\D/g, "").length < 10} onClick={alertDonors}>
                {t("check_alert_btn")}
              </button>
            </div>
          )}
        </section>
      )}
      <p className="tiny muted">{t("check_whatsapp")}</p>
    </div>
  );
}
