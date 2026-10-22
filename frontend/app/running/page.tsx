"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { show } from "@/lib/blood";

type Running = { id: string; group: string; units: number; component: string; hospital: string; kind: string; status: string; created_at: string; expires_at: string | null };

export default function RunningRequests() {
  const [token, setToken] = useState("");
  const [rows, setRows] = useState<Running[] | null>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async (tok: string) => {
    try {
      setRows(await api<Running[]>("/api/admin/requests/running", { admin: tok }));
    } catch (e) {
      setRows(null);
      setMsg((e as Error).message);
    }
  }, []);

  useEffect(() => {
    let tok = "";
    try { tok = localStorage.getItem("rd:admin") ?? ""; } catch {}
    setToken(tok);
    if (tok) load(tok);
  }, [load]);

  async function stop(rid?: string) {
    if (!window.confirm(rid ? "Stop this request? Donors still being asked get a 'no longer needed' message." : "Stop ALL running requests?")) return;
    setBusy(rid ?? "all");
    try {
      const r = await api<{ stopped: number }>(`/api/admin/requests/stop${rid ? `?rid=${encodeURIComponent(rid)}` : ""}`, { method: "POST", admin: token });
      setMsg(`Stopped ${r.stopped} request${r.stopped === 1 ? "" : "s"}.`);
      await load(token);
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="wrap" style={{ paddingTop: 24, paddingBottom: 40 }}>
      <h1 className="h1">Running requests</h1>
      <p className="muted small">Every blood request still alerting donors. Stop the ones you forgot to close. Needs the admin token.</p>
      <form className="row" style={{ marginTop: 16 }} onSubmit={(e) => { e.preventDefault(); try { localStorage.setItem("rd:admin", token); } catch {} setMsg(""); load(token); }}>
        <input className="input" style={{ flex: 1 }} type="password" placeholder="Admin token" value={token} onChange={(e) => setToken(e.target.value)} />
        <button className="btn btn-primary" type="submit">Load</button>
      </form>
      {msg && <p className="note" style={{ marginTop: 14 }} role="status">{msg}</p>}

      {rows && (
        <>
          <div className="row" style={{ marginTop: 20, justifyContent: "space-between", alignItems: "center" }}>
            <b>{rows.length} running</b>
            {rows.length > 0 && <button className="btn btn-primary btn-sm" disabled={!!busy} onClick={() => stop()}>{busy === "all" ? "Stopping..." : "Stop all"}</button>}
          </div>
          {rows.length === 0 && <p className="muted" style={{ marginTop: 12 }}>Nothing is running.</p>}
          <ul style={{ listStyle: "none", padding: 0, margin: "12px 0 0" }}>
            {rows.map((r) => (
              <li key={r.id} className="sheet" style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", marginTop: 10 }}>
                <div>
                  <b>{show(r.group)}</b> · {r.units} unit{r.units === 1 ? "" : "s"} · {r.component} · {r.hospital}
                  <div className="muted small">{r.kind} · {r.status} · started {new Date(r.created_at).toLocaleString()}{r.expires_at ? ` · expires ${new Date(r.expires_at).toLocaleString()}` : ""}</div>
                </div>
                <button className="btn btn-secondary btn-sm" disabled={!!busy} onClick={() => stop(r.id)}>{busy === r.id ? "Stopping..." : "Stop"}</button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
