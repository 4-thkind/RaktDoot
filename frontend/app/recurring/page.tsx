"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, type Component, type Group, type Place } from "@/lib/api";
import { GROUPS, show } from "@/lib/blood";
import { useLang, type Key } from "@/lib/i18n";

type Slot = { id: string; date: string; status: string; donor: string | null; donor_group: string | null };
type Rota = { id: string; patient_label: string; group: Group; component: Component; units: number; interval_days: number; next_due: string;
  hospital: string; synthetic: boolean; slots: Slot[]; manage_token?: string };

export default function Page() {
  return (
    <Suspense fallback={null}>
      <Recurring />
    </Suspense>
  );
}

function Schedule({ rota }: { rota: Rota }) {
  const { t, lang } = useLang();
  const byDate = new Map<string, Slot[]>();
  rota.slots.forEach((s) => byDate.set(s.date, [...(byDate.get(s.date) ?? []), s]));
  return (
    <section className="sheet">
      <h2 className="h3">
        {rota.patient_label} · {show(rota.group)} {t(`comp_${rota.component}` as Key).toLowerCase()} · {rota.units} unit(s) / {rota.interval_days} d · {rota.hospital}
      </h2>
      <ul className="register" style={{ marginTop: 12 }}>
        {[...byDate.entries()].slice(0, 10).map(([d, slots]) => (
          <li key={d} style={{ gridTemplateColumns: "120px 1fr" }}>
            <div className="num" style={{ fontWeight: 600 }}>{new Date(d).toLocaleDateString(`${lang}-IN`, { day: "numeric", month: "short", year: "numeric" })}</div>
            <div className="split" style={{ gridColumn: "auto" }}>
              {slots.map((s) => (
                <span key={s.id} className={`badge ${s.status === "confirmed" ? "good" : s.status === "unfilled" || s.status === "declined" ? "" : "on"}`}>
                  {s.donor ? `${s.donor} (${show(s.donor_group ?? "")})` : "—"} · {t(`rec_s_${s.status}` as Key)}
                </span>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Recurring() {
  const { t } = useLang();
  const params = useSearchParams();
  const [demo, setDemo] = useState<Rota | null>(null);
  const [mine, setMine] = useState<Rota | null>(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ patient_label: "", patient_group: "B+" as Group, component: "prbc" as Component, units: 1, interval_days: 21,
    next_due: new Date(Date.now() + 3 * 864e5).toISOString().slice(0, 10), requester_name: "", requester_phone: "" });
  const [hospital, setHospital] = useState<Place | null>(null);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Place[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Rota>("/api/recurring/demo").then(setDemo).catch(() => setDemo(null));
    const id = params.get("id"), tok = params.get("t");
    if (id && tok) api<Rota>(`/api/recurring/${id}?t=${encodeURIComponent(tok)}`).then(setMine).catch((e) => setError(e.message));
  }, [params]);

  useEffect(() => {
    if (q.trim().length < 2) return setHits([]);
    const h = setTimeout(() => api<Place[]>(`/api/places/search?q=${encodeURIComponent(q)}`).then(setHits).catch(() => setHits([])), 350);
    return () => clearTimeout(h);
  }, [q]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!hospital) return setError(t("err_hospital"));
    setBusy(true);
    setError("");
    try {
      const r = await api<Rota>("/api/recurring", { method: "POST", body: JSON.stringify({
        ...form, hospital_name: hospital.name, hospital_lat: hospital.lat, hospital_lng: hospital.lng }) });
      setMine(r);
      window.history.replaceState(null, "", `/recurring?id=${r.id}&t=${encodeURIComponent(r.manage_token ?? "")}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const set = (k: string, v: string | number) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <div className="narrow stack" style={{ paddingTop: 32, ["--gap" as string]: "18px", maxWidth: 760 }}>
      <h1 className="h1">{t("rec_title")}</h1>
      <p className="lede">{t("rec_body")}</p>
      {error && <p className="note" role="alert">{error}</p>}
      {mine && (
        <>
          <p className="note neutral small">{t("rec_saved")} <span className="num" style={{ wordBreak: "break-all" }}>{typeof window !== "undefined" ? window.location.href : ""}</span></p>
          <Schedule rota={mine} />
        </>
      )}
      {demo && !mine && (
        <>
          <h2 className="h2">{t("rec_demo")}</h2>
          <Schedule rota={demo} />
        </>
      )}

      <h2 className="h2" style={{ marginTop: 24 }}>{t("rec_form")}</h2>
      <form className="stack" onSubmit={submit}>
        <label className="field"><span className="label">{t("rec_label")}</span>
          <input className="input" required maxLength={80} value={form.patient_label} onChange={(e) => set("patient_label", e.target.value)} /></label>
        <div className="row">
          <label className="field" style={{ flex: 1 }}><span className="label">{t("f_patient_group")}</span>
            <select className="input" value={form.patient_group} onChange={(e) => set("patient_group", e.target.value)}>
              {GROUPS.map((g) => <option key={g} value={g}>{show(g)}</option>)}
            </select></label>
          <label className="field" style={{ flex: 1 }}><span className="label">{t("f_component")}</span>
            <select className="input" value={form.component} onChange={(e) => set("component", e.target.value)}>
              {(["prbc", "whole_blood", "platelets", "plasma"] as Component[]).map((c) => <option key={c} value={c}>{t(`comp_${c}` as Key)}</option>)}
            </select></label>
        </div>
        <div className="row">
          <label className="field" style={{ flex: 1 }}><span className="label">{t("f_units")}</span>
            <input className="input num" type="number" min={1} max={4} value={form.units} onChange={(e) => set("units", Number(e.target.value))} /></label>
          <label className="field" style={{ flex: 1 }}><span className="label">{t("rec_interval")}</span>
            <input className="input num" type="number" min={7} max={60} value={form.interval_days} onChange={(e) => set("interval_days", Number(e.target.value))} /></label>
          <label className="field" style={{ flex: 1 }}><span className="label">{t("rec_next")}</span>
            <input className="input num" type="date" value={form.next_due} onChange={(e) => set("next_due", e.target.value)} /></label>
        </div>
        <div className="field"><span className="label">{t("hospital")}</span>
          {hospital ? (
            <div className="row"><b>{hospital.name}</b><button type="button" className="linkbtn small" onClick={() => setHospital(null)}>{t("change")}</button></div>
          ) : (
            <>
              <input className="input" type="search" value={q} placeholder={t("search_ph")} onChange={(e) => setQ(e.target.value)} />
              <ul className="choices">{hits.map((p, i) => (
                <li key={`${p.name}-${i}`}><button type="button" onClick={() => setHospital(p)}><span className="t">{p.name}</span><span className="s">{p.address}</span></button></li>
              ))}</ul>
            </>
          )}
        </div>
        <label className="field"><span className="label">{t("your_name")}</span>
          <input className="input" required maxLength={80} value={form.requester_name} onChange={(e) => set("requester_name", e.target.value)} /></label>
        <label className="field"><span className="label">{t("your_phone")}</span>
          <input className="input num" type="tel" required value={form.requester_phone} onChange={(e) => set("requester_phone", e.target.value)} /></label>
        <button className="btn btn-primary btn-block" disabled={busy}>{t("rec_submit")}</button>
      </form>
    </div>
  );
}
