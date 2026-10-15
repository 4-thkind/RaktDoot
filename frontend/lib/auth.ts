"use client";

import type { User as SupabaseUser } from "@supabase/supabase-js";
import { useEffect, useState } from "react";
import { api } from "./api";
import { supabase } from "./supabase";

export type User = { id: string; email: string; name: string; phone: string; whatsapp_consent: boolean };

function toUser(u?: SupabaseUser | null): User | null {
  if (!u) return null;
  const m = u.user_metadata || {};
  return { id: u.id, email: u.email || "", name: m.name || u.email || "", phone: m.phone || "", whatsapp_consent: m.whatsapp_consent === true };
}

/** Ask our backend to send the WhatsApp welcome. It sends only once per account, so calling it again is safe. */
async function sendWelcome(accessToken: string) {
  try {
    await api("/api/auth/welcome", { method: "POST", token: accessToken });
  } catch {
    // a WhatsApp problem must never block signup or login
  }
}

export async function signup(body: { name: string; email: string; phone: string; password: string; whatsapp_consent: boolean; language: string }) {
  const { data, error } = await supabase.auth.signUp({
    email: body.email.trim(),
    password: body.password,
    options: { data: { name: body.name.trim(), phone: body.phone, language: body.language, whatsapp_consent: body.whatsapp_consent } },
  });
  if (error) throw new Error(error.message);
  // No session means Supabase wants the email confirmed first; the welcome is then sent on first login.
  if (data.session) {
    await sendWelcome(data.session.access_token);
    return { needsConfirm: false };
  }
  return { needsConfirm: true };
}

export async function login(body: { email: string; password: string }) {
  const { data, error } = await supabase.auth.signInWithPassword({ email: body.email.trim(), password: body.password });
  if (error) throw new Error(error.message);
  await sendWelcome(data.session.access_token);
}

export async function logout() {
  await supabase.auth.signOut();
}

/** The logged-in user. Supabase keeps the session in the browser and refreshes it automatically. */
export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setUser(toUser(data.session?.user));
      setReady(true);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => setUser(toUser(session?.user)));
    return () => sub.subscription.unsubscribe();
  }, []);
  return { user, ready };
}