"use client";

import { useEffect, useState } from "react";
import { API_BASE, api } from "@/lib/api";
import { CampRegister } from "@/components/CampRegister";
import { mapLink } from "@/lib/blood";
import { useLang } from "@/lib/i18n";

type Camp = { id: string; date: string; time: string; title: string; address: string; district: string; organiser: string;
  register_url: string | null; lat: number | null; lng: number | null; sample: boolean; distance_km: number | null };
type Site = { name: string; lat: number; lng: number; type: string; score: number; donor_pool: number; at_risk: string[]; unmet: number;
  nearest_camp_km: number | null; reason: string };
type Placement = { sites: Site[]; synthetic_inputs: boolean; kmeans: { engine: string; ms: number }; candidates: number };

// Delhi NCR frame for the little map (lat/lng -> svg)
const BOX = { minLat: 28.35, maxLat: 28.8, minLng: 76.95, maxLng: 77.55 };
const W = 420, H = 320;
const xy = (lat: number, lng: number) => [((lng - BOX.minLng) / (BOX.maxLng - BOX.minLng)) * W, H - ((lat - BOX.minLat) / (BOX.maxLat - BOX.minLat)) * H];

/** A1 upcoming camps and F10 camp placement. */
export default function Camps() {
  const { t, lang } = useLang();
  const [camps, setCamps] = useState<Camp[] | null>(null);
  const [place, setPlace] = useState<Placement | null>(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    api<{ camps: Camp[] }>("/api/camps").then((r) => setCamps(r.camps)).catch((e) => setError(e.message));
    api<Placement>("/api/camps/placement?k=5").then(setPlace).catch((e) => setError(e.message));
  }, []);

  const fmt = (d: string) => new Date(d).toLocaleDateString(`${lang}-IN`, { weekday: "short", day: "numeric", month: "short" });

  return (
    <div className="wrap stack" style={{ paddingTop: 32, ["--gap" as string]: "18px" }}>
      <h1 className="h1">{t("camps_title")}</h1>
      {error && <p className="note" role="alert">{error}</p>}
      {camps?.some((c) => c.sample) && <p className="note">{t("camps_sample")}</p>}
      {camps && camps.length === 0 && <p className="muted">{t("camps_none")}</p>}
      <ul className="register">
        {(camps ?? []).slice(0, 10).map((c) => (
          <li key={c.id}>
            <div>
              <div className="name">{c.title}</div>
              <div className="meta">{c.address}{c.organiser ? ` · ${c.organiser}` : ""}</div>
            </div>
            <div className="units"><b style={{ fontSize: 22 }}>{fmt(c.date)}</b><span>{c.time}</span></div>
            <div className="actions">
              <button className="btn btn-secondary btn-sm" onClick={() => setOpen(open === c.id ? null : c.id)}>{t("camps_register")}</button>
              {c.lat !== null && c.lng !== null && <a className="btn btn-quiet btn-sm" href={mapLink(c.lat, c.lng)} target="_blank" rel="noreferrer">{t("directions")}</a>}
            </div>
            {open === c.id && <CampRegister campId={c.id} title={c.title} />}
          </li>
        ))}
      </ul>
      <p className="tiny muted">{t("camps_register_note")}</p>

      <h2 className="h2" style={{ marginTop: 28 }}>{t("place_title")}</h2>
      <p className="muted" style={{ margin: "6px 0 0" }}>{t("place_body")}</p>
      {place?.synthetic_inputs && <p className="note small">{t("radar_synthetic")}</p>}
      {place && (
        <div style={{ display: "grid", gap: 20, gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", alignItems: "start" }}>
          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Recommended camp sites in Delhi NCR" style={{ background: "#fffef8", border: "1px solid var(--rule)", borderRadius: 6 }}>
            {[...Array(7)].map((_, i) => <line key={i} x1={(i * W) / 6} x2={(i * W) / 6} y1={0} y2={H} stroke="var(--rule)" />)}
            {[...Array(5)].map((_, i) => <line key={i} y1={(i * H) / 4} y2={(i * H) / 4} x1={0} x2={W} stroke="var(--rule)" />)}
            {(camps ?? []).filter((c) => c.lat !== null).map((c) => {
              const [x, y] = xy(c.lat as number, c.lng as number);
              return <rect key={c.id} x={x - 3} y={y - 3} width={6} height={6} fill="none" stroke="var(--muted)"><title>{c.title}</title></rect>;
            })}
            {place.sites.map((s, i) => {
              const [x, y] = xy(s.lat, s.lng);
              return (
                <g key={s.name}>
                  <title>{s.name}: {s.reason}</title>
                  <circle cx={x} cy={y} r={11} fill="var(--burgundy)" />
                  <text x={x} y={y + 4} textAnchor="middle" fontSize={12} fill="var(--ivory)" fontWeight={600}>{i + 1}</text>
                </g>
              );
            })}
          </svg>
          <ol style={{ margin: 0, paddingLeft: 22 }}>
            {place.sites.map((s) => (
              <li key={s.name} style={{ marginBottom: 12 }}>
                <b>{s.name}</b> <span className="tiny muted num">({s.score.toFixed(2)})</span>
                <div className="small muted">{s.reason}</div>
              </li>
            ))}
          </ol>
        </div>
      )}
      {place && (
        <p className="small">
          <a href={`${API_BASE}/api/camps/placement.csv?k=10`}>{t("place_export")}</a>
          <span className="tiny muted"> · {place.candidates} candidate sites{place.kmeans.engine !== "none" ? ` · KMeans: ${place.kmeans.engine}, ${place.kmeans.ms} ms` : ""}</span>
        </p>
      )}
    </div>
  );
}
