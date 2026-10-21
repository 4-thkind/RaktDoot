"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, type Config } from "@/lib/api";
import { show } from "@/lib/blood";

type Stats = {
  donors: number; donors_synthetic: number; blood_banks: number; blood_banks_eraktkosh: number; requests: number; notifications: number;
  donations: number; donations_verified: number; stock_history_real: number; stock_history_synthetic: number;
  leaderboard: { name: string; group: string; verified: number; donations: number }[];
  recent: { id: string; group: string; units: number; hospital: string; kind: string; component: string; status: string; created_at: string; manage_token: string }[];
};
type Run = { id: number; kind: string; purpose: string; target: string; status: string; run_id: string | null; duration_s: number; steps: number | null; error: string | null; at: string; link: string | null };
type TinyFish = {
  mode: string; runs: Run[]; summary: { kind: string; status: string; count: number; avg_s: number }[];
  recipes: { version: number; active: boolean; success: number; fail: number; verified_ok: number; verified_mismatch: number; learned_codes: number; from_run: string | null; last_ok: string | null }[];
  unmatched_banks: { name: string; count: number; address: string }[];
};
type Arm = { variant: string; segment: string; mean: number; pulls: number; accepts: number; history: [number, number][] };
type Bandit = { enabled: boolean; real: Arm[]; simulated: Arm[]; true_rates_simulation: Record<string, number> };
type Backtest = { component: string; points: number; mae: number; naive_mae: number; precision: number; recall: number; naive_precision: number; naive_recall: number; synthetic: boolean };

const COLORS = ["#80011f", "#8a6412", "#2f6b4f", "#3b5b92", "#6c6056"];

function BanditChart({ arms, title }: { arms: Arm[]; title: string }) {
  const byVariant = new Map<string, Arm>();
  arms.forEach((a) => { const cur = byVariant.get(a.variant); if (!cur || a.pulls > cur.pulls) byVariant.set(a.variant, a); });
  const list = [...byVariant.values()];
  const maxX = Math.max(10, ...list.map((a) => a.history.at(-1)?.[0] ?? 0));
  const maxY = Math.max(0.1, ...list.flatMap((a) => a.history.map((p) => p[1])));
  const W = 520, H = 180;
  if (!list.length) return <p className="small muted">{title}: no data yet.</p>;
  return (
    <figure style={{ margin: 0 }}>
      <figcaption className="small" style={{ fontWeight: 600 }}>{title}</figcaption>
      <svg viewBox={`0 0 ${W} ${H + 20}`} role="img" aria-label={`${title}: posterior acceptance rate per wording`}>
        <line x1={0} y1={H} x2={W} y2={H} stroke="var(--rule-strong)" />
        {list.map((a, i) => (
          <polyline key={a.variant} fill="none" stroke={COLORS[i % COLORS.length]} strokeWidth={2}
            points={a.history.map(([x, y]) => `${(x / maxX) * W},${H - (y / maxY) * (H - 10)}`).join(" ")} />
        ))}
        <text x={2} y={H + 16} fontSize={11} fill="var(--muted)">outcomes recorded per wording (accepted, declined or unanswered)</text>
      </svg>
      <div className="plate-caption" style={{ justifyContent: "flex-start" }}>
        {list.map((a, i) => (
          <span key={a.variant}><i style={{ background: COLORS[i % COLORS.length] }} />{a.variant}: {(a.mean * 100).toFixed(1)}% ({a.pulls})</span>
        ))}
      </div>
    </figure>
  );
}

export default function Admin() {
  const [token, setToken] = useState("");
  const [cfg, setCfg] = useState<Config | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [tf, setTf] = useState<TinyFish | null>(null);
  const [bandit, setBandit] = useState<Bandit | null>(null);
  const [bt, setBt] = useState<Backtest[]>([]);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    try {
      setToken(localStorage.getItem("rd:admin") ?? "");
    } catch {}
    api<Config>("/api/config").then(setCfg).catch((e) => setMsg(e.message));
  }, []);

  const load = useCallback(async (tok = token) => {
    try {
      const [s, t, b] = await Promise.all([
        api<Stats>("/api/admin/stats", { admin: tok }), api<TinyFish>("/api/admin/tinyfish", { admin: tok }), api<Bandit>("/api/admin/bandit", { admin: tok }),
      ]);
      setStats(s); setTf(t); setBandit(b);
      setMsg("");
    } catch (e) {
      setMsg((e as Error).message);
    }
  }, [token]);

  async function run(path: string, label: string, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) return;
    setBusy(label);
    try {
      const res = await api<Record<string, unknown>>(path, { method: "POST", admin: token });
      setMsg(`${label}: ${JSON.stringify(res).slice(0, 400)}`);
      load();
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  async function backtest() {
    setBusy("Backtest");
    try {
      setBt(await Promise.all(["prbc", "platelets"].map((c) => api<Backtest>(`/api/admin/radar/backtest?component=${c}`, { admin: token }))));
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy("");
    }
  }

  const btn = (path: string, label: string, confirmText?: string, cls = "btn-quiet") => (
    <button className={`btn ${cls} btn-sm`} disabled={!!busy} onClick={() => run(path, label, confirmText)}>{busy === label ? "Working…" : label}</button>
  );

  return (
    <div className="wrap" style={{ paddingTop: 32, maxWidth: 1000 }}>
      <h1 className="h1">Team controls</h1>
      <p className="muted small">For the demo only. Needs the ADMIN_TOKEN set on the backend.</p>
      {cfg && (
        <p className="sheet small" style={{ marginTop: 16 }}>
          WhatsApp: <b>{cfg.whatsapp_mode}</b> · TinyFish: <b>{cfg.tinyfish_mode === "live" ? `live (proxy ${cfg.proxy_country || "off"}, replay ${cfg.replay ? "on" : "off"})` : "sample data"}</b> ·
          LLM: <b>{cfg.llm}</b> · Vision: <b>{cfg.vision}</b> · Speech: <b>{cfg.stt}</b> · Dispatcher: <b>{cfg.dispatch_agent}</b> ·
          Bandit: <b>{cfg.bandit ? "on" : "off"}</b> · Intel sklearnex: <b>{cfg.intel_sklearn ? "on" : "off"}</b> · Radii {cfg.radii_km.join(", ")} km ·
          Quiet hours {cfg.quiet_hours ? "on" : "off"}
        </p>
      )}
      <form className="row" style={{ marginTop: 16 }} onSubmit={(e) => { e.preventDefault(); try { localStorage.setItem("rd:admin", token); } catch {} load(); }}>
        <input className="input" style={{ flex: 1 }} type="password" placeholder="Admin token" value={token} onChange={(e) => setToken(e.target.value)} />
        <button className="btn btn-primary" type="submit">Load</button>
      </form>
      {msg && <p className="note" style={{ marginTop: 14, wordBreak: "break-word" }} role="status">{msg}</p>}

      {stats && (
        <>
          <div className="funnel num" style={{ gridTemplateColumns: "repeat(5, 1fr)" }}>
            <div><b>{stats.donors}</b><span>donors ({stats.donors_synthetic} synthetic)</span></div>
            <div><b>{stats.blood_banks}</b><span>blood centres ({stats.blood_banks_eraktkosh} from eRaktKosh)</span></div>
            <div><b>{stats.requests}</b><span>requests</span></div>
            <div><b>{stats.notifications}</b><span>alerts sent</span></div>
            <div><b>{stats.donations_verified}/{stats.donations}</b><span>donations photo-verified</span></div>
          </div>

          <h2 className="h2" style={{ marginTop: 28 }}>Scheduler</h2>
          <div className="row" style={{ marginTop: 10 }}>
            {btn("/api/admin/tick", "Run scheduler now")}
            {btn("/api/admin/tick?advance_hours=3", "Pretend 3 h passed")}
            {btn("/api/admin/tick?advance_hours=25", "Pretend 25 h passed")}
            {btn("/api/admin/reset", "Reset and re-seed", "Delete everything and re-seed 200 synthetic donors?", "btn-secondary")}
          </div>

          <h2 className="h2" style={{ marginTop: 28 }}>TinyFish: Sense, Verify, Act, Learn</h2>
          <div className="row" style={{ marginTop: 10 }}>
            {btn("/api/admin/tinyfish/sweep", "Sweep NCR stock (batch)")}
            {btn("/api/admin/tinyfish/monitors", "Create monitors")}
            {btn("/api/admin/directory/refresh", "Refresh directory (Fetch)")}
            {btn("/api/admin/camps/refresh", "Refresh camps (Fetch)")}
            {btn("/api/admin/guide/rebuild", "Rebuild guide sources (Fetch)")}
          </div>
          {tf && (
            <>
              <p className="small muted" style={{ marginTop: 10 }}>
                Mode: <b>{tf.mode}</b>. {tf.summary.map((s) => `${s.kind} ${s.status}: ${s.count} (avg ${s.avg_s} s)`).join(" · ") || "No TinyFish calls yet."}
              </p>
              {tf.recipes.length > 0 && (
                <p className="small">Replay recipes: {tf.recipes.map((r) => `v${r.version}${r.active ? " (active)" : ""} ${r.success} ok / ${r.fail} failed, verified ${r.verified_ok}/${r.verified_ok + r.verified_mismatch}, ${r.learned_codes} learned codes${r.from_run ? `, healed from ${r.from_run.slice(0, 10)}` : ""}`).join("; ")}</p>
              )}
              <div style={{ overflowX: "auto" }}>
                <table className="matrix" style={{ fontSize: 13, marginTop: 8 }}>
                  <thead><tr>{["when", "kind", "purpose", "target", "status", "time", "steps", "run"].map((h) => <th key={h} style={{ fontSize: 13, padding: "0 6px" }}>{h}</th>)}</tr></thead>
                  <tbody>
                    {tf.runs.map((r) => (
                      <tr key={r.id}>
                        <td style={{ padding: "0 6px" }}>{new Date(r.at).toLocaleTimeString()}</td><td>{r.kind}</td><td>{r.purpose}</td>
                        <td style={{ textAlign: "left", padding: "0 6px" }}>{r.target}</td><td title={r.error ?? ""}>{r.status}</td><td>{r.duration_s} s</td><td>{r.steps ?? ""}</td>
                        <td>{r.link ? <a href={r.link} target="_blank" rel="noreferrer">{r.run_id?.slice(0, 8)}</a> : r.run_id?.slice(0, 12) ?? ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {tf.unmatched_banks.length > 0 && (
                <details className="small" style={{ marginTop: 8 }}><summary>{tf.unmatched_banks.length} eRaktKosh banks not matched to the directory</summary>
                  <ul>{tf.unmatched_banks.map((u) => <li key={u.name}>{u.name} ({u.count}×) {u.address}</li>)}</ul>
                </details>
              )}
            </>
          )}

          <h2 className="h2" style={{ marginTop: 28 }}>Shortage radar</h2>
          <div className="row" style={{ marginTop: 10 }}>
            <Link className="btn btn-quiet btn-sm" href="/radar">Open radar (drive buttons appear with your token)</Link>
            <button className="btn btn-quiet btn-sm" disabled={!!busy} onClick={backtest}>{busy === "Backtest" ? "Working…" : "Run backtest"}</button>
          </div>
          {bt.length > 0 && (
            <p className="small">{bt.map((b) => `${b.component}: MAE ${b.mae} vs naive ${b.naive_mae}; shortage precision ${b.precision} / recall ${b.recall} (naive ${b.naive_precision}/${b.naive_recall}) over ${b.points} forecasts${b.synthetic ? " (synthetic history)" : ""}`).join(". ")}</p>
          )}

          <h2 className="h2" style={{ marginTop: 28 }}>Alert wording (bandit)</h2>
          <div className="row" style={{ marginTop: 10 }}>{btn("/api/admin/bandit/simulate?n=600", "Simulate 600 donors (labelled simulation)")}</div>
          {bandit && (
            <div style={{ display: "grid", gap: 20, gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", marginTop: 12 }}>
              <BanditChart arms={bandit.real} title="Real alerts" />
              <BanditChart arms={bandit.simulated} title={`Simulation (hidden true rates: ${Object.entries(bandit.true_rates_simulation).map(([k, v]) => `${k} ${v}`).join(", ")})`} />
            </div>
          )}

          {stats.leaderboard.length > 0 && (
            <>
              <h2 className="h2" style={{ marginTop: 28 }}>Donor leaderboard</h2>
              <ol className="small">{stats.leaderboard.map((d, i) => <li key={i}>{d.name} ({show(d.group)}): {d.donations} donations, {d.verified} photo-verified</li>)}</ol>
            </>
          )}

          <p className="small muted">Stock history: {stats.stock_history_real} real rows, {stats.stock_history_synthetic} synthetic rows.</p>

          <h2 className="h2" style={{ marginTop: 28 }}>Recent requests</h2>
          <ul className="choices" style={{ marginTop: 12 }}>
            {stats.recent.map((r) => (
              <li key={r.id}>
                <Link href={`/request/${r.id}?t=${encodeURIComponent(r.manage_token)}`} style={{ display: "grid", gridTemplateColumns: "1fr auto", padding: "12px 4px", textDecoration: "none", color: "inherit" }}>
                  <span className="t">{show(r.group)} {r.component}, {r.units} unit{r.units > 1 ? "s" : ""}, {r.hospital}{r.kind !== "emergency" ? ` (${r.kind})` : ""}</span>
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
