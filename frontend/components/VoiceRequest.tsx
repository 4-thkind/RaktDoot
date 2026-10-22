"use client";

import { useRef, useState } from "react";
import { ApiError, upload, type SlipFields } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { FieldsReview } from "./ScanSlip";

type Parsed = { transcript: string; engine?: string; sample?: boolean; error?: string | null; fields: (SlipFields & { money_ask?: boolean }) | null };

/** F4 on the web: say the request, review what was understood, then pre-fill the flow. */
export function VoiceRequest({ onUse }: { onUse: (f: SlipFields) => void }) {
  const { t, lang } = useLang();
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [res, setRes] = useState<Parsed | null>(null);
  const media = useRef<MediaRecorder | null>(null);
  const limit = useRef<ReturnType<typeof setTimeout>>(undefined);

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

  // Record in the browser and transcribe on our server (local Whisper): works offline, in any browser,
  // and on phones; the browser's own speech recognition depends on Google and fails silently in many setups.
  async function start() {
    setRes(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setRes({ transcript: "", fields: null, error: t("voice_unsupported") });
      return;
    }
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setRes({ transcript: "", fields: null, error: t("voice_denied") });
      return;
    }
    const m = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    m.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    m.onstop = () => {
      stream.getTracks().forEach((x) => x.stop());
      clearTimeout(limit.current);
      setListening(false);
      fromAudio(new Blob(chunks, { type: m.mimeType || "audio/webm" }));
    };
    media.current = m;
    setListening(true);
    m.start();
    limit.current = setTimeout(() => m.state === "recording" && m.stop(), 30000); // a request fits in 30 s
  }

  function stop() {
    if (media.current?.state === "recording") media.current.stop();
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
