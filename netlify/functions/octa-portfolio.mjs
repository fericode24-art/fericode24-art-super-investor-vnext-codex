// Netlify Function (v2) â€” store portfolio OCTA condiviso app â†” runner.
// Senza PIN (OCTA Ã¨ un portafoglio dedicato, no cifratura client-side).
// Protezione minima: token statico in env var OCTA_SYNC_TOKEN, verificato
// nell'header X-Octa-Token. Il workflow Python GitHub Actions lo legge
// dai GitHub secrets.
//
//   GET  /.netlify/functions/octa-portfolio   â†’ { portfolio, history, updated }
//   POST /.netlify/functions/octa-portfolio   â†’ salva JSON nel body
//
// Header X-Octa-Token obbligatorio per POST (lettura libera).

import { createHash } from "node:crypto";
import { getStore } from "@netlify/blobs";

const STORE = "octa-portfolio";
const KEY = "state";
const EMPTY = JSON.stringify({ portfolio: {}, history: [], updated: null });
const TOKEN_HASH = "44b50c26e784fceb4a0741c5cac60fc24e0ed231513df99f9b039d9aaeafe8f0";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Octa-Token, X-Octa-Expected-Updated",
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
      // Verifica token per scrittura
      const expectedToken = process.env.OCTA_SYNC_TOKEN;
      const providedToken = req.headers.get("X-Octa-Token");
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

      // FIX BUG #5: optimistic locking. Il client puÃ² inviare header
      // X-Octa-Expected-Updated col timestamp che si aspetta sia nel cloud.
      // Se diverso â†’ 409 Conflict (qualcun altro ha scritto nel frattempo).
      const expectedUpdated = req.headers.get("X-Octa-Expected-Updated");
      if (expectedUpdated) {
        const cur = await store.get(KEY);
        if (cur) {
          try {
            const curObj = JSON.parse(cur);
            const curUpdated = curObj.updated || null;
            if (curUpdated && curUpdated !== expectedUpdated) {
              return new Response(JSON.stringify({
                error: "conflict",
                current_updated: curUpdated,
                expected_updated: expectedUpdated,
                hint: "Il cloud Ã¨ stato modificato dopo il tuo ultimo pull. " +
                      "Rifai pull e ri-applica le modifiche.",
              }), { status: 409, headers: CORS });
            }
          } catch { /* cur non parsabile, lascia passare write */ }
        }
      }
      await store.set(KEY, body);
      return new Response(JSON.stringify({ ok: true,
        updated: parsed.updated || new Date().toISOString() }),
        { headers: CORS });
    }
    return new Response(JSON.stringify({ error: "method_not_allowed" }),
      { status: 405, headers: CORS });
  } catch (e) {
    return new Response(JSON.stringify({ error: "server_error", detail: String(e.message || e) }),
      { status: 500, headers: CORS });
  }
};


