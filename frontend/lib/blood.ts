import type { Group } from "./api";

export const GROUPS: Group[] = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

// Red cells / whole blood: patient -> groups they can receive from. Mirrors backend core/compatibility.py
export const RECEIVES_FROM: Record<Group, Group[]> = {
  "O-": ["O-"],
  "O+": ["O+", "O-"],
  "A-": ["A-", "O-"],
  "A+": ["A+", "A-", "O+", "O-"],
  "B-": ["B-", "O-"],
  "B+": ["B+", "B-", "O+", "O-"],
  "AB-": ["AB-", "A-", "B-", "O-"],
  "AB+": ["AB+", "AB-", "A+", "A-", "B+", "B-", "O+", "O-"],
};

/** Typographic minus for display; data keeps the ASCII hyphen. */
export const show = (g: string) => g.replace("-", "−");

export const telLink = (phone: string) => `tel:+${phone}`;
export const waLink = (phone: string, text?: string) => `https://wa.me/${phone}${text ? `?text=${encodeURIComponent(text)}` : ""}`;
export const mapLink = (lat: number, lng: number) => `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
export const formatPhone = (p: string) => (p.startsWith("91") && p.length === 12 ? `+91 ${p.slice(2, 7)} ${p.slice(7)}` : `+${p}`);
