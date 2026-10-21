"use client";

import { useRef, useState } from "react";
import { ApiError, api, upload, type SlipFields } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { FieldsReview } from "./ScanSlip";

type Parsed = { transcript: string; engine?: string; sample?: boolean; error?: string | null; fields: (SlipFields & { money_ask?: boolean }) | null };

// The browser's own speech recognition (Chrome, Edge, Safari) needs no server key; otherwise we record and upload.
type Rec = { lang: string; interimResults: boolean; maxAlternatives: number; start: () => void; stop: () => void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null; onerror: (() => void) | null; onend: (() => void) | null };
const recognizer = (): (new () => Rec) | null =>
  typeof window === "undefined" ? null : ((window as unknown as Record<string, unknown>).SpeechRecognition ?? (window as unknown as Record<string, unknown>).webkitSpeechRecognition) as (new () => Rec) | null;

/** F4 on the web: say the request, review what was understood, then pre-fill the flow. */
export function VoiceRequest({ onUse }: { onUse: (f: SlipFields) => void }) {
  const { t, lang } = useLang();
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [res, setRes] = useState<Parsed | null>(null);
  const rec = useRef<Rec | null>(null);
  const media = useRef<MediaRecorder | null>(null);

  async function fromText(text: string) {
    setBusy(true);
    try {
      setRes(await api<Parsed>("/api/extract", { method: "POST", body: JSON.stringify({ text }) }));
    } catch (e) {
      setRes({ transcript: text, fields: null, error: (e as ApiError).message });
    } finally {
      setBusy(false);
    }
  }

  async function fromAudio(blob: Blob | null, sample?: string) {
    setBusy(true);
    try {
      const form = new FormData();
      if (blob) form.append("file", blob, "voice.webm");
      setRes(await upload<Parsed>(sample ? `/api/voice/parse?sample=${sample}` : "/api/voice/parse", form));
    } catch (e) {
      setRes({ transcript: "", fields: null, error: (e as ApiError).message });
    } finally {
      setBusy(false);
    }
  }

  async function start() {
    setRes(null);
    const R = recognizer();
    if (R) {
      const r = new R();
      r.lang = lang === "hi" ? "hi-IN" : "en-IN";
      r.interimResults = false;
      r.maxAlternatives = 1;
      r.onresult = (e) => fromText(Array.from(e.results).map((x) => x[0].transcript).join(" "));
      r.onerror = () => setListening(false);
      r.onend = () => setListening(false);
      rec.current = r;
      setListening(true);
      r.start();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const m = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      m.ondataavailable = (e) => chunks.push(e.data);
      m.onstop = () => {
        stream.getTracks().forEach((x) => x.stop());
        setListening(false);
        fromAudio(new Blob(chunks, { type: m.mimeType || "audio/webm" }));
      };
      media.current = m;
      setListening(true);
      m.start();
    } catch {
      setRes({ transcript: "", fields: null, error: t("voice_none") });
    }
  }

  function stop() {
    rec.current?.stop();
    media.current?.stop();
  }

  return (
    <div className="sheet stack" style={{ ["--gap" as string]: "12px" }}>
      <p style={{ margin: 0 }}>{t("voice_body")}</p>
      <div className="row">
        {!listening ? (
          <button className="btn btn-primary btn-sm" type="button" onClick={start} disabled={busy} aria-label={t("voice_start")}>
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-2.08A7 7 0 0 0 19 12h-2Z" /></svg>
            {t("voice_start")}
          </button>
        ) : (
          <button className="btn btn-secondary btn-sm" type="button" onClick={stop}>{t("voice_stop")} · {t("voice_listening")}</button>
        )}
        <button className="linkbtn small" type="button" disabled={busy || listening}
          onClick={() => fromAudio(null, lang === "hi" ? "voice_request_hi.mp3" : "voice_request.mp3")}>{t("voice_sample")}</button>
      </div>
      {busy && <p className="small muted" aria-live="polite" style={{ margin: 0 }}>…</p>}
      {res?.transcript && <p className="small" style={{ margin: 0 }}>{t("voice_heard")}: <i>“{res.transcript}”</i>{res.engine ? <span className="tiny muted"> ({res.engine})</span> : null}</p>}
      {res && (res.error || !res.fields?.patient_group) && <p className="note small" role="alert" style={{ margin: 0 }}>{res.error || t("voice_none")}</p>}
      {res?.fields?.patient_group && <FieldsReview fields={res.fields} onUse={onUse} />}
      <p className="tiny muted" style={{ margin: 0 }}>{t("voice_privacy")}</p>
    </div>
  );
}
