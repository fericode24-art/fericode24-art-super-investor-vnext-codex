// Netlify Function v1 (CommonJS) — importazione portafoglio da file Excel/PDF.
// Accetta POST JSON: { filename, dataBase64 }. Restituisce: { ok, rows }.
// Uso v1 (zip-and-ship) perché pdf-parse non è bundle-friendly con esbuild.
const crypto = require("node:crypto");
const XLSX = require("xlsx");
const pdfjs = require("pdfjs-dist/legacy/build/pdf.js");

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Tracker-Token",
  "Content-Type": "application/json",
};
const ok = (obj) => ({ statusCode: 200, headers: CORS, body: JSON.stringify(obj) });
const err = (code, obj) => ({ statusCode: code, headers: CORS, body: JSON.stringify(obj) });

const ISIN_RE = /\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b/;
const TRACKER_TOKEN_HASH = "8b9f12156d371010537f001e705adf0195e652b3a9965aa7fab4d476526e95c7";

function sha256(value) {
  return crypto.createHash("sha256").update(String(value || ""), "utf8").digest("hex");
}

function tokenOk(provided, expected) {
  if (!provided) return false;
  if (expected) return provided === expected;
  return sha256(provided) === TRACKER_TOKEN_HASH;
}

// Parse di un numero in formato europeo:
//   "1.234,56" → 1234.56     (migliaia + decimali)
//   "58.000"   → 58000       (intero con separatore migliaia all'italiana)
//   "86,2774"  → 86.2774
//   "1234.56"  → 1234.56     (anglosassone)
function num(s) {
  if (s == null) return NaN;
  if (typeof s === "number") return s;
  let str = String(s).trim().replace(/\s|€|\$|%/g, "");
  if (/,/.test(str) && /\.\d{3}/.test(str)) {
    // 1.234,56 — punti come migliaia, virgola come decimale
    str = str.replace(/\./g, "").replace(",", ".");
  } else if (/^-?\d{1,3}(\.\d{3})+$/.test(str)) {
    // 58.000 / 1.050 / 1.234.567 — intero italiano (punti come migliaia)
    str = str.replace(/\./g, "");
  } else if (/,/.test(str)) {
    // 86,2774
    str = str.replace(",", ".");
  }
  const n = parseFloat(str);
  return isNaN(n) ? NaN : n;
}

function mapType(s) {
  s = String(s || "").trim().toLowerCase();
  if (s.includes("etf")) return "ETF";
  if (s.includes("etc") || s.includes("etn") || s.includes("etp")) return "ETC";
  if (s.includes("fond") || s.includes("sicav") || s.includes("monetar")) return "Fondo";
  if (s.includes("azion") || s.includes("stock") || s.includes("equity")) return "Azione";
  if (s.includes("titoli di stato") || s.includes("obbligaz") || s.includes("bond")) return "Obbligazione";
  if (s.includes("crypto") || s.includes("bitcoin")) return "Crypto";
  return s ? s[0].toUpperCase() + s.slice(1) : "Altro";
}

function parseExcel(buf) {
  const wb = XLSX.read(buf, { type: "buffer" });
  const out = [];
  for (const name of wb.SheetNames) {
    const sheet = wb.Sheets[name];
    const aoa = XLSX.utils.sheet_to_json(sheet, { header: 1, raw: true, defval: null });
    let hi = -1;
    for (let i = 0; i < aoa.length; i++) {
      if (aoa[i] && aoa[i].some(c => String(c || "").toUpperCase().trim() === "ISIN")) {
        hi = i; break;
      }
    }
    if (hi < 0) continue;
    const hd = aoa[hi].map(c => String(c || "").trim().toLowerCase());
    const find = (preds) => {
      for (let i = 0; i < hd.length; i++)
        if (preds.some(p => p(hd[i]))) return i;
      return -1;
    };
    const idxIsin = find([h => h === "isin"]);
    const idxQty = find([h => h.startsWith("quantit") || h === "q.tà" || h === "qta" || h === "numero quote"]);
    const idxName = find([h => h === "titolo" || h === "descrizione" || h === "nome"]);
    const idxType = find([h => h === "strumento" || h === "tipo"]);
    const idxValCarico = find([h => h.includes("valore di carico") || h.includes("valore carico") || h.includes("controvalore di carico")]);
    const idxPriceCarico = find([h => h.includes("prezzo medio") || h.includes("p.zo medio") || h.includes("medio fiscale") || h.includes("valore quota di carico")]);
    const idxValCur = find([h => h.includes("valore di mercato") || h.includes("valore ultima") || (h.includes("controvalore") && !h.includes("carico"))]);
    if (idxIsin < 0 || idxQty < 0) continue;

    for (let i = hi + 1; i < aoa.length; i++) {
      const r = aoa[i];
      if (!r) continue;
      const isin = String(r[idxIsin] || "").trim().toUpperCase();
      if (!/^[A-Z]{2}[A-Z0-9]{9}[0-9]$/.test(isin)) continue;
      const qty = num(r[idxQty]);
      if (!(qty > 0)) continue;
      const valCarico = idxValCarico >= 0 ? num(r[idxValCarico]) : NaN;
      const priceCarico = idxPriceCarico >= 0 ? num(r[idxPriceCarico]) : NaN;
      const price = (!isNaN(valCarico) && valCarico > 0) ? valCarico / qty : priceCarico;
      if (!(price >= 0)) continue;
      const type = idxType >= 0 ? mapType(r[idxType]) : "Altro";
      const name = idxName >= 0 ? String(r[idxName] || "").trim() : "";
      let manualPrice;
      if (type === "Fondo" || type === "Obbligazione") {
        const vc = idxValCur >= 0 ? num(r[idxValCur]) : NaN;
        if (!isNaN(vc) && vc > 0 && qty > 0) manualPrice = vc / qty;
      }
      out.push({ symbol: isin, name: name || isin,
        quantity: qty, price, type, sector: type, manualPrice });
    }
  }
  return out;
}

// PDF: estrazione con pdfjs-dist usando le posizioni X/Y dei testi per
// ricostruire le righe delle tabelle (pdf-parse fonde le celle).
async function parsePdf(buf) {
  const data = new Uint8Array(buf);
  const doc = await pdfjs.getDocument({ data, disableFontFace: true, useSystemFonts: false }).promise;
  // Raggruppa tutti gli item per pagina e Y (con tolleranza ±2).
  // Tengo le righe in ordine di lettura (alto→basso, sinistra→destra).
  const rows = [];                            // [{page, y, cells: [{x,str}]}]
  for (let p = 1; p <= doc.numPages; p++) {
    const page = await doc.getPage(p);
    const tc = await page.getTextContent();
    const pageRows = {};
    for (const it of tc.items) {
      const y = Math.round(it.transform[5]);
      if (!pageRows[y]) pageRows[y] = [];
      pageRows[y].push({ x: it.transform[4], str: it.str });
    }
    const ys = Object.keys(pageRows).map(Number).sort((a, b) => b - a);
    for (const y of ys) {
      const cells = pageRows[y].sort((a, b) => a.x - b.x)
        .map(c => c.str.trim()).filter(Boolean);
      if (!cells.length) continue;
      rows.push({ page: p, y, cells });
    }
  }
  // Per ogni riga con ISIN, parsa le celle.
  const TYPE_MAP = [
    [/totale fondi|totale sicav/i, "Fondo"],
    [/totale azion/i, "Azione"],
    [/totale etf\b/i, "ETF"],
    [/totale etc|totale etn/i, "ETC"],
    [/totale titoli di stato|totale obbligaz/i, "Obbligazione"],
  ];
  const out = [];
  let pending = [];

  const flushAs = (t) => {
    for (const r of pending) {
      r.type = t;
      r.sector = t;
      if (t === "Fondo" && r._ultima != null) r.manualPrice = r._ultima;
      delete r._ultima;
    }
    out.push(...pending);
    pending = [];
  };

  for (let idx = 0; idx < rows.length; idx++) {
    const row = rows[idx];
    const joined = row.cells.join(" ");
    // È una riga "Totale ..." → chiudi le pending col tipo.
    let matched = false;
    for (const [re, t] of TYPE_MAP) {
      if (re.test(joined)) { flushAs(t); matched = true; break; }
    }
    if (matched) continue;
    // Cerca un ISIN tra le celle.
    let isinCellIdx = -1, isin = null;
    for (let i = 0; i < row.cells.length; i++) {
      const m = row.cells[i].match(/^[A-Z]{2}[A-Z0-9]{9}[0-9]$/);
      if (m) { isinCellIdx = i; isin = row.cells[i]; break; }
    }
    if (!isin) continue;
    // Nome: celle prima dell'ISIN (caso azioni/obbligazioni). Se vuoto, il
    // nome sta su una riga separata molto vicina (caso fondi); preferisco
    // quella IMMEDIATAMENTE sotto (delta y piccolo) per evitare gli header.
    const HEADER_RE = /var\.|prezzo|controvalore|isin|descrizione|quota|totale|utile|perdit|carico|fiscale|mercato|data|valuta|cambio|simbolo|strumento|titolo|rateo/i;
    const isNameLike = (txt) =>
      txt && !/\d/.test(txt)
        && !/^[A-Z]{2}[A-Z0-9]{9}[0-9]$/.test(txt)
        && !HEADER_RE.test(txt);
    const before = row.cells.slice(0, isinCellIdx).join(" ").trim();
    let name = isNameLike(before) ? before : "";
    if (!name) {
      // riga molto vicina sotto
      for (let k = idx + 1; k < rows.length; k++) {
        const nb = rows[k];
        if (nb.page !== row.page) break;
        if (Math.abs(row.y - nb.y) > 6) break;
        const txt = nb.cells.join(" ").trim();
        if (isNameLike(txt)) { name = txt; break; }
      }
    }
    if (!name) name = before || isin;
    // Numeri: dalle celle dopo l'ISIN, escludendo date/orari/percentuali pure.
    const after = row.cells.slice(isinCellIdx + 1);
    const nums = [];
    for (const cell of after) {
      // scarta date dd.mm.yyyy e orari hh.mm.ss
      if (/^\d{1,2}\.\d{1,2}\.\d{4}$/.test(cell)) continue;
      if (/^\d{1,2}[:.]\d{2}([:.]\d{2})?$/.test(cell)) continue;
      const n = num(cell);
      if (!isNaN(n)) nums.push(n);
    }
    if (nums.length < 2) continue;
    const qty = nums[0];
    if (!(qty > 0)) continue;
    const cvCarico = nums.length >= 3 ? nums[nums.length - 2] : null;
    const price = (cvCarico != null && qty > 0) ? cvCarico / qty : nums[1];
    const ultima = nums.length >= 3 ? nums[2] : null;
    pending.push({
      symbol: isin, name: name || isin,
      quantity: qty, price, type: "Altro", sector: "Altro",
      _ultima: ultima,
    });
  }
  if (pending.length) {
    for (const r of pending) { r.type = "Altro"; r.sector = "Altro"; delete r._ultima; }
    out.push(...pending);
  }
  return out;
}

exports.handler = async (event) => {
  if (event.httpMethod === "OPTIONS") return { statusCode: 200, headers: CORS, body: "" };
  if (event.httpMethod !== "POST") return err(405, { ok: false, error: "method_not_allowed" });
  // FIX BUG #b (round 4): auth token + size limit + parsing isolato per
  // mitigare CVE xlsx/pdfjs (file malformati = DoS o RCE potenziale).
  const expectedToken = process.env.TRACKER_SYNC_TOKEN;
  const providedToken = event.headers["x-tracker-token"] || event.headers["X-Tracker-Token"];
  if (!tokenOk(providedToken, expectedToken)) {
    return err(401, { ok: false, error: "unauthorized" });
  }
  try {
    const body = JSON.parse(event.body || "{}");
    const filename = String(body.filename || "").toLowerCase();
    const dataB64 = body.dataBase64 || "";
    if (!dataB64) throw new Error("file vuoto");
    // Hard cap 5MB sul base64 (~3.7MB binari) per evitare DoS
    if (dataB64.length > 5_000_000) throw new Error("file troppo grande (>5MB)");
    const buf = Buffer.from(dataB64, "base64");
    const isPdf = filename.endsWith(".pdf") || buf.slice(0, 4).toString() === "%PDF";
    const rows = isPdf ? await parsePdf(buf) : parseExcel(buf);
    for (const r of rows) if (r.manualPrice == null) delete r.manualPrice;
    return ok({ ok: true, rows, source: isPdf ? "pdf" : "excel" });
  } catch (e) {
    return err(500, { ok: false, error: e.message });
  }
};
