"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Config } from "@/lib/api";
import { show } from "@/lib/blood";

type Stats = {
  donors: number; donors_synthetic: number; blood_banks: number; requests: number; notifications: number; donations: number;
  recent: { id: string; group: string; units: number; hospital: string; status: string; created_at: string; manage_token: string }[];
};

export default function Admin() {
  const [token, setToken] = useState("");
  const [cfg, setCfg] = useState<Config | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    try {
      setToken(localStorage.getItem("rd:admin") ?? "");
    } catch {}
    api<Config>("/api/config").then(setCfg).catch((e) => setMsg(e.message));
  }, []);

  async function load(tok = token) {
    try {
      setStats(await api<Stats>("/api/admin/stats", { admin: tok }));
      setMsg("");
    } catch (e) {
      setMsg((e as Error).message);
    }
  }

  async function run(path: string, label: string, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) return;
    try {
      const res = await api<Record<string, number>>(path, { method: "POST", admin: token });
      setMsg(`${label}: ${Object.entries(res).map(([k, v]) => `${k} ${v}`).join(", ")}`);
      load();
    } catch (e) {
      setMsg((e as Error).message);
    }
  }

  return (
    <div className="narrow" style={{ paddingTop: 32, maxWidth: 760 }}>
      <h1 className="h1">Team controls</h1>
      <p className="muted small">For the demo only. Needs the ADMIN_TOKEN set on the backend.</p>
      {cfg && (
        <p className="sheet small" style={{ marginTop: 16 }}>
          WhatsApp channel: <b>{cfg.whatsapp_mode}</b>. eRaktKosh lookup: <b>{cfg.tinyfish_mode === "live" ? "live (TinyFish)" : "sample data"}</b>.
          Component searched: {cfg.component}. Wave radii: {cfg.radii_km.join(", ")} km. Quiet hours: {cfg.quiet_hours ? "respected (11 pm to 7 am)" : "off"}.
        </p>
      )}
      <form className="row" style={{ marginTop: 16 }} onSubmit={(e) => { e.preventDefault(); try { localStorage.setItem("rd:admin", token); } catch {} load(); }}>
        <input className="input" style={{ flex: 1 }} type="password" placeholder="Admin token" value={token} onChange={(e) => setToken(e.target.value)} />
        <button className="btn btn-primary" type="submit">Load</button>
      </form>
      {msg && <p className="note" style={{ marginTop: 14 }} role="status">{msg}</p>}

      {stats && (
        <>
          <div className="funnel num" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
            <div><b>{stats.donors}</b><span>donors ({stats.donors_synthetic} synthetic)</span></div>
            <div><b>{stats.requests}</b><span>requests</span></div>
            <div><b>{stats.notifications}</b><span>alerts sent</span></div>
          </div>
          <div className="stack" style={{ marginTop: 20 }}>
            <button className="btn btn-quiet btn-block" onClick={() => run("/api/admin/tick", "Scheduler ran")}>Run scheduler now</button>
            <button className="btn btn-quiet btn-block" onClick={() => run("/api/admin/tick?advance_hours=3", "Pretended 3 hours passed")}>Pretend 3 hours passed (on-the-way check)</button>
            <button className="btn btn-quiet btn-block" onClick={() => run("/api/admin/tick?advance_hours=25", "Pretended 25 hours passed")}>Pretend 25 hours passed (did you donate?)</button>
            <button className="btn btn-secondary btn-block" onClick={() => run("/api/admin/reset", "Reset", "Delete everything and re-seed 200 synthetic donors?")}>Reset database and re-seed</button>
          </div>
          <h2 className="h2" style={{ marginTop: 32 }}>Recent requests</h2>
          <ul className="choices" style={{ marginTop: 12 }}>
            {stats.recent.map((r) => (
              <li key={r.id}>
                <Link href={`/request/${r.id}?t=${encodeURIComponent(r.manage_token)}`} style={{ display: "grid", gridTemplateColumns: "1fr auto", padding: "12px 4px", textDecoration: "none", color: "inherit" }}>
                  <span className="t">{show(r.group)}, {r.units} unit{r.units > 1 ? "s" : ""}, {r.hospital}</span>
                  <span className="d">{r.status}</span>
                  <span className="s num">{new Date(r.created_at).toLocaleString()}</span>
                </Link>
              </li>
            ))}
          </ul>
          <p className="small" style={{ marginTop: 20 }}><Link href="/simulator">Open the WhatsApp simulator</Link></p>
        </>
      )}
    </div>
  );
}
