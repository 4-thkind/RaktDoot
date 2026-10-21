"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { GROUPS, show } from "@/lib/blood";
import { useLang } from "@/lib/i18n";

type Reg = { id: string; status: "started" | "otp_sent" | "registered" | "failed"; steps: string[]; ref: string | null; error: string | null;
  engine: string; demo_sms: string | null };

/** A2: Rakt Doot fills the camp sign-up (captcha included); the donor only types the OTP. */
export function CampRegister({ campId, title }: { campId: string; title: string }) {
  const { t } = useLang();
  const [f, setF] = useState({ name: "", phone: "", dob: "", gender: "M", blood_group: "O+", aadhaar: "", consent: false });
  const [reg, setReg] = useState<Reg | null>(null);
  const [otp, setOtp] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k: string, v: string | boolean) => setF((x) => ({ ...x, [k]: v }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setReg(await api<Reg>(`/api/camps/${campId}/register`, { method: "POST", body: JSON.stringify({ ...f, aadhaar: f.aadhaar.replace(/\D/g, "") }) }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault();
    if (!reg) return;
    setBusy(true);
    setError("");
    try {
      const r = await api<Reg>(`/api/camps/registrations/${reg.id}/otp`, { method: "POST", body: JSON.stringify({ otp }) });
      setReg(r);
      if (r.status !== "registered") setError(r.steps.at(-1) ?? "OTP");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sheet stack" style={{ ["--gap" as string]: "10px", gridColumn: "1 / -1" }}>
      <h3 className="h3">{t("reg_title")}: {title}</h3>
      <p className="small muted" style={{ margin: 0 }}>{t("reg_body")}</p>
      {!reg && (
        <form className="stack" style={{ ["--gap" as string]: "8px" }} onSubmit={submit}>
          <input className="input" required placeholder={t("your_name")} value={f.name} maxLength={80} onChange={(e) => set("name", e.target.value)} />
          <input className="input num" required type="tel" placeholder={t("your_phone")} value={f.phone} onChange={(e) => set("phone", e.target.value)} />
          <div className="row">
            <label className="small" style={{ flex: 1 }}>{t("reg_dob")}
              <input className="input num" required type="date" value={f.dob} onChange={(e) => set("dob", e.target.value)} /></label>
            <select className="input" style={{ flex: 1 }} aria-label={t("gender")} value={f.gender} onChange={(e) => set("gender", e.target.value)}>
              <option value="M">{t("male")}</option><option value="F">{t("female")}</option><option value="O">{t("other")}</option>
            </select>
            <select className="input" style={{ flex: 1 }} aria-label={t("f_patient_group")} value={f.blood_group} onChange={(e) => set("blood_group", e.target.value)}>
              {GROUPS.map((g) => <option key={g} value={g}>{show(g)}</option>)}
            </select>
          </div>
          <label className="small">{t("reg_aadhaar")}
            <input className="input num" required inputMode="numeric" placeholder="2345 6789 0123" value={f.aadhaar} onChange={(e) => set("aadhaar", e.target.value)} /></label>
          <label className="small row" style={{ gap: 8, flexWrap: "nowrap", alignItems: "flex-start" }}>
            <input type="checkbox" checked={f.consent} onChange={(e) => set("consent", e.target.checked)} style={{ marginTop: 5 }} />
            <span>{t("reg_consent")}</span>
          </label>
          <button className="btn btn-primary btn-sm" disabled={busy || !f.consent}>{busy ? t("reg_working") : t("reg_submit")}</button>
        </form>
      )}
      {reg && (
        <>
          <p className="small" style={{ margin: 0, fontWeight: 600 }}>{t("reg_steps")}</p>
          <ul className="log">{reg.steps.map((s, i) => <li key={i} className={i === reg.steps.length - 1 ? "now" : undefined}>{s}</li>)}</ul>
          {reg.demo_sms && reg.status === "otp_sent" && (
            <div className="note neutral small" aria-live="polite"><b>{t("reg_phone_demo")}:</b> {reg.demo_sms}</div>
          )}
          {reg.status === "otp_sent" && (
            <form className="row" onSubmit={verify}>
              <input className="input num" style={{ flex: 1 }} required inputMode="numeric" maxLength={8} placeholder={t("reg_otp")} value={otp} onChange={(e) => setOtp(e.target.value)} />
              <button className="btn btn-primary btn-sm" disabled={busy}>{t("reg_verify")}</button>
            </form>
          )}
          {reg.status === "registered" && <p className="note small" style={{ borderLeftColor: "var(--green)" }}>{t("reg_done", { ref: reg.ref ?? "" })}</p>}
          {reg.status === "failed" && <p className="note small" role="alert">{reg.error}</p>}
        </>
      )}
      {error && <p className="note small" role="alert">{error}</p>}
    </div>
  );
}
