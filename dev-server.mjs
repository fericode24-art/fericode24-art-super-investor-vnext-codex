import http from "node:http";
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const root = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const pub = path.join(root, "dashboard");
const localDir = path.join(root, ".local");
const port = Number(process.env.PORT || 5177);
const CHART = "https://query1.finance.yahoo.com/v8/finance/chart/";
const SEARCH = "https://query1.finance.yahoo.com/v1/finance/search";
const ISIN_RE = /^[A-Z]{2}[A-Z0-9]{9}[0-9]$/;
const QUOTE_TYPE = {
  EQUITY: "Azione", ETF: "ETF", MUTUALFUND: "Fondo",
  CRYPTOCURRENCY: "Crypto", INDEX: "Indice", CURRENCY: "Valuta",
};

await fs.mkdir(localDir, { recursive: true });

async function loadEnvFile(file) {
  try {
    const raw = await fs.readFile(file, "utf8");
    for (const line of raw.split(/\r?\n/)) {
      const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.+?)\s*$/i);
      if (!m || process.env[m[1]]) continue;
      process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
    }
  } catch {}
}
await loadEnvFile(path.join(root, ".env"));
await loadEnvFile(path.join(root, ".local", ".env"));
await loadEnvFile(path.join(root, "..", "super-investor-dashboard", ".env"));

function send(res, status, body, type = "application/json") {
  res.writeHead(status, { "Content-Type": type, "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET,POST,OPTIONS", "Access-Control-Allow-Headers": "Content-Type,X-Octa-Token,X-Tracker-Token,X-Octa-Expected-Updated" });
  res.end(body);
}
function json(res, status, obj) { send(res, status, JSON.stringify(obj)); }
async function readJson(name, fallback) {
  try { return JSON.parse(await fs.readFile(path.join(localDir, name), "utf8")); }
  catch { return fallback; }
}
async function writeJson(name, obj) { await fs.writeFile(path.join(localDir, name), JSON.stringify(obj, null, 2)); }
async function bodyText(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  return Buffer.concat(chunks).toString("utf8") || "{}";
}
async function bodyJson(req) {
  return JSON.parse(await bodyText(req));
}
async function fetchMeta(symbol) {
  try {
    const r = await fetch(CHART + encodeURIComponent(symbol) + "?interval=1d&range=1d", { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!r.ok) return null;
    const j = await r.json();
    return j?.chart?.result?.[0]?.meta || null;
  } catch { return null; }
}
async function resolveIsin(isin) {
  try {
    const r = await fetch(SEARCH + "?quotesCount=6&newsCount=0&q=" + encodeURIComponent(isin), { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!r.ok) return null;
    const j = await r.json();
    return (j.quotes || []).find(q => q.symbol)?.symbol || null;
  } catch { return null; }
}
async function quote(sym) {
  if (ISIN_RE.test(sym)) {
    const real = await resolveIsin(sym);
    if (real) sym = real;
  }
  for (const v of [sym, sym + ".DE", sym + ".MI"]) {
    const m = await fetchMeta(v);
    if (m?.regularMarketPrice != null) return { price: m.regularMarketPrice, currency: m.currency || "USD", resolved: v, prevClose: m.chartPreviousClose ?? null };
  }
  return null;
}
async function fetchHistoryFull(symbol, range = "1y") {
  try {
    let target = symbol;
    if (ISIN_RE.test(target)) target = (await resolveIsin(target)) || target;
    const query = range === "max"
      ? "?interval=1d&period1=0&period2=" + (Math.floor(Date.now() / 1000) + 86400)
      : "?interval=1d&range=" + range;
    const r = await fetch(CHART + encodeURIComponent(target) + query, { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!r.ok) return [];
    const j = await r.json();
    const res = j?.chart?.result?.[0];
    const ts = res?.timestamp || [];
    const cl = res?.indicators?.quote?.[0]?.close || [];
    const out = [];
    for (let i = 0; i < ts.length; i++) if (cl[i] != null) out.push([ts[i], Math.round(cl[i] * 100) / 100]);
    const meta = res?.meta || {};
    return { currency: meta.currency || "EUR", last: meta.regularMarketPrice ?? (out.length ? out[out.length - 1][1] : null), history: out, symbol: target };
  } catch { return { currency: "EUR", last: null, history: [], symbol }; }
}
async function fetchHistory(symbol, range = "1y") {
  return (await fetchHistoryFull(symbol, range)).history;
}
async function enrichInfo(sym) {
  try {
    const r = await fetch(SEARCH + "?quotesCount=5&newsCount=0&q=" + encodeURIComponent(sym), { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!r.ok) return null;
    const j = await r.json();
    const hit = (j.quotes || []).find(q => q.symbol);
    if (!hit) return null;
    const type = QUOTE_TYPE[(hit.quoteType || "").toUpperCase()] || "Altro";
    return { type, sector: hit.sector || type, name: hit.shortname || hit.longname || hit.symbol };
  } catch { return null; }
}
async function benchmark(sym) {
  let target = sym;
  if (ISIN_RE.test(target)) target = (await resolveIsin(target)) || target;
  const h = await fetchHistoryFull(target, "max");
  if (!h.history.length) return null;
  return { symbol: h.symbol, currency: h.currency, last: h.last, history: h.history };
}
async function routeFunction(req, res, url) {
  if (req.method === "OPTIONS") return send(res, 204, "", "text/plain");
  if (url.pathname.endsWith("/octa-portfolio")) {
    if (req.method === "GET") return json(res, 200, await readJson("octa-portfolio.json", { portfolio: {}, history: [], updated: null }));
    if (req.method === "POST") { const data = await bodyJson(req); data.updated ||= new Date().toISOString(); await writeJson("octa-portfolio.json", data); return json(res, 200, { ok: true, updated: data.updated }); }
  }
  if (url.pathname.endsWith("/portfolios")) {
    if (req.method === "GET") return json(res, 200, await readJson("portfolios.json", { portfolios: [], updated: null }));
    if (req.method === "POST") { const data = await bodyJson(req); data.updated ||= new Date().toISOString(); await writeJson("portfolios.json", data); return json(res, 200, { ok: true }); }
  }
  if (url.pathname.endsWith("/import-file") && req.method === "POST") {
    try {
      const { handler } = require(path.join(root, "netlify/functions/import-file.js"));
      const event = { httpMethod: "POST", headers: req.headers, body: await bodyText(req) };
      const out = await handler(event);
      return send(res, out.statusCode || 200, out.body || "{}", out.headers?.["Content-Type"] || "application/json");
    } catch (e) {
      return json(res, 500, { ok: false, error: String(e.message || e) });
    }
  }
  if (url.pathname.endsWith("/quotes") && req.method === "POST") {
    const data = await bodyJson(req);
    const symbols = [...new Set((data.symbols || []).map(s => String(s).trim().toUpperCase()).filter(Boolean))].slice(0, 60);
    const enrich = [...new Set((data.enrich || []).map(s => String(s).trim().toUpperCase()).filter(Boolean))].slice(0, 40);
    const histSymbols = [...new Set((data.priceHistory || []).map(s => String(s).trim().toUpperCase()).filter(Boolean))].slice(0, 25);
    const historyRange = String(data.historyRange || "max").replace(/[^0-9a-z]/gi, "") || "max";
    const bSym = data.benchmark ? String(data.benchmark).trim().toUpperCase() : "";
    const quotes = {}, priceHistory = {}, fxHistory = {}, info = {};
    await Promise.all(symbols.map(async s => { quotes[s] = await quote(s); }));
    await Promise.all(enrich.map(async s => { const e = await enrichInfo(s); if (e) info[s] = e; }));
    await Promise.all(histSymbols.map(async s => { priceHistory[s] = await fetchHistory(s, historyRange); }));
    const eur = await fetchMeta("EURUSD=X");
    if (data.fxHistory) fxHistory.EURUSD = await fetchHistory("EURUSD=X", historyRange);
    const bench = bSym ? await benchmark(bSym) : null;
    return json(res, 200, { quotes, fx: { EURUSD: eur?.regularMarketPrice || null }, fxHistory, info, priceHistory, bench });
  }
  if (url.pathname.endsWith("/vix-live")) {
    const m = await fetchMeta("^VIX");
    if (m?.regularMarketPrice != null) return json(res, 200, { vix: Math.round(m.regularMarketPrice * 10) / 10, ts: new Date().toISOString(), source: "yahoo" });
    return json(res, 500, { error: "vix_unavailable" });
  }
  if (url.pathname.endsWith("/ai") && req.method === "POST") {
    try {
      const { handler } = require(path.join(root, "netlify/functions/ai.js"));
      const event = { httpMethod: "POST", headers: req.headers, body: await bodyText(req) };
      const out = await handler(event);
      return send(res, out.statusCode || 200, out.body || "{}", out.headers?.["Content-Type"] || "application/json");
    } catch (e) {
      return json(res, 500, { error: String(e.message || e) });
    }
  }
  if (url.pathname.endsWith("/run-engines") && req.method === "POST") {
    return json(res, 501, { ok: false, error: "Run GitHub disponibile solo in deploy con GITHUB_ACTIONS_TOKEN." });
  }
  return json(res, 404, { error: "not_found" });
}
function mime(file) {
  const ext = path.extname(file).toLowerCase();
  return { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml" }[ext] || "application/octet-stream";
}
async function serveStatic(req, res, url) {
  let rel = decodeURIComponent(url.pathname.replace(/^\/+/, "")) || "index.html";
  if (rel.includes("..")) return send(res, 400, "bad path", "text/plain");
  let file = path.join(pub, rel);
  try {
    const st = await fs.stat(file);
    if (st.isDirectory()) file = path.join(file, "index.html");
    const data = await fs.readFile(file);
    send(res, 200, data, mime(file));
  } catch {
    send(res, 404, "not found", "text/plain");
  }
}
const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", `http://${req.headers.host}`);
    if (url.pathname.startsWith("/.netlify/functions/")) return routeFunction(req, res, url);
    return serveStatic(req, res, url);
  } catch (e) { json(res, 500, { error: String(e.message || e) }); }
});
server.listen(port, () => console.log(`Super Investor vNext: http://localhost:${port}`));

