"use client";

import { useState } from "react";
import { api, type GuideAnswer } from "@/lib/api";
import { useLang } from "@/lib/i18n";

/** Family guide (F13): cited answers from official documents only. */
export function GuidePanel() {
  const { t, lang } = useLang();
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [items, setItems] = useState<{ q: string; a: GuideAnswer }[]>([]);
  const [error, setError] = useState("");

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    const question = q.trim();
    if (question.length < 2) return;
    setBusy(true);
    setError("");
    try {
      const a = await api<GuideAnswer>(`/api/guide/ask?q=${encodeURIComponent(question)}&lang=${lang}`);
      setItems((x) => [{ q: question, a }, ...x].slice(0, 5));
      setQ("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="sheet stack" style={{ ["--gap" as string]: "12px" }} aria-labelledby="guide-h">
      <h2 className="h3" id="guide-h">{t("guide_title")}</h2>
      <form className="row" onSubmit={ask} style={{ flexWrap: "nowrap" }}>
        <input className="input" value={q} maxLength={500} placeholder={t("guide_ph")} onChange={(e) => setQ(e.target.value)} aria-label={t("guide_title")} />
        <button className="btn btn-secondary btn-sm" type="submit" disabled={busy}>{t("guide_ask")}</button>
      </form>
      {error && <p className="note" role="alert">{error}</p>}
      <div aria-live="polite" className="stack" style={{ ["--gap" as string]: "14px" }}>
        {items.map(({ q: question, a }, i) => (
          <div key={i}>
            <p className="small" style={{ margin: 0, fontWeight: 600 }}>{question}</p>
            <p style={{ margin: "4px 0 0" }}>{a.answer}{" "}
              {typeof window !== "undefined" && "speechSynthesis" in window && (
                <button type="button" className="linkbtn small" onClick={() => {
                  const u = new SpeechSynthesisUtterance(a.answer);
                  u.lang = lang === "hi" ? "hi-IN" : "en-IN";
                  window.speechSynthesis.cancel();
                  window.speechSynthesis.speak(u);
                }}>{t("listen")}</button>
              )}
            </p>
            {a.sources.length > 0 && (
              <p className="tiny muted" style={{ margin: "4px 0 0" }}>
                {t("guide_sources")}: {a.sources.map((s, j) => (
                  <span key={s.url}>{j > 0 && ", "}<a href={s.url} target="_blank" rel="noreferrer">{s.title}</a></span>
                ))}
              </p>
            )}
          </div>
        ))}
      </div>
      <p className="tiny muted" style={{ margin: 0 }}>{t("guide_note")}</p>
    </section>
  );
}
