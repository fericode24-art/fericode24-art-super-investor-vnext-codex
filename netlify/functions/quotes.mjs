// Netlify Function (v2) — quotazioni leggere per il tracker "Portafogli".
// Scarica SOLO i prezzi dei titoli richiesti: niente a che vedere col motore
// Radar (che gira per conto suo su GitHub Actions). Solo fetch, zero dipendenze.
//
//   POST { symbols: ["AAPL","VWCE",...], benchmark?: "SXR8.DE" }
//   → { quotes: { SYM: {price,currency,resolved} | null },
//       fx: { EURUSD },
//       bench: { symbol, currency, last, history: [[t,c],...] } | null }
//
// Per ogni simbolo prova le varianti: così com'è, .DE (XETRA), .MI (Borsa
// Italiana) — copre azioni USA, ETF su Fineco/XETRA e crypto (es. BTC-EUR).
// Se è indicato un benchmark, scarica anche la sua serie storica (3 anni)
// per il confronto andamento portafoglio vs indice.

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Content-Type": "application/json",
};
const CHART = "https://query1.finance.yahoo.com/v8/finance/chart/";
const SEARCH = "https://query1.finance.yahoo.com/v1/finance/search";
// ISIN: 2 lettere paese + 9 alfanumerici + 1 cifra di controllo (es. IE00BK5BQT80)
const ISIN_RE = /^[A-Z]{2}[A-Z0-9]{9}[0-9]$/;

async function fetchMeta(symbol) {
  try {
    const r = await fetch(CHART + encodeURIComponent(symbol) + "?interval=1d&range=1d",
      { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!r.ok) return null;
    const j = await r.json();
    return j?.chart?.result?.[0]?.meta || null;
  } catch { return null; }
}

// Risolve un ISIN nel ticker Yahoo corrispondente tramite l'endpoint di ricerca.
async function resolveIsin(isin) {
  try {
    const r = await fetch(SEARCH + "?quotesCount=6&newsCount=0&q=" + encodeURIComponent(isin),
      { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!r.ok) return null;
    const j = await r.json();
    const hit = (j.quotes || []).find(q => q.symbol);
    return hit ? hit.symbol : null;
  } catch { return null; }
}

// Costruisce la quotazione: prezzo, valuta, chiusura precedente (per la
// variazione di giornata) e simbolo Yahoo effettivamente usato.
function mkQuote(m, resolved) {
  return {
    price: m.regularMarketPrice,
    currency: m.currency || "USD",
    resolved,
    prevClose: m.chartPreviousClose ?? m.previousClose ?? null,
  };
}

// Fallback obbligazioni: Börse Frankfurt quota i titoli di Stato per ISIN,
// gratis e in JSON. Per le obbligazioni (nominal:true) il prezzo è in % del
// valore nominale → lo divido per 100 così combacia col modello del tracker.
const BF = "https://api.boerse-frankfurt.de/v1/data/quote_box/single";
async function bfQuote(isin) {
  try {
    const r = await fetch(BF + "?isin=" + encodeURIComponent(isin) + "&mic=XFRA",
      { headers: { "User-Agent": "Mozilla/5.0", "Accept": "application/json" } });
    if (!r.ok) return null;
    const j = await r.json();
    let p = j && j.lastPrice;
    if (p == null || !(p > 0)) return null;
    if (j.nominal === true) p = p / 100;
    return { price: p, currency: "EUR", resolved: isin };
  } catch { return null; }
}

async function quote(sym) {
  // Se è un ISIN, prima lo traduco in ticker Yahoo, poi prendo il prezzo.
  if (ISIN_RE.test(sym)) {
    const real = await resolveIsin(sym);
    if (real) {
      const m = await fetchMeta(real);
      if (m && m.regularMarketPrice != null) return mkQuote(m, real);
    }
    return await bfQuote(sym);            // fallback obbligazioni / titoli di Stato
  }
  for (const v of [sym, sym + ".DE", sym + ".MI"]) {
    const m = await fetchMeta(v);
    if (m && m.regularMarketPrice != null) return mkQuote(m, v);
  }
  return null;
}

// Arricchimento una tantum di uno strumento: tipo (azione/ETF/fondo/crypto),
// settore e nome leggibile. Usato per le allocazioni per tipo e per settore.
const QUOTE_TYPE = {
  EQUITY: "Azione", ETF: "ETF", MUTUALFUND: "Fondo",
  CRYPTOCURRENCY: "Crypto", INDEX: "Indice", CURRENCY: "Valuta",
};
async function enrichInfo(sym) {
  try {
    const r = await fetch(SEARCH + "?quotesCount=5&newsCount=0&q=" + encodeURIComponent(sym),
      { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!r.ok) return null;
    const j = await r.json();
    const hit = (j.quotes || []).find(q => q.symbol);
    if (!hit) return null;
    const type = QUOTE_TYPE[(hit.quoteType || "").toUpperCase()] || "Altro";
    // gli strumenti non azionari non hanno un settore: uso la categoria
    const sector = hit.sector || type;
    return { type, sector, name: hit.shortname || hit.longname || hit.symbol };
  } catch { return null; }
}

// Serie storica giornaliera. Default 3 anni per il confronto con un indice;
// per i grafici dei singoli titoli (Radar / dettaglio titolo) usiamo 5 anni.
async function fetchHistory(symbol, range = "3y") {
  try {
    const params = range === "max"
      ? "?interval=1d&period1=0&period2=" + Math.floor(Date.now() / 1000)
      : "?interval=1d&range=" + encodeURIComponent(range);
    const r = await fetch(CHART + encodeURIComponent(symbol) + params,
      { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!r.ok) return null;
    const j = await r.json();
    const res = j?.chart?.result?.[0];
    if (!res) return null;
    const ts = res.timestamp || [];
    const cl = res.indicators?.quote?.[0]?.close || [];
    const history = [];
    for (let i = 0; i < ts.length; i++)
      if (cl[i] != null) history.push([ts[i], Math.round(cl[i] * 100) / 100]);
    const meta = res.meta || {};
    return {
      currency: meta.currency || "EUR",
      last: meta.regularMarketPrice ?? (history.length ? history[history.length - 1][1] : null),
      history,
    };
  } catch { return null; }
}

async function benchmark(sym) {
  let real = sym;
  if (ISIN_RE.test(sym)) { real = await resolveIsin(sym); if (!real) return null; }
  const h = await fetchHistory(real);
  if (!h || !h.history.length) return null;
  return { symbol: real, currency: h.currency, last: h.last, history: h.history };
}

function cleanRange(value, fallback = "5y") {
  const allowed = new Set(["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]);
  const v = String(value || fallback).trim().toLowerCase();
  return allowed.has(v) ? v : fallback;
}

export default async (req) => {
  if (req.method === "OPTIONS") return new Response("", { headers: CORS });
  if (req.method !== "POST")
    return new Response(JSON.stringify({ error: "method_not_allowed" }),
      { status: 405, headers: CORS });
  try {
    const body = await req.json();
    const list = Array.isArray(body.symbols) ? body.symbols : [];
    const uniq = [...new Set(list.map(s => String(s).trim().toUpperCase()).filter(Boolean))]
      .slice(0, 60);                       // tetto leggero
    const bSym = body.benchmark ? String(body.benchmark).trim().toUpperCase() : "";
    const enrich = Array.isArray(body.enrich)
      ? [...new Set(body.enrich.map(s => String(s).trim().toUpperCase()).filter(Boolean))]
        .slice(0, 40)
      : [];
    // Lista di ticker per cui restituire lo storico prezzi (5y, giornaliero).
    // Usato dal Radar quando il pipeline non li include nel data.json.
    const phList = Array.isArray(body.priceHistory)
      ? [...new Set(body.priceHistory.map(s => String(s).trim().toUpperCase()).filter(Boolean))]
        .slice(0, 20)
      : [];
    const historyRange = cleanRange(body.historyRange, "5y");
    const wantsFxHistory = body.fxHistory === true;
    const quotes = {}, info = {}, priceHistory = {}, fxHistory = {};
    const [, fxMeta, fxHist, bench] = await Promise.all([
      Promise.all([
        ...uniq.map(async s => { quotes[s] = await quote(s); }),
        ...enrich.map(async s => { const e = await enrichInfo(s); if (e) info[s] = e; }),
        ...phList.map(async s => {
          // Per gli ISIN risolvo prima nel ticker Yahoo, altrimenti la chart
          // API risponderebbe vuoto. Per i ticker veri la passo cosi' com'e'.
          let target = s;
          if (ISIN_RE.test(s)) target = (await resolveIsin(s)) || s;
          const h = await fetchHistory(target, historyRange);
          if (h && h.history) priceHistory[s] = h.history;
        }),
      ]),
      fetchMeta("EURUSD=X"),
      wantsFxHistory ? fetchHistory("EURUSD=X", historyRange) : Promise.resolve(null),
      bSym ? benchmark(bSym) : Promise.resolve(null),
    ]);
    if (fxHist?.history?.length) fxHistory.EURUSD = fxHist.history;
    const fx = { EURUSD: fxMeta?.regularMarketPrice || null };
    return new Response(JSON.stringify({ quotes, fx, bench, info, priceHistory, fxHistory }),
      { headers: CORS });
  } catch {
    return new Response(JSON.stringify({ error: "server_error" }),
      { status: 500, headers: CORS });
  }
};
