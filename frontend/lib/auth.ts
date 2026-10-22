"use client";

import type { User as SupabaseUser } from "@supabase/supabase-js";
import { useEffect, useState } from "react";
import { ApiError, api } from "./api";
import { supabase } from "./supabase";

export type User = { id: string; email: string; name: string; phone: string; whatsapp_consent: boolean };

function toUser(u?: SupabaseUser | null): User | null {
  if (!u) return null;
  const m = u.user_metadata || {};
  return { id: u.id, email: u.email || "", name: m.name || u.email || "", phone: m.phone || "", whatsapp_consent: m.whatsapp_consent === true };
}

/** Supabase errors as ApiError, so the pages show the real reason instead of "Something went wrong". */
function authError(e: { message: string; status?: number; code?: string }): ApiError {
  if (e.code === "over_email_send_rate_limit" || e.status === 429)
    return new ApiError(429, "Too many sign-up emails were sent in the last hour. Please wait a few minutes and try again, or log in if you already have an account.");
  if (e.code === "email_not_confirmed") return new ApiError(400, "Please confirm your email first: open the link we emailed you, then log in.");
  if (e.code === "invalid_credentials") return new ApiError(400, "Wrong email or password.");
  if (e.code === "user_already_exists") return new ApiError(400, "An account with this email already exists. Please log in.");
  return new ApiError(e.status ?? 0, e.message || "Could not reach the login service. Check your connection and try again.");
}

/** Ask our backend to send the WhatsApp welcome. It sends only once per account, so calling it again is safe. */
async function sendWelcome(accessToken: string) {
  try {
    await api("/api/auth/welcome", { method: "POST", token: accessToken });
  } catch {
    // a WhatsApp problem must never block signup or login
  }
}

export async function signup(body: { name: string; email: string; phone: string; password: string; whatsapp_consent: boolean; telegram_consent?: boolean; language: string }) {
  const { data, error } = await supabase.auth.signUp({
    email: body.email.trim(),
    password: body.password,
    options: { data: { name: body.name.trim(), phone: body.phone, language: body.language, whatsapp_consent: body.whatsapp_consent, telegram_consent: body.telegram_consent === true } },
  });
  if (error) throw authError(error);
  // No session means Supabase wants the email confirmed first; the welcome is then sent on first login.
  if (data.session) {
    await sendWelcome(data.session.access_token);
    return { needsConfirm: false };
  }
  return { needsConfirm: true };
}

export async function login(body: { email: string; password: string }) {
  const { data, error } = await supabase.auth.signInWithPassword({ email: body.email.trim(), password: body.password });
  if (error) throw authError(error);
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