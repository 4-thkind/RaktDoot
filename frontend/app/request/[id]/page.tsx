"use client";

import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { DispatchPlate } from "@/components/ProximityPlate";
import { API_BASE, api, type Snapshot } from "@/lib/api";
import { formatPhone, mapLink, show, telLink, waLink } from "@/lib/blood";
import { useAgo, useLang } from "@/lib/i18n";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <Dashboard />
    </Suspense>
  );
}

function useToken(id: string) {
  const params = useSearchParams();
  const [token, setToken] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    const fromUrl = params.get("t");
    if (fromUrl) {
      setToken(fromUrl);
      try {
        localStorage.setItem(`rd:req:${id}`, fromUrl);
      } catch {}
      return;
    }
    try {
      setToken(localStorage.getItem(`rd:req:${id}`));
    } catch {
      setToken(null);
    }
  }, [id, params]);
  return token;
}

function Dashboard() {
  const { id } = useParams<{ id: string }>();
  const { t } = useLang();
  const ago = useAgo();
  const token = useToken(id);
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [, tick] = useState(0);

  useEffect(() => {
    if (!token) return;
    let es: EventSource | null = null;
    let retry: ReturnType<typeof setTimeout>;
    const open = () => {
      es = new EventSource(`${API_BASE}/api/requests/${id}/events?t=${encodeURIComponent(token)}`);
      es.onmessage = (ev) => {
        setSnap(JSON.parse(ev.data));
        setError("");
      };
      es.onerror = () => {
        es?.close();
        // fall back to one fetch (also surfaces a bad link), then reconnect
        api<Snapshot>(`/api/requests/${id}?t=${encodeURIComponent(token)}`).then(setSnap).catch((e) => setError(e.message));
        retry = setTimeout(open, 4000);
      };
    };
    open();
    const timer = setInterval(() => tick((n) => n + 1), 20000);
    return () => {
      es?.close();
      clearTimeout(retry);
      clearInterval(timer);
    };
  }, [id, token]);

  async function act(path: string, confirmText?: string) {
    if (!token || (confirmText && !window.confirm(confirmText))) return;
    setBusy(true);
    try {
      setSnap(await api<Snapshot>(`/api/requests/${id}/${path}?t=${encodeURIComponent(token)}`, { method: "POST" }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function shareLink() {
    if (!snap) return;
    const data = { title: "Blood needed", text: snap.preview, url: snap.share_url };
    if (navigator.share) {
      try {
        await navigator.share(data);
        return;
      } catch {}
    }
    try {
      await navigator.clipboard.writeText(snap.share_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {}
  }

  if (token === null) return <div className="narrow" style={{ paddingTop: 32 }}><p className="note">{t("link_missing")}</p></div>;
  if (error && !snap) return <div className="narrow" style={{ paddingTop: 32 }}><p className="note" role="alert">{error}</p></div>;
  if (!snap) return <div className="narrow" style={{ paddingTop: 32 }}><p className="muted">{t("keep_page")}</p></div>;

  const open = ["dispatching", "matched", "needs_public_share", "open"].includes(snap.status);
  const connected = snap.funnel.connected;
  const expiresSoon = snap.expires_at && new Date(snap.expires_at).getTime() - Date.now() < 6 * 3600 * 1000;
  const nextWave = snap.next_wave_at && snap.status === "dispatching"
    ? new Date(snap.next_wave_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : null;
  const firstDonor = snap.seconds_to_first_donor !== null
    ? snap.seconds_to_first_donor < 60 ? `${Math.round(snap.seconds_to_first_donor)} s` : `${Math.round(snap.seconds_to_first_donor / 60)} min` : null;

  return (
    <div className="narrow">
      <div className="status-head">
        <p className="kicker" style={{ margin: 0 }}>
          {show(snap.patient_group)}, {snap.units} unit{snap.units > 1 ? "s" : ""}, {snap.hospital.name}
        </p>
        <h1 className="h1" style={{ marginTop: 6 }} aria-live="polite">{t(`st_${snap.status}` as "st_open")}</h1>
        {open && <p className="muted" style={{ margin: "6px 0 0" }}>{t("connected_of", { n: connected, target: snap.target })}</p>}
        {firstDonor && <p className="small muted" style={{ margin: "4px 0 0" }}>{t("first_donor", { t: firstDonor })}</p>}
      </div>

      <div className="funnel num" role="list">
        {(["notified", "delivered", "read", "responded", "connected"] as const).map((k) => (
          <div key={k} role="listitem"><b>{snap.funnel[k]}</b><span>{t(`f_${k}`)}</span></div>
        ))}
      </div>

      {error && <p className="note" role="alert" style={{ marginTop: 16 }}>{error}</p>}

      {snap.status === "needs_public_share" && (
        <div className="pivot" style={{ marginTop: 20 }}>
          <p style={{ margin: "0 0 12px" }}>{t("public_share_body")}</p>
          <button className="btn btn-primary btn-block" onClick={shareLink}>{t("share")}</button>
        </div>
      )}

      <section style={{ marginTop: 28 }}>
        <h2 className="h2">{t("donors_title")}</h2>
        {snap.donors.length === 0 ? (
          <p className="muted">{open ? t("donors_empty") : ""}</p>
        ) : (
          <ul className="donor-list" style={{ marginTop: 14 }}>
            {snap.donors.map((d) => (
              <li key={d.id} className={d.status === "connected" ? "live" : undefined}>
                <div>
                  <div style={{ fontWeight: 600 }}>{d.name}</div>
                  <div className="small muted num">
                    {d.distance_km} {t("km")}
                    {d.eta_minutes ? `, ${t("eta", { m: d.eta_minutes })}` : ""}
                    {d.since ? `, ${ago(d.since)}` : ""}
                  </div>
                  <span className={`badge ${d.status === "connected" ? "on" : d.status === "donated" ? "good" : ""}`} style={{ marginTop: 6 }}>
                    {t(`ds_${d.status}` as "ds_accepted")}
                  </span>
                </div>
                <div className="grp">{show(d.group)}</div>
                {d.phone && (
                  <div className="actions">
                    <a className="btn btn-primary btn-sm" href={telLink(d.phone)}>{t("call")}</a>
                    <a className="btn btn-secondary btn-sm" href={waLink(d.phone)} target="_blank" rel="noreferrer">{t("whatsapp")}</a>
                  </div>
                )}
                {d.phone && <div className="tiny muted num" style={{ gridColumn: "1 / -1" }}>{formatPhone(d.phone)}</div>}
              </li>
            ))}
          </ul>
        )}
      </section>

      {snap.wave > 0 && (
        <section style={{ marginTop: 32 }}>
          <h2 className="h2">{t("rings_title")}</h2>
          <DispatchPlate rings={snap.rings} reachedKm={snap.radius_km} label={`Donors messaged within ${snap.radius_km} km of the hospital`} />
          {nextWave && <p className="small muted" style={{ textAlign: "center" }}>{t("next_wave", { time: nextWave })}</p>}
        </section>
      )}

      <section className="stack" style={{ marginTop: 28, ["--gap" as string]: "10px" }}>
        <div className="row">
          <button className="btn btn-quiet" style={{ flex: 1 }} onClick={shareLink}>{copied ? t("copied") : t("share")}</button>
          <a className="btn btn-quiet" style={{ flex: 1 }} href={`https://wa.me/?text=${encodeURIComponent(snap.preview)}`} target="_blank" rel="noreferrer">{t("share_wa")}</a>
        </div>
        <p className="tiny muted" style={{ margin: 0 }}>{t("share_note")}</p>
        {open && (
          <>
            {(snap.status === "dispatching" || snap.status === "needs_public_share") && (
              <button className="btn btn-secondary btn-block" disabled={busy} onClick={() => act("widen")}>{t("widen")}</button>
            )}
            {expiresSoon && <button className="btn btn-secondary btn-block" disabled={busy} onClick={() => act("extend")}>{t("extend")}</button>}
            <button className="btn btn-primary btn-block" disabled={busy} onClick={() => act("fulfil", t("fulfil_confirm"))}>{t("fulfil")}</button>
            <button className="linkbtn small" style={{ alignSelf: "flex-start" }} disabled={busy} onClick={() => act("cancel", t("cancel_confirm"))}>{t("cancel_req")}</button>
          </>
        )}
        <p className="small" style={{ margin: "8px 0 0" }}>
          <a href={mapLink(snap.hospital.lat, snap.hospital.lng)} target="_blank" rel="noreferrer">{snap.hospital.name}</a>
        </p>
        {open && <p className="tiny muted" style={{ margin: 0 }}>{t("keep_page")}</p>}
      </section>
    </div>
  );
}
