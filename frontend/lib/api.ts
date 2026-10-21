// empty = same origin: Next proxies /api to the backend (see next.config.mjs)
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, init?: RequestInit & { admin?: string; token?: string }): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (init?.admin) headers["X-Admin-Token"] = init.admin;
  if (init?.token) headers["Authorization"] = `Bearer ${init.token}`;
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers: { ...headers, ...(init?.headers as Record<string, string>) } });
  } catch {
    throw new ApiError(0, "Cannot reach the Rakt Doot server. Check your connection and try again.");
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") msg = body.detail;
      else if (Array.isArray(body.detail)) msg = body.detail.map((d: { msg: string }) => d.msg.replace(/^Value error, /, "")).join(". ");
    } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

/** multipart upload (no JSON content-type, the browser sets the boundary) */
export async function upload<T>(path: string, form: FormData): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
  } catch {
    throw new ApiError(0, "Cannot reach the Rakt Doot server. Check your connection and try again.");
  }
  if (!res.ok) throw new ApiError(res.status, `Upload failed (${res.status})`);
  return res.json() as Promise<T>;
}

export type Group = "A+" | "A-" | "B+" | "B-" | "AB+" | "AB-" | "O+" | "O-";
export type Component = "prbc" | "platelets" | "plasma" | "whole_blood";

export type Bank = {
  name: string;
  address: string | null;
  phone: string | null;
  category: string | null;
  last_updated: string | null;
  distance_km: number | null;
  bearing: number | null;
  lat: number | null;
  lng: number | null;
  exact_units: number | null;
  compatible_units: Partial<Record<Group, number>>;
  total_compatible: number | null;
  availability_text: string | null;
  match_score?: number | null;
};

export type StockResult = {
  source: "live" | "cache" | "stale_cache" | "demo" | "unavailable";
  sample: boolean;
  fetched_at: string | null;
  run_id: string | null;
  streaming_url: string | null;
  reason: string | null;
  component?: Component;
  component_label?: string | null;
  served_by?: "cache" | "replay" | "agent" | "sample" | "stale_cache" | "none" | null;
  duration_s?: number | null;
  steps?: number | null;
  group: Group;
  compatible_groups: Group[];
  banks: Bank[];
  place?: { state: string; district: string };
  summary: { banks_checked: number; banks_with_stock: number; nearest_stock_km?: number | null; near_threshold_km?: number; suggest_donors: boolean };
};

export type Place = { name: string; address: string | null; lat: number; lng: number; distance_km?: number; source?: string };

export type DonorCard = {
  id: string;
  name: string;
  group: Group;
  distance_km: number;
  status: "accepted" | "connected" | "donated" | "deferred" | "no_show";
  eta_minutes: number | null;
  phone: string | null;
  since: string | null;
};

export type Snapshot = {
  id: string;
  status: "open" | "dispatching" | "matched" | "needs_public_share" | "fulfilled" | "expired" | "cancelled";
  patient_group: Group;
  group_confirmed: boolean;
  compatible: Group[];
  units: number;
  patient_age: number;
  patient_gender: "M" | "F" | "O";
  hospital: { name: string; address: string | null; lat: number; lng: number; verified: boolean | null; check: HospitalCheck };
  component: Component;
  kind: "emergency" | "drive" | "recurring";
  allow_o_neg: boolean;
  decisions: Decision[];
  requester_name: string;
  target: number;
  wave: number;
  radius_km: number;
  next_wave_at: string | null;
  created_at: string;
  dispatched_at: string | null;
  expires_at: string | null;
  closed_at: string | null;
  seconds_to_first_donor: number | null;
  funnel: { notified: number; delivered: number; read: number; responded: number; connected: number };
  counts: Record<string, number>;
  rings: { radius_km: number; notified: number }[];
  donors: DonorCard[];
  share_url: string;
  share_slug: string;
  preview: string;
};

export type HospitalCheck = {
  score?: number;
  verified?: boolean | null;
  evidence?: { source: string; title: string; url?: string; distance_km?: number | null; match?: number }[];
  checked_with?: string[];
};

export type Decision = { at: string; engine: "llm" | "rules" | "fallback"; action: string; args: Record<string, unknown>; reason: string; result: string };

export type SlipFields = {
  patient_group: Group | null; units: number | null; component: Component | null; hospital: string | null; ward: string | null;
  urgency: string | null; date: string | null; patient_name: string | null; confidence: Record<string, number>;
};

export type GuideAnswer = { answer: string; sources: { title: string; url: string }[]; refused: boolean; engine: string };

export type Config = {
  whatsapp_mode: "cloud" | "twilio" | "mock"; tinyfish_mode: "live" | "demo"; join_link: string; component: string; radii_km: number[];
  quiet_hours: boolean; llm: "live" | "rules"; vision: "live" | "sample"; stt: string; replay: boolean; proxy_country: string;
  dispatch_agent: "llm" | "rules" | "off"; bandit: boolean; intel_sklearn: boolean;
};
