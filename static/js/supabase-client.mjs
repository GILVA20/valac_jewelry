import { createClient } from "https://esm.sh/@supabase/supabase-js@2.12.0";

const url = globalThis.SUPABASE_URL;
const key = globalThis.SUPABASE_ANON_KEY;

if (!url || !key) {
  throw new Error(
    "[Supabase] Missing SUPABASE_URL or SUPABASE_ANON_KEY. Check base.html injection."
  );
}
// Verification log (boolean flags only, never log secrets)
console.log('[supabase-client] initialized:', !!url, !!key);

export const supabase = createClient(url, key);
