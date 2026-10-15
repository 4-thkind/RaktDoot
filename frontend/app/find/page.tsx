"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { StockPlate } from "@/components/ProximityPlate";
import { API_BASE, api, type Bank, type Group, type Place, type StockResult } from "@/lib/api";
import { GROUPS, RECEIVES_FROM, mapLink, show } from "@/lib/blood";
import { useAgo, useLang } from "@/lib/i18n";

type Step = 1 | 2 | 3 | 4 | 5;
type Origin = { lat: number; lng: number; label: string };
type Gender = "M" | "F" | "O";
const TOTAL = 5;

export default function FindBlood() {
  const { t, lang } = useLang();
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [group, setGroup] = useState<Group | null>(null);
  const [groupConfirmed, setGroupConfirmed] = useState(true);
  const [origin, setOrigin] = useState<Origin | null>(null);
  const [hospital, setHospital] = useState<Place | null>(null);

  // details
  const [units, setUnits] = useState(1);
  const [age, setAge] = useState("");
  const [gender, setGender] = useState<Gender | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const top = useRef<HTMLDivElement>(null);
  const go = (s: Step) => {
    setStep(s);
    requestAnimationFrame(() => top.current?.scrollIntoView({ block: "start" }));
  };

  function validate() {
    const e: Record<string, string> = {};
    const a = Number(age);
    if (age === "" || !Number.isFinite(a) || a < 0 || a > 120) e.age = t("err_age");
    if (!gender) e.gender = t("err_required");
    if (!hospital) e.hospital = t("err_hospital");
    if (!name.trim()) e.name = t("err_required");
    const digits = phone.replace(/\D/g, "").replace(/^(91|0)(?=\d{10}$)/, "");
    if (!/^[6-9]\d{9}$/.test(digits)) e.phone = t("err_phone");
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function send() {
    if (!group || !hospital || !gender) return;
    setSubmitting(true);
    setSubmitError("");
    try {
      const created = await api<{ id: string; manage_token: string }>("/api/requests", {
        method: "POST",
        body: JSON.stringify({
          patient_group: group, group_confirmed: groupConfirmed, units, patient_age: Number(age), patient_gender: gender,
          hospital_name: hospital.name, hospital_address: hospital.address, hospital_lat: hospital.lat, hospital_lng: hospital.lng,
          requester_name: name.trim(), requester_phone: phone, language: lang,
        }),
      });
      await api(`/api/requests/${created.id}/dispatch?t=${encodeURIComponent(created.manage_token)}`, { method: "POST" });
      try {
        localStorage.setItem(`rd:req:${created.id}`, created.manage_token);
      } catch {}
      router.push(`/request/${created.id}?t=${encodeURIComponent(created.manage_token)}`);
    } catch (err) {
      setSubmitError((err as Error).message);
      setSubmitting(false);
    }
  }

  return (
    <div className="narrow" ref={top} style={{ scrollMarginTop: 12 }}>
      <div className="progress" aria-live="polite">
        {step > 1 && (
          <button className="linkbtn" onClick={() => go((step - 1) as Step)}>{t("back")}</button>
        )}
        <span>{t("step_of", { n: step, total: TOTAL })}</span>
        <span className="bar" aria-hidden><i style={{ width: `${(step / TOTAL) * 100}%` }} /></span>
      </div>

      {step === 1 && (
        <GroupStep
          selected={group}
          onPick={(g, confirmed) => {
            setGroup(g);
            setGroupConfirmed(confirmed);
            go(origin ? 3 : 2);
          }}
        />
      )}

      {step === 2 && (
        <WhereStep
          onPick={(o, place) => {
            setOrigin(o);
            if (place) setHospital(place);
            go(3);
          }}
        />
      )}

      {step === 3 && group && origin && (
        <StockStep group={group} origin={origin} onAskDonors={() => go(4)} />
      )}

      {step === 4 && origin && (
        <section className="stack" style={{ ["--gap" as string]: "22px" }}>
          <h1 className="h1">{t("q_details")}</h1>
          <div className="field">
            <span className="label" id="units-l">{t("units_needed")}</span>
            <div className="stepper" role="group" aria-labelledby="units-l">
              <button type="button" aria-label="One fewer" onClick={() => setUnits((u) => Math.max(1, u - 1))} disabled={units <= 1}>−</button>
              <output className="num" aria-live="polite">{units}</output>
              <button type="button" aria-label="One more" onClick={() => setUnits((u) => Math.min(12, u + 1))} disabled={units >= 12}>+</button>
            </div>
          </div>
          <label className="field">
            <span className="label">{t("age")}</span>
            <input className="input num" inputMode="numeric" maxLength={3} value={age} aria-invalid={!!errors.age}
              onChange={(e) => setAge(e.target.value.replace(/\D/g, ""))} />
            {errors.age && <span className="err">{errors.age}</span>}
          </label>
          <div className="field">
            <span className="label" id="gender-l">{t("gender")}</span>
            <div className="seg" role="group" aria-labelledby="gender-l">
              {(["M", "F", "O"] as Gender[]).map((g) => (
                <button key={g} type="button" aria-pressed={gender === g} onClick={() => setGender(g)}>
                  {t(g === "M" ? "male" : g === "F" ? "female" : "other")}
                </button>
              ))}
            </div>
            {errors.gender && <span className="err">{errors.gender}</span>}
          </div>
          <HospitalField origin={origin} value={hospital} onChange={setHospital} error={errors.hospital} />
          <label className="field">
            <span className="label">{t("your_name")}</span>
            <input className="input" autoComplete="given-name" value={name} maxLength={80} aria-invalid={!!errors.name} onChange={(e) => setName(e.target.value)} />
            {errors.name && <span className="err">{errors.name}</span>}
          </label>
          <label className="field">
            <span className="label">{t("your_phone")}</span>
            <input className="input num" type="tel" autoComplete="tel" inputMode="tel" placeholder="98765 43210" value={phone}
              aria-invalid={!!errors.phone} onChange={(e) => setPhone(e.target.value)} />
            <span className="help">{t("phone_help")}</span>
            {errors.phone && <span className="err">{errors.phone}</span>}
          </label>
          <div className="dock">
            <button className="btn btn-primary btn-block" onClick={() => validate() && go(5)}>{t("continue")}</button>
          </div>
        </section>
      )}

      {step === 5 && group && hospital && gender && (
        <section className="stack" style={{ ["--gap" as string]: "18px" }}>
          <h1 className="h1">{t("q_review")}</h1>
          <p className="muted" style={{ margin: "8px 0 0" }}>{t("review_body")}</p>
          <div className="letter num" aria-label="Message preview">
            {[
              "URGENT BLOOD REQUEST (Rakt Doot)",
              `Patient needs: ${show(group)} (${units} unit${units > 1 ? "s" : ""})${groupConfirmed ? "" : " - group not yet confirmed"}`,
              `Can receive from: ${RECEIVES_FROM[group].map(show).join(", ")}`,
              `Patient: ${age}, ${gender === "M" ? "Male" : gender === "F" ? "Female" : "Other"}`,
              `Hospital: ${hospital.name}`,
              "Distance from you: shown to each donor",
            ].join("\n")}
          </div>
          <ul className="small muted" style={{ paddingLeft: 18, marginBottom: 0 }}>
            <li>{t("phone_help")}</li>
            <li>{t("trust_1")}</li>
            <li>{t("trust_2")}</li>
          </ul>
          {submitError && <p className="note" role="alert">{submitError}</p>}
          <div className="dock">
            <button className="btn btn-primary btn-block btn-xl" onClick={send} disabled={submitting}>
              {submitting ? t("sending") : t("send")}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ step 1 */
function GroupStep({ selected, onPick }: { selected: Group | null; onPick: (g: Group, confirmed: boolean) => void }) {
  const { t } = useLang();
  const [unsure, setUnsure] = useState(false);
  return (
    <section>
      <h1 className="h1">{t("q_group")}</h1>
      <div className="groups" role="group" aria-label={t("q_group")}>
        {GROUPS.map((g) => (
          <button key={g} className="group-tile" aria-pressed={selected === g} onClick={() => onPick(g, true)}>{show(g)}</button>
        ))}
      </div>
      <div style={{ marginTop: 22 }}>
        {!unsure ? (
          <button className="linkbtn" onClick={() => setUnsure(true)}>{t("dont_know")}</button>
        ) : (
          <div className="sheet stack">
            <p style={{ margin: 0 }}>{t("dont_know_body")}</p>
            <button className="btn btn-secondary" onClick={() => onPick("O-", false)}>{t("search_o_neg")}</button>
          </div>
        )}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ step 2 */
function usePlaceSearch(origin?: Origin | null) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Place[] | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const query = q.trim();
    if (query.length < 2) {
      setResults(null);
      return;
    }
    let live = true;
    setBusy(true);
    const id = setTimeout(async () => {
      const near = origin ? `&lat=${origin.lat}&lng=${origin.lng}` : "";
      try {
        const res = await api<Place[]>(`/api/places/search?q=${encodeURIComponent(query)}${near}`);
        if (live) setResults(res);
      } catch {
        if (live) setResults([]);
      } finally {
        if (live) setBusy(false);
      }
    }, 350);
    return () => {
      live = false;
      clearTimeout(id);
    };
  }, [q, origin]);
  return { q, setQ, results, busy };
}

function WhereStep({ onPick }: { onPick: (o: Origin, place?: Place) => void }) {
  const { t } = useLang();
  const [locating, setLocating] = useState(false);
  const [denied, setDenied] = useState(false);
  const { q, setQ, results, busy } = usePlaceSearch();

  function locate() {
    if (!("geolocation" in navigator)) {
      setDenied(true);
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        onPick({ lat: pos.coords.latitude, lng: pos.coords.longitude, label: "you" });
      },
      () => {
        setLocating(false);
        setDenied(true);
      },
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 300000 },
    );
  }

  return (
    <section className="stack" style={{ ["--gap" as string]: "18px" }}>
      <h1 className="h1">{t("q_where")}</h1>
      <p className="muted" style={{ margin: "8px 0 0" }}>{t("where_body")}</p>
      <button className="btn btn-primary btn-block" onClick={locate} disabled={locating}>
        {locating ? t("locating") : t("use_location")}
      </button>
      {denied && <p className="note" role="status">{t("loc_denied")}</p>}
      <label className="field" style={{ marginTop: 26 }}>
        <span className="label">{t("or_search")}</span>
        <input className="input" type="search" value={q} placeholder={t("search_ph")} onChange={(e) => setQ(e.target.value)} autoComplete="off" />
      </label>
      {results && results.length === 0 && !busy && <p className="muted small">{t("no_results")}</p>}
      {results && results.length > 0 && (
        <ul className="choices">
          {results.map((p, i) => (
            <li key={`${p.name}-${i}`}>
              <button onClick={() => onPick({ lat: p.lat, lng: p.lng, label: p.name }, p.source === "pincode" ? undefined : p)}>
                <span className="t">{p.name}</span>
                <span className="s">{p.address}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ step 3 */
function StockStep({ group, origin, onAskDonors }: { group: Group; origin: Origin; onAskDonors: () => void }) {
  const { t, lang } = useLang();
  const ago = useAgo();
  const [log, setLog] = useState<string[]>([]);
  const [agentUrl, setAgentUrl] = useState<string | null>(null);
  const [result, setResult] = useState<StockResult | null>(null);
  const [, tick] = useState(0);

  useEffect(() => {
    setLog([t("checking")]);
    setResult(null);
    const url = `${API_BASE}/api/stock/stream?lat=${origin.lat}&lng=${origin.lng}&group=${encodeURIComponent(group)}`;
    const es = new EventSource(url);
    let finished = false;
    es.addEventListener("progress", (ev) => {
      const data = JSON.parse((ev as MessageEvent).data);
      if (data.streaming_url) setAgentUrl(data.streaming_url);
      if (data.message) setLog((l) => (l[l.length - 1] === data.message ? l : [...l, data.message]));
    });
    es.addEventListener("result", (ev) => {
      finished = true;
      setResult(JSON.parse((ev as MessageEvent).data));
    });
    es.addEventListener("done", () => es.close());
    es.onerror = () => {
      es.close();
      if (!finished) {
        setResult({ source: "unavailable", sample: false, fetched_at: null, run_id: null, streaming_url: null, reason: "connection lost",
          group, compatible_groups: [], banks: [], summary: { banks_checked: 0, banks_with_stock: 0, suggest_donors: true } });
      }
    };
    const timer = setInterval(() => tick((n) => n + 1), 30000);
    return () => {
      es.close();
      clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [group, origin.lat, origin.lng]);

  const place = origin.label === "you" ? (lang === "hi" ? "आप" : "you") : origin.label;
  const banks = result?.banks ?? [];
  const points = useMemo(
    () => banks.filter((b) => b.distance_km !== null && b.bearing !== null).map((b) => ({
      bearing: b.bearing as number, distance_km: b.distance_km as number, filled: (b.total_compatible ?? 0) > 0,
      label: `${b.name}, ${b.distance_km} km, ${b.total_compatible ?? 0} units`,
    })),
    [banks],
  );

  return (
    <section className="stack" style={{ ["--gap" as string]: "18px" }}>
      <h1 className="h1">{t("q_stock", { place })}</h1>
      <p className="muted" style={{ margin: "8px 0 0" }}>{t("stock_for", { group: show(group) })}</p>

      {!result && (
        <div className="sheet" aria-live="polite">
          <ul className="log">
            {log.map((line, i) => <li key={i} className={i === log.length - 1 ? "now" : undefined}>{line}</li>)}
          </ul>
          {agentUrl && <p style={{ margin: "10px 0 0" }}><a href={agentUrl} target="_blank" rel="noreferrer">{t("watch_agent")}</a></p>}
          <p className="small muted" style={{ margin: "12px 0 0" }}>
            <button className="linkbtn" onClick={onAskDonors}>{t("ask_donors")}</button>
          </p>
        </div>
      )}

      {result && (
        <>
          {result.sample && <p className="note">{t("sample_note")}</p>}
          {result.source === "stale_cache" && <p className="note">{t("stale_note", { reason: result.reason ?? "" })}</p>}
          {result.source === "unavailable" && <p className="note">{t("unavailable_note", { reason: result.reason ?? "" })}</p>}

          {result.summary.suggest_donors && (
            <div className="pivot stack" style={{ ["--gap" as string]: "10px" }}>
              <h2 className="h2">{t("pivot_title")}</h2>
              <p style={{ margin: 0 }}>{t("pivot_body")}</p>
              <button className="btn btn-primary btn-block" onClick={onAskDonors}>{t("ask_donors")}</button>
            </div>
          )}

          {points.length > 0 && (
            <div>
              <StockPlate points={points} label={`${banks.length} blood centres around the hospital`} />
              <div className="plate-caption">
                <span><i style={{ background: "var(--burgundy)" }} />{show(group)} usable stock</span>
                <span><i style={{ border: "1.5px solid var(--burgundy)" }} />{t("none_listed")}</span>
              </div>
            </div>
          )}

          {banks.length > 0 && (
            <>
              <div className="row small muted">
                <span>{result.place ? `${result.place.district}, ${result.place.state}` : ""}</span>
                <span className="spacer" />
                {result.fetched_at && <span>{t("fetched", { when: ago(result.fetched_at) })}</span>}
                {result.streaming_url && <a href={result.streaming_url} target="_blank" rel="noreferrer">{t("watch_agent")}</a>}
              </div>
              <ul className="register">
                {banks.map((b, i) => <BankRow key={`${b.name}-${i}`} bank={b} group={group} />)}
              </ul>
              <p className="small muted">{t("found_stock")}</p>
            </>
          )}

          {!result.summary.suggest_donors && (
            <div className="dock">
              <button className="btn btn-secondary btn-block" onClick={onAskDonors}>{t("ask_donors")}</button>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function BankRow({ bank, group }: { bank: Bank; group: Group }) {
  const { t } = useLang();
  const total = bank.total_compatible ?? 0;
  const entries = Object.entries(bank.compatible_units) as [Group, number][];
  return (
    <li>
      <div>
        <div className="name">{bank.name}</div>
        <div className="meta num">
          {bank.distance_km !== null ? `${bank.distance_km} ${t("km")}` : t("distance_unknown")}
          {bank.category ? `, ${bank.category}` : ""}
          {bank.last_updated ? `, ${bank.last_updated}` : ""}
        </div>
      </div>
      <div className="units num">
        <b className={total ? undefined : "zero"}>{total}</b>
        <span>{t("units_of")}</span>
      </div>
      {entries.length > 0 && (
        <div className="split num" aria-label={`Stock by group for a ${group} patient`}>
          {entries.map(([g, n]) => (
            <span key={g} className={n ? "has" : "none"}>{show(g)} {n}</span>
          ))}
        </div>
      )}
      {!entries.length && bank.availability_text && <div className="split">{bank.availability_text}</div>}
      <div className="actions">
        {bank.phone && <a className="btn btn-quiet btn-sm" href={`tel:${bank.phone.replace(/[^\d+]/g, "")}`}>{t("call")} {bank.phone}</a>}
        {bank.lat !== null && bank.lng !== null && (
          <a className="btn btn-quiet btn-sm" href={mapLink(bank.lat, bank.lng)} target="_blank" rel="noreferrer">{t("directions")}</a>
        )}
      </div>
    </li>
  );
}

/* ------------------------------------------------------------------ hospital */
function HospitalField({ origin, value, onChange, error }: { origin: Origin; value: Place | null; onChange: (p: Place) => void; error?: string }) {
  const { t } = useLang();
  const [editing, setEditing] = useState(!value);
  const [nearby, setNearby] = useState<Place[]>([]);
  const { q, setQ, results } = usePlaceSearch(origin);

  useEffect(() => {
    api<Place[]>(`/api/places/nearby-hospitals?lat=${origin.lat}&lng=${origin.lng}`).then(setNearby).catch(() => setNearby([]));
  }, [origin.lat, origin.lng]);

  const list = results ?? nearby;
  return (
    <div className="field">
      <span className="label">{t("hospital")}</span>
      {value && !editing ? (
        <div className="sheet row" style={{ padding: 14 }}>
          <div>
            <div style={{ fontWeight: 600 }}>{value.name}</div>
            {value.address && <div className="small muted">{value.address}</div>}
          </div>
          <span className="spacer" />
          <button className="linkbtn" onClick={() => setEditing(true)}>{t("change")}</button>
        </div>
      ) : (
        <>
          <input className="input" type="search" value={q} placeholder={t("search_ph")} onChange={(e) => setQ(e.target.value)} aria-invalid={!!error} />
          <ul className="choices" style={{ marginTop: 8 }}>
            {list.map((p, i) => (
              <li key={`${p.name}-${i}`}>
                <button type="button" aria-pressed={value?.name === p.name} onClick={() => { onChange(p); setEditing(false); }}>
                  <span className="t">{p.name}</span>
                  <span className="s">{p.address}</span>
                  {p.distance_km !== undefined && <span className="d num">{p.distance_km} {t("km")}</span>}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
      <span className="help">{t("hospital_help")}</span>
      {error && <span className="err">{error}</span>}
    </div>
  );
}
