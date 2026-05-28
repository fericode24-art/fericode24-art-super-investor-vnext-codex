// Netlify Function (v1 CJS) — VIX live on-demand per OCTA.
// Restituisce il valore corrente del VIX (Yahoo ^VIX) senza dipendenze esterne.
// Usato dalla sezione OCTA per mostrare regime di mercato sempre fresco.
// GET /api/vix-live → { vix: 16.42, ts: "2026-05-25T..." }

// FIX BUG #7: cache CDN 5 min (VIX cambia poco, riduce 50x le invocazioni)
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Content-Type": "application/json",
  "Cache-Control": "public, max-age=60, s-maxage=300, stale-while-revalidate=600",
  "Netlify-CDN-Cache-Control": "public, s-maxage=300, stale-while-revalidate=600",
};

const CHART = "https://query1.finance.yahoo.com/v8/finance/chart/^VIX?interval=1d&range=5d";

exports.handler = async function (event) {
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 204, headers: CORS, body: "" };
  }
  try {
    const r = await fetch(CHART, { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!r.ok) throw new Error("Yahoo HTTP " + r.status);
    const j = await r.json();
    const meta = j?.chart?.result?.[0]?.meta;
    const closes = j?.chart?.result?.[0]?.indicators?.quote?.[0]?.close || [];
    // Prendo l'ultimo valore non-null
    let last = meta?.regularMarketPrice;
    if (last == null) {
      for (let i = closes.length - 1; i >= 0; i--) {
        if (closes[i] != null) { last = closes[i]; break; }
      }
    }
    if (last == null) throw new Error("VIX value not found");
    return {
      statusCode: 200,
      headers: CORS,
      body: JSON.stringify({
        vix: Math.round(last * 10) / 10,
        ts: new Date().toISOString(),
        source: "yahoo",
      }),
    };
  } catch (e) {
    return {
      statusCode: 500,
      headers: CORS,
      body: JSON.stringify({ error: String(e.message || e) }),
    };
  }
};
