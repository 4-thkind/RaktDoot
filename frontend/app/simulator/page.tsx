"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { api, type Config } from "@/lib/api";
import { GROUPS, formatPhone, show } from "@/lib/blood";

type ChatRow = { phone: string; name: string | null; group: string | null; location: string | null; last: string | null; last_at: string | null; last_direction: string | null };
type Msg = { id: number; direction: "in" | "out"; kind: string; body: string; options: { id: string; title: string }[] | null; location: { lat: number; lng: number; name?: string } | null; at: string };
type Chat = { phone: string; donor: { name: string; group: string; language: string; location: string | null; last_donation_date: string | null; opted_out: boolean } | null; messages: Msg[] };

const PLACES: [string, number, number][] = [
  ["Saket, South Delhi", 28.5245, 77.2066],
  ["Connaught Place", 28.6315, 77.2167],
  ["Cyber City, Gurugram", 28.495, 77.089],
  ["Sector 18, Noida", 28.5706, 77.3261],
];

export default function Page() {
  return (
    <Suspense fallback={null}>
      <Simulator />
    </Suspense>
  );
}

function Simulator() {
  const params = useSearchParams();
  const [cfg, setCfg] = useState<Config | null>(null);
  const [rows, setRows] = useState<ChatRow[]>([]);
  const [q, setQ] = useState("");
  const [group, setGroup] = useState("");
  const [phone, setPhone] = useState<string | null>(null);
  const [chat, setChat] = useState<Chat | null>(null);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<Config>("/api/config").then(setCfg).catch((e) => setError(e.message));
    if (params.get("new")) setPhone("91" + String(Math.floor(7000000000 + Math.random() * 2999999999)));
  }, [params]);

  const loadList = useCallback(() => {
    api<ChatRow[]>(`/api/mock/chats?q=${encodeURIComponent(q)}&group=${encodeURIComponent(group)}`).then(setRows).catch((e) => setError(e.message));
  }, [q, group]);

  const loadChat = useCallback(() => {
    if (!phone) return;
    api<Chat>(`/api/mock/chats/${phone}`).then((c) => {
      setChat((old) => (old && old.messages.length === c.messages.length && old.phone === c.phone ? old : c));
    }).catch((e) => setError(e.message));
  }, [phone]);

  useEffect(() => {
    if (cfg?.whatsapp_mode !== "mock") return;
    loadList();
    const id = setInterval(loadList, 3000);
    return () => clearInterval(id);
  }, [cfg, loadList]);

  useEffect(() => {
    if (cfg?.whatsapp_mode !== "mock" || !phone) return;
    setChat(null);
    loadChat();
    const id = setInterval(loadChat, 2000);
    return () => clearInterval(id);
  }, [cfg, phone, loadChat]);

  useEffect(() => {
    end.current?.scrollIntoView({ block: "end" });
  }, [chat?.messages.length]);

  async function send(body: { text?: string; button_id?: string; lat?: number; lng?: number }) {
    if (!phone) return;
    try {
      setChat(await api<Chat>("/api/mock/inbound", { method: "POST", body: JSON.stringify({ phone, ...body }) }));
      loadList();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (cfg && cfg.whatsapp_mode !== "mock") {
    return <div className="narrow" style={{ paddingTop: 32 }}><p className="note">The simulator only runs when the backend has WHATSAPP_MODE=mock. This server sends real WhatsApp messages.</p></div>;
  }

  const lastOptionsId = chat ? [...chat.messages].reverse().find((m) => m.direction === "out" && m.options)?.id : undefined;

  return (
    <div className="wrap" style={{ paddingTop: 24 }}>
      <div className="row" style={{ marginBottom: 14 }}>
        <div>
          <h1 className="h1">WhatsApp simulator</h1>
          <p className="muted small" style={{ margin: "4px 0 0" }}>
            Plays the donor&apos;s phone while the backend runs in mock mode. Every message here is exactly what the bot would send on WhatsApp.
          </p>
        </div>
      </div>
      {error && <p className="note" role="alert">{error}</p>}
      <div className="sim" data-open={phone ? "true" : "false"}>
        <aside className="sim-list">
          <div className="tools">
            <input className="input" style={{ minHeight: 40 }} type="search" placeholder="Search name or number" value={q} onChange={(e) => setQ(e.target.value)} />
            <div className="row" style={{ gap: 8 }}>
              <select className="input" style={{ minHeight: 40, flex: 1 }} value={group} onChange={(e) => setGroup(e.target.value)} aria-label="Filter by blood group">
                <option value="">All groups</option>
                {GROUPS.map((g) => <option key={g} value={g}>{show(g)}</option>)}
              </select>
              <button className="btn btn-quiet btn-sm" onClick={() => setPhone("91" + String(Math.floor(7000000000 + Math.random() * 2999999999)))}>New number</button>
            </div>
          </div>
          <ul>
            {rows.map((r) => (
              <li key={r.phone}>
                <button aria-current={phone === r.phone} onClick={() => setPhone(r.phone)}>
                  <span style={{ fontWeight: 600 }}>{r.name ?? formatPhone(r.phone)}</span>
                  <span className="small" style={{ color: "var(--burgundy)", fontFamily: "var(--serif)" }}>{r.group ? show(r.group) : ""}</span>
                  <span className="tiny muted" style={{ gridColumn: "1 / -1", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {r.last ? `${r.last_direction === "in" ? "You: " : ""}${r.last}` : r.location ?? ""}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <section className="sim-chat" aria-label="Chat">
          {phone ? (
            <>
              <header>
                <button className="linkbtn small" onClick={() => setPhone(null)} aria-label="Back to chats">Chats</button>
                <div>
                  <div style={{ fontWeight: 600 }}>{chat?.donor?.name ?? "Not registered"}</div>
                  <div className="tiny muted num">
                    {formatPhone(phone)}
                    {chat?.donor ? `, ${show(chat.donor.group)}, ${chat.donor.language === "hi" ? "Hindi" : "English"}` : ""}
                    {chat?.donor?.last_donation_date ? `, last donated ${chat.donor.last_donation_date}` : ""}
                    {chat?.donor?.opted_out ? ", opted out" : ""}
                  </div>
                </div>
              </header>
              <div className="sim-msgs">
                {chat && chat.messages.length === 0 && <p className="muted small" style={{ textAlign: "center" }}>No messages yet. Send JOIN to register this number.</p>}
                {chat?.messages.map((m) => (
                  <div key={m.id} className={`bubble ${m.direction}`}>
                    {m.location ? (
                      <a href={`https://maps.google.com/?q=${m.location.lat},${m.location.lng}`} target="_blank" rel="noreferrer">Location: {m.location.name || m.body}</a>
                    ) : m.body}
                    <time className="num">{new Date(m.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>
                    {m.direction === "out" && m.options && (
                      <div className="opts">
                        {m.options.map((o) => (
                          <button key={o.id} disabled={m.id !== lastOptionsId} onClick={() => send({ button_id: o.id })}>{o.title}</button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                <div ref={end} />
              </div>
              <form className="sim-compose" onSubmit={(e) => { e.preventDefault(); if (text.trim()) { send({ text }); setText(""); } }}>
                <select className="input" style={{ maxWidth: 150 }} aria-label="Share a location" value=""
                  onChange={(e) => { const p = PLACES[Number(e.target.value)]; if (p) send({ lat: p[1], lng: p[2] }); }}>
                  <option value="">Location</option>
                  {PLACES.map(([n], i) => <option key={n} value={i}>{n}</option>)}
                </select>
                <input className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Type a reply, e.g. haan 20 min mein" />
                <button className="btn btn-primary btn-sm" type="submit">Send</button>
              </form>
            </>
          ) : (
            <div className="sim-msgs" style={{ justifyContent: "center", alignItems: "center" }}>
              <p className="muted">Pick a donor to see their WhatsApp, or start a new number.</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
