import { createClient } from "@supabase/supabase-js";

// Placeholders keep `next build` working when the keys are not set yet; real auth needs the real values.
const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "http://localhost:54321";
const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "missing-anon-key";

export const supabase = createClient(url, key);