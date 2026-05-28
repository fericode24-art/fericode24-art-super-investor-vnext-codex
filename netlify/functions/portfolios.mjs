// Netlify Function (v2) â€” store condiviso dei portafogli del tracker.
// Usa Netlify Blobs: store nativo, gratuito, incluso nel piano. Nessun
// account o dipendenza esterna. I dati arrivano qui GIÃ€ CIFRATI dal client
// (cifratura col PIN lato browser) â€” il server vede solo testo opaco.
//
//   GET  /.netlify/functions/portfolios   â†’ ritorna il JSON salvato
//   POST /.netlify/functions/portfolios   â†’ salva il JSON inviato nel body
//
// FIX BUG #a (round 4): POST richiede header X-Tracker-Token che combacia
// con env var TRACKER_SYNC_TOKEN. Senza, chiunque puÃ² sovrascrivere i blob.
// GET resta libero perchÃ© i blob sono cifrati lato client col PIN.
import { createHash } from "node:crypto";
import { getStore } from "@netlify/blobs";

const STORE = "sv-portfolios";
const KEY = "data";
const EMPTY = JSON.stringify({ portfolios: [], updated: null });
const TOKEN_HASH = "8b9f12156d371010537f001e705adf0195e652b3a9965aa7fab4d476526e95c7";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Tracker-Token",
  "Content-Type": "application/json",
};

function sha256(value) {
  return createHash("sha256").update(String(value || ""), "utf8").digest("hex");
}

function tokenOk(provided, expected) {
  if (!provided) return false;
  if (expected) return provided === expected;
  return sha256(provided) === TOKEN_HASH;
}

export default async (req) => {
  if (req.method === "OPTIONS") return new Response("", { headers: CORS });

  let store;
  try {
    store = getStore(STORE);
  } catch (e) {
    return new Response(JSON.stringify({ error: "blobs_unavailable" }),
      { status: 500, headers: CORS });
  }

  try {
    if (req.method === "GET") {
      const data = await store.get(KEY);
      return new Response(data || EMPTY, { headers: CORS });
    }
    if (req.method === "POST") {
      // FIX BUG #a: token obbligatorio per scrittura
      const expectedToken = process.env.TRACKER_SYNC_TOKEN;
      const providedToken = req.headers.get("X-Tracker-Token");
      if (!tokenOk(providedToken, expectedToken)) {
        return new Response(JSON.stringify({ error: "unauthorized" }), { status: 401, headers: CORS });
      }
      const body = await req.text();
      if (!body || body.length > 2_000_000) {
        return new Response(JSON.stringify({ error: "bad_body" }),
          { status: 400, headers: CORS });
      }
      let parsed;
      try { parsed = JSON.parse(body); }
      catch { return new Response(JSON.stringify({ error: "not_json" }),
        { status: 400, headers: CORS }); }
      // PROTEZIONE ANTI-WIPE: rifiuta POST che svuota portfolios se cloud ne ha.
      // Override con header X-Allow-Wipe: 1 (solo se sai cosa stai facendo).
      if (!parsed || !Array.isArray(parsed.portfolios) || parsed.portfolios.length === 0) {
        const allow = req.headers.get("X-Allow-Wipe") === "1";
        if (!allow) {
          const cur = await store.get(KEY);
          if (cur) {
            try {
              const curObj = JSON.parse(cur);
              if (curObj.portfolios && curObj.portfolios.length > 0) {
                return new Response(JSON.stringify({
                  error: "wipe_refused",
                  hint: "Body vuoto ma cloud ha portafogli. Forza con X-Allow-Wipe: 1",
                }), { status: 409, headers: CORS });
              }
            } catch {}
          }
        }
      }
      await store.set(KEY, body);
      return new Response(JSON.stringify({ ok: true }), { headers: CORS });
    }
    return new Response(JSON.stringify({ error: "method_not_allowed" }),
      { status: 405, headers: CORS });
  } catch (e) {
    return new Response(JSON.stringify({ error: "server_error" }),
      { status: 500, headers: CORS });
  }
};

