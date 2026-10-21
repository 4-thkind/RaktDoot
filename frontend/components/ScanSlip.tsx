"use client";

import { useRef, useState } from "react";
import { API_BASE, ApiError, upload, type SlipFields } from "@/lib/api";
import { show } from "@/lib/blood";
import { useLang, type Key } from "@/lib/i18n";

type Result = { fields: SlipFields | null; error?: string; sample?: boolean; low_confidence?: string[]; engine?: string };
const SHOWN: (keyof SlipFields)[] = ["patient_group", "component", "units", "hospital", "ward", "urgency", "date"];

/** Downscale and re-encode on the device before upload: smaller, faster, and strips EXIF location. */
async function shrink(file: File, max = 1600): Promise<Blob> {
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, max / Math.max(bmp.width, bmp.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bmp.width * scale);
  canvas.height = Math.round(bmp.height * scale);
  canvas.getContext("2d")!.drawImage(bmp, 0, 0, canvas.width, canvas.height);
  return new Promise((res, rej) => canvas.toBlob((b) => (b ? res(b) : rej(new Error("encode failed"))), "image/jpeg", 0.8));
}

/** F3: photograph the requisition slip, review what was read, then pre-fill the flow. */
export function ScanSlip({ onUse }: { onUse: (f: SlipFields) => void }) {
  const { t } = useLang();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<Result | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  async function send(path: string, form: FormData) {
    setBusy(true);
    setRes(null);
    try {
      setRes(await upload<Result>(path, form));
    } catch (e) {
      setRes({ fields: null, error: e instanceof ApiError ? e.message : "Could not read the slip." });
    } finally {
      setBusy(false);
    }
  }

  async function pick(file: File | undefined) {
    if (!file) return;
    const blob = await shrink(file).catch(() => file);
    setPreview(URL.createObjectURL(blob));
    const form = new FormData();
    form.append("file", blob, "slip.jpg");
    send("/api/vision/slip", form);
  }

  function sample() {
    setPreview(`${API_BASE}/api/samples/requisition_slip.jpg`);
    send("/api/vision/slip?sample=requisition_slip.jpg", new FormData());
  }

  const f = res?.fields;

  return (
    <div className="sheet stack" style={{ ["--gap" as string]: "12px" }}>
      <p style={{ margin: 0 }}>{t("scan_body")}</p>
      <div className="row">
        <button className="btn btn-secondary btn-sm" type="button" onClick={() => input.current?.click()} disabled={busy}>{t("scan_take")}</button>
        <button className="linkbtn small" type="button" onClick={sample} disabled={busy}>{t("scan_sample")}</button>
        <input ref={input} type="file" accept="image/*" capture="environment" hidden onChange={(e) => pick(e.target.files?.[0])} />
      </div>
      {busy && <p className="small muted" aria-live="polite" style={{ margin: 0 }}>{t("scan_reading")}</p>}
      {preview && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={preview} alt="" style={{ maxHeight: 220, width: "auto", borderRadius: 4, border: "1px solid var(--rule)" }} />
      )}
      {res?.error && <p className="note" role="alert" style={{ margin: 0 }}>{res.error}</p>}
      {f && (
        <>
          {res?.sample && <p className="note neutral small" style={{ margin: 0 }}>{t("scan_sample_note")}</p>}
          <FieldsReview fields={f} low={res?.low_confidence} onUse={onUse} />
        </>
      )}
      <p className="tiny muted" style={{ margin: 0 }}>{t("scan_privacy")}</p>
    </div>
  );
}


/** Shared review of request fields read from a slip or a voice note, low-confidence fields highlighted. */
export function FieldsReview({ fields: f, low, onUse }: { fields: SlipFields; low?: string[]; onUse: (f: SlipFields) => void }) {
  const { t } = useLang();
  const lowSet = new Set(low ?? Object.entries(f.confidence ?? {}).filter(([k, c]) => c < 0.6 && f[k as keyof SlipFields] != null).map(([k]) => k));
  const value = (k: keyof SlipFields) => {
    const v = f[k];
    if (v === null || v === undefined) return "-";
    if (k === "patient_group") return show(String(v));
    if (k === "component") return t(`comp_${v}` as Key);
    return String(v);
  };
  return (
    <>
      <h3 className="h3">{t("scan_check")}</h3>
      <dl className="small" style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 14px", margin: 0 }}>
        {SHOWN.map((k) => (
          <div key={k} style={{ display: "contents" }}>
            <dt className="muted">{t(`f_${k}` as Key)}</dt>
            <dd style={{ margin: 0, fontWeight: 600, background: lowSet.has(k) ? "var(--ochre-tint)" : undefined }}>
              {value(k)} {lowSet.has(k) && <span className="tiny" style={{ fontWeight: 400 }}>({t("scan_low")})</span>}
            </dd>
          </div>
        ))}
      </dl>
      <button className="btn btn-primary btn-sm" type="button" onClick={() => onUse(f)} disabled={!f.patient_group}>{t("scan_use")}</button>
    </>
  );
}
