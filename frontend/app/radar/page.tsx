"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type Component } from "@/lib/api";
import { GROUPS, show } from "@/lib/blood";
import { useLang, type Key } from "@/lib/i18n";

type Cell = {
  state: string; district: string; group: string; component: Component; synthetic: boolean; current: number;
  forecast: number[]; threshold: number; risk: number; hours_to_shortage: number | null; factors: string[];
};
type Radar = { component: Component; generated_at: string; synthetic: boolean; cells: Cell[]; at_risk: Cell[] };

/** Risk 0..1 -> burgundy tint. Text stays readable on every step. */
const shade = (r: number) => `color-mix(in srgb, var(--burgundy) ${Math.round(r * 85)}%, var(--ivory))`;

/** F1: Shortage Radar. */
export default function ShortageRadar() {
  const { t } = useLang();
  const [component, setComponent] = useState<Component>("prbc");
  const [data, setData] = useState<Radar | null>(null);
  const [error, setError] = useState("");
  const [admin, setAdmin] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    try {
      setAdmin(localStorage.getItem("rd:admin") ?? "");
    } catch {}
  }, []);
  useEffect(() => {
    setData(null);
    api<Radar>(`/api/radar?component=${component}`).then(setData).catch((e) => setError(e.message));
  }, [component]);

  const districts = useMemo(() => [...new Set((data?.cells ?? []).map((c) => c.district))].sort(), [data]);
  const byKey = useMemo(() => new Map((data?.cells ?? []).map((c) => [`${c.district}|${c.group}`, c])), [data]);

  async function drive(c: Cell) {
    setMsg("");
    try {
      await api(`/api/admin/radar/drive?district=${encodeURIComponent(c.district)}&group=${encodeURIComponent(c.group)}&component=${c.component}`,
        { method: "POST", admin });
      setMsg(t("radar_drive_done"));
    } catch (e) {
      setMsg((e as Error).message);
    }
  }

  return (
    <div className="wrap stack" style={{ paddingTop: 32, ["--gap" as string]: "18px" }}>
      <h1 className="h1">{t("nav_radar")}</h1>
      <p className="lede">{t("radar_body")}</p>
      <div className="seg" role="group" aria-label={t("f_component")} style={{ maxWidth: 360 }}>
        {(["prbc", "platelets"] as Component[]).map((c) => (
          <button key={c} aria-pressed={component === c} onClick={() => setComponent(c)}>{t(`comp_${c}` as Key)}</button>
        ))}
      </div>
      {error && <p className="note" role="alert">{error}</p>}
      {data?.synthetic && <p className="note">{t("radar_synthetic")}</p>}
      {msg && <p className="note neutral" role="status">{msg}</p>}
      {!data && !error && <p className="muted">…</p>}

      {data && (
        <>
          <h2 className="h2">{t("radar_at_risk")}</h2>
          {data.at_risk.length === 0 && <p className="muted">{t("radar_none")}</p>}
          <ul className="register">
            {data.at_risk.slice(0, 12).map((c) => (
              <li key={`${c.district}-${c.group}`}>
                <div>
                  <div className="name">{c.district}, {c.state} · {show(c.group)}</div>
                  <div className="meta num">
                    {t("radar_now", { n: c.current })} · {c.forecast.join(" → ")}
                    {c.hours_to_shortage ? ` · ${t("radar_in", { h: c.hours_to_shortage })}` : ""}
                  </div>
                </div>
                <div className="units num"><b>{Math.round(c.risk * 100)}%</b><span>{t("radar_risk")}</span></div>
                <div className="split">{c.factors.map((f) => <span key={f}>{f}</span>)}</div>
                {admin && (
                  <div className="actions"><button className="btn btn-secondary btn-sm" onClick={() => drive(c)}>{t("radar_drive")}</button></div>
                )}
              </li>
            ))}
          </ul>

          <h2 className="h2" style={{ marginTop: 28 }}>{t("radar_all")}</h2>
          <div style={{ overflowX: "auto" }}>
            <table className="matrix" style={{ minWidth: 520 }}>
              <thead>
                <tr><th className="corner" /> {GROUPS.map((g) => <th key={g} scope="col">{show(g)}</th>)}</tr>
              </thead>
              <tbody>
                {districts.map((d) => (
                  <tr key={d}>
                    <th scope="row" style={{ width: 150, fontFamily: "var(--sans)", fontSize: 14, color: "var(--ink)" }}>{d}</th>
                    {GROUPS.map((g) => {
                      const c = byKey.get(`${d}|${g}`);
                      return (
                        <td key={g} title={c ? `${Math.round(c.risk * 100)}% · ${c.factors.join(", ")}` : ""}
                          style={{ background: c ? shade(c.risk) : undefined, color: c && c.risk > 0.55 ? "var(--ivory)" : "var(--ink)", fontSize: 13 }}>
                          {c ? `${Math.round(c.risk * 100)}` : ""}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="tiny muted">{t("radar_method")}</p>
        </>
      )}
    </div>
  );
}
