"use client";

/**
 * The proximity plate: a range map centred on the patient's hospital. Rings are real distances
 * (square-root scale so the near rings stay readable) and marks sit on their true compass bearing.
 */

type Point = { bearing: number; distance_km: number; filled: boolean; label: string };

const SIZE = 400;
const C = SIZE / 2;
const R = 176;

function radiusFor(km: number, maxKm: number) {
  return R * Math.sqrt(Math.min(km, maxKm) / maxKm);
}

function polar(bearing: number, r: number) {
  const a = ((bearing - 90) * Math.PI) / 180;
  return [C + r * Math.cos(a), C + r * Math.sin(a)];
}

export function StockPlate({ points, label }: { points: Point[]; label: string }) {
  const rings = [5, 10, 25, 50];
  const maxKm = 50;
  return (
    <figure style={{ margin: 0 }}>
      <svg className="plate" viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label={label}>
        <Rings rings={rings} maxKm={maxKm} />
        {points.map((p, i) => {
          const far = p.distance_km > maxKm;
          const [x, y] = polar(p.bearing, radiusFor(p.distance_km, maxKm));
          return (
            <g key={i}>
              <title>{p.label}</title>
              {far && <line x1={x} y1={y} x2={polar(p.bearing, R + 10)[0]} y2={polar(p.bearing, R + 10)[1]} stroke="var(--burgundy)" strokeWidth={1.5} />}
              <circle cx={x} cy={y} r={6} fill={p.filled ? "var(--burgundy)" : "var(--ivory)"} stroke="var(--burgundy)" strokeWidth={1.6} />
            </g>
          );
        })}
        <Centre />
      </svg>
    </figure>
  );
}

export function DispatchPlate({ rings, reachedKm, label }: { rings: { radius_km: number; notified: number }[]; reachedKm: number; label: string }) {
  const maxKm = Math.max(...rings.map((r) => r.radius_km), 1);
  return (
    <svg className="plate" viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label={label}>
      {[...rings].reverse().map((r) => {
        const reached = r.radius_km <= reachedKm + 1e-6;
        return (
          <circle key={r.radius_km} cx={C} cy={C} r={radiusFor(r.radius_km, maxKm)}
            fill={reached ? "rgba(128, 1, 31, 0.07)" : "transparent"} stroke={reached ? "var(--burgundy)" : "var(--rule-strong)"}
            strokeWidth={reached ? 1.4 : 1} strokeDasharray={reached ? undefined : "3 5"} />
        );
      })}
      {rings.map((r, i) => {
        const inner = i ? radiusFor(rings[i - 1].radius_km, maxKm) : 0;
        const mid = (inner + radiusFor(r.radius_km, maxKm)) / 2;
        const reached = r.radius_km <= reachedKm + 1e-6;
        return (
          <g key={r.radius_km}>
            <text x={C} y={C - radiusFor(r.radius_km, maxKm) + 14} textAnchor="middle" fontSize={11.5} fill="var(--muted)" fontFamily="var(--sans)">{r.radius_km} km</text>
            {reached && r.notified > 0 && (
              <text x={C} y={C + mid + 7} textAnchor="middle" fontFamily="var(--serif)" fontSize={i === 0 ? 20 : 18} fill="var(--burgundy)">
                {r.notified}
              </text>
            )}
          </g>
        );
      })}
      <Centre />
    </svg>
  );
}

function Rings({ rings, maxKm }: { rings: number[]; maxKm: number }) {
  return (
    <g>
      {rings.map((km) => {
        const r = radiusFor(km, maxKm);
        return (
          <g key={km}>
            <circle cx={C} cy={C} r={r} fill="none" stroke="var(--rule-strong)" strokeWidth={1} strokeDasharray={km === maxKm ? undefined : "2 5"} />
            <text x={C + r * 0.7071 + 4} y={C + r * 0.7071 + 12} fontSize={12} fill="var(--muted)" fontFamily="var(--sans)">{km} km</text>
          </g>
        );
      })}
      <line x1={C} y1={C - R - 8} x2={C} y2={C - R + 6} stroke="var(--ink)" strokeWidth={1} />
      <text x={C} y={C - R - 12} textAnchor="middle" fontSize={12} fill="var(--ink)" fontFamily="var(--sans)">N</text>
    </g>
  );
}

function Centre() {
  return (
    <g aria-hidden>
      <circle cx={C} cy={C} r={11} fill="var(--ivory)" stroke="var(--ink)" strokeWidth={1} />
      <path d={`M${C - 5} ${C}h10M${C} ${C - 5}v10`} stroke="var(--burgundy)" strokeWidth={2.4} />
    </g>
  );
}
