(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const LS = {
    view: "si_vnext_view",
    octaPortfolio: "si_vnext_octa_portfolio",
    octaHistory: "si_vnext_octa_history",
    octaExecuted: "si_vnext_octa_executed",
    apexExecuted: "si_vnext_apex_executed",
    apexHistory: "si_vnext_apex_history",
    octaCloudTs: "si_vnext_octa_cloud_ts",
    trackerCache: "si_vnext_tracker_cache",
    trackerOpen: "si_vnext_tracker_open",
    chartRanges: "si_vnext_chart_ranges",
    apexHistoryOpen: "si_vnext_apex_history_open",
  };
  const params = new URLSearchParams(location.search);
  if (params.get("repair") === "1") {
    repairLocalState();
    params.delete("repair");
    const clean = params.toString();
    history.replaceState(null, "", `${location.pathname}${clean ? "?" + clean : ""}`);
  }
  const API = {
    octa: "/.netlify/functions/octa-portfolio",
    portfolios: "/.netlify/functions/portfolios",
    quotes: "/.netlify/functions/quotes",
    ai: "/.netlify/functions/ai",
    vix: "/.netlify/functions/vix-live",
    importFile: "/.netlify/functions/import-file",
    runEngines: "/.netlify/functions/run-engines",
  };
  const HOLIDAYS = new Set([
    "2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25","2026-06-19","2026-07-03","2026-09-07","2026-11-26","2026-12-25",
    "2027-01-01","2027-01-18","2027-02-15","2027-03-26","2027-05-31","2027-06-18","2027-07-05","2027-09-06","2027-11-25","2027-12-24",
    "2028-01-17","2028-02-21","2028-04-14","2028-05-29","2028-06-19","2028-07-04","2028-09-04","2028-11-23","2028-12-25",
    "2029-01-01","2029-01-15","2029-02-19","2029-03-30","2029-05-28","2029-06-19","2029-07-04","2029-09-03","2029-11-22","2029-12-25",
    "2030-01-01","2030-01-21","2030-02-18","2030-04-19","2030-05-27","2030-06-19","2030-07-04","2030-09-02","2030-11-28","2030-12-25"
  ]);
  const COLORS = ["#42d392", "#67d6e8", "#f1bd5b", "#b9a0ff", "#ff8a65", "#83a8ff", "#ff6b6b", "#9be564"];
  const TARGET_WEIGHTS = {
    "fede smart": {
      description: "Allocazione target da rispettare e ribilanciare se uno strumento esce dalla banda.",
      bandTolerancePct: 2,
      items: [
        { code: "IWMO", matchAny: ["IS3R.DE", "IE00BP3QZ825"], name: "iShares Edge MSCI World Momentum", weight: 18 },
        { code: "IQGA", matchAny: ["IQGA.DE", "IE000TZ4SIN6"], name: "Invesco Global Enhanced Equity", weight: 18 },
        { code: "SGLN", matchAny: ["PPFB.DE", "IE00B4ND3602"], name: "iShares Physical Gold", weight: 14 },
        { code: "CL2", matchAny: ["CL2.PA", "FR0010755611"], name: "Amundi MSCI USA Daily 2x Leveraged", weight: 12 },
        { code: "BITC", matchAny: ["IB1T.DE", "XS2940466316"], name: "iShares Bitcoin ETP", weight: 10 },
        { code: "DBMF", matchAny: ["DBMFE.PA", "LU2951555403"], name: "iMGP DBi Managed Futures", weight: 10 },
        { code: "IQMA", matchAny: ["MHQA.DE", "IE000U07IGB1"], name: "Invesco EM Enhanced Equity", weight: 6 },
        { code: "VAGF", matchAny: ["VAGF.DE", "IE00BG47KH54"], name: "Vanguard Global Aggregate Bond", weight: 6 },
        { code: "FLESA", matchAny: ["FVSA.DE", "IE000STIHQB2"], name: "Franklin Euro Short Maturity", weight: 6 },
      ],
    },
  };

  const state = {
    view: params.get("view") || localStorage.getItem(LS.view) || "today",
    octaData: null,
    octaArchive: null,
    legacyData: null,
    freshnessFile: null,
    octaPortfolio: loadJson(LS.octaPortfolio, {}),
    octaHistory: loadJson(LS.octaHistory, []),
    octaExecuted: loadJson(LS.octaExecuted, {}),
    apexData: null,
    vixData: null,
    apexExecuted: loadJson(LS.apexExecuted, {}),
    apexHistory: loadJson(LS.apexHistory, []),
    apexFocus: params.get("apex") || null,
    tracker: { portfolios: [], updated: null },
    openPf: null,
    quotes: {},
    priceHistory: {},
    fx: {},
    fxHistory: {},
    priceHistoryRange: {},
    info: {},
    sync: { octa: "local", portfolios: "local", msg: "" },
    pendingTrade: null,
    pendingApexExec: null,
    pendingOpenPf: null,
    pendingImportRows: [],
    radarOpen: false,
    apexHistoryOpen: loadJson(LS.apexHistoryOpen, {}),
    allocView: "symbol",
    detailTicker: null,
    detailHolding: null,
    chartRanges: loadJson(LS.chartRanges, {}),
  };
  const CHART_RANGES = [
    ["1D", "1G", 1],
    ["1W", "1S", 7],
    ["1M", "1M", 31],
    ["3M", "3M", 93],
    ["1Y", "1A", 366],
    ["5Y", "5A", 366 * 5],
    ["MAX", "Max", null],
  ];
  const CLOUD_RUNNER = {
    name: "GitHub Actions",
    deploy: "Netlify vNext",
    schedule: "08:35/08:45/08:55 Italia lun-ven",
    check: "08:57 Italia",
    site: "https://super-investor-vnext-codex.netlify.app",
    repo: "https://github.com/fericode24-art/fericode24-art-super-investor-vnext-codex/actions",
    workflow: "https://github.com/fericode24-art/fericode24-art-super-investor-vnext-codex/actions/workflows/octa-vnext-refresh.yml",
  };
  const MARKET_WATCH = [
    { symbol: "^GSPC", label: "S&P 500" },
    { symbol: "BTC-USD", label: "Bitcoin" },
    { symbol: "GC=F", label: "Oro" },
  ];
  const STATUS_INFO = {
    FRESH_BREAKOUT: { label: "Compra: breakout", cls: "good", desc: "Il prezzo sta rompendo verso l'alto: il motore lo considera comprabile se resta alto in classifica." },
    PULLBACK_IN_TREND: { label: "Compra: ritracciamento", cls: "good", desc: "Il trend e ancora buono, ma il prezzo ha respirato: ingresso piu ordinato rispetto a comprare sui massimi." },
    NEUTRAL: { label: "Compra: ok", cls: "good", desc: "Non ci sono divieti tecnici: si compra solo se score e portafoglio lo richiedono." },
    CONSOLIDATION: { label: "Aspetta: laterale", cls: "warn", desc: "Il titolo e in una fase laterale: meglio aspettare una rottura piu chiara." },
    EXTENDED: { label: "Aspetta: tirato", cls: "warn", desc: "Il prezzo e gia salito molto: il rischio e comprare troppo tardi." },
    BROKEN: { label: "Vendi: trend rotto", cls: "bad", desc: "Il trend tecnico si e rotto: il motore segnala uscita o forte prudenza." },
    AVOID: { label: "Evita: rischio alto", cls: "bad", desc: "Il motore vede troppi rischi o un veto tecnico: non e un candidato operativo." },
    ROTATION_OUT: { label: "Vendi: sostituito", cls: "warn", desc: "Il titolo esce perche oggi ci sono candidati migliori nella rotazione." },
  };
  const SCORE_TIPS = {
    radar: "Quanto il titolo e presente nei fondi osservati e se stanno aumentando esposizione.",
    entry: "Dice se il prezzo e in un punto sensato per comprare o se e meglio aspettare.",
    opp: "La priorita finale nella lista OCTA: piu e alto, piu il titolo e interessante oggi.",
    momentum: "Quanto il titolo sta correndo rispetto agli altri.",
    insider: "Segnali extra di supporto, usati solo quando il motore li abilita.",
    funds: "Quanti fondi osservati hanno questo titolo in portafoglio.",
  };
  const LIVE_SIGNAL_PROFILE = {
    active: [
      ["Fondi", "Presenza e accumulo nei fondi osservati"],
      ["Forza", "Quanto il titolo corre rispetto agli altri"],
      ["Ingresso tecnico", "Breakout, ritracciamento, laterale o trend rotto"],
      ["VIX e optimizer", "Regime, 8 slot, settore, anti-churn"],
    ],
    inactive: [
      ["Insider Form 4", "Cache/prefetch presente, peso zero nel live"],
      ["Earnings / PEAD", "Cache/prefetch presente, peso zero nel live"],
      ["Analyst", "Codice/provider previsto, non pesato nel live"],
      ["Congressional / squeeze", "Shadow test: visibile prima del peso live"],
    ],
  };
  const chartStore = new Map();

  function loadJson(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key) || "") || fallback; }
    catch { return fallback; }
  }
  function saveJson(key, val) { localStorage.setItem(key, JSON.stringify(val)); }
  function esc(v) { return String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }
  function eur(n, dec = 0) { return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: dec }).format(Number(n || 0)); }
  function eurMaybe(n, dec = 0) { return Number.isFinite(Number(n)) ? eur(Number(n), dec) : "n/d"; }
  function compactEur(n) {
    const x = Number(n || 0), a = Math.abs(x);
    if (a >= 1000000) return `€${(x / 1000000).toFixed(a >= 10000000 ? 0 : 1)}M`;
    if (a >= 1000) return `€${(x / 1000).toFixed(a >= 10000 ? 0 : 1)}k`;
    return eur(x, 0);
  }
  function pct(n, dec = 1) { const x = Number(n || 0); return (x >= 0 ? "+" : "") + x.toFixed(dec) + "%"; }
  function pctWeight(n, dec = 1) { return Number(n || 0).toFixed(dec) + "%"; }
  function todayISO() { return new Date().toISOString().slice(0, 10); }
  function dateIT(s) { if (!s) return "n/d"; const [y,m,d] = String(s).slice(0,10).split("-"); return d && m && y ? `${d}/${m}/${y}` : String(s); }
  function timeIT(s) { if (!s) return "n/d"; try { return new Date(s).toLocaleString("it-IT", { day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit" }); } catch { return s; } }
  function localISO(d) {
    const x = d instanceof Date ? d : new Date(d);
    const y = x.getFullYear();
    const m = String(x.getMonth() + 1).padStart(2, "0");
    const day = String(x.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }
  function hhmm(d) {
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  }
  function toast(msg) { const t = document.createElement("div"); t.className = "toast"; t.textContent = msg; document.body.appendChild(t); setTimeout(() => t.remove(), 3600); }
  function repairLocalState() {
    Object.values(LS).forEach(k => localStorage.removeItem(k));
    Object.keys(localStorage).filter(k => k.startsWith("si_vnext_")).forEach(k => localStorage.removeItem(k));
    if ("caches" in window) caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith("super-investor-vnext")).map(k => caches.delete(k)))).catch(() => {});
    if ("serviceWorker" in navigator) navigator.serviceWorker.getRegistrations().then(regs => Promise.all(regs.map(r => r.unregister()))).catch(() => {});
  }
  function repairAndReload(view = state.view || "today") {
    repairLocalState();
    location.href = `/?repair=1&view=${encodeURIComponent(view)}&v=22`;
  }
  function fxRate() {
    const x = Number(state.fx?.EURUSD);
    return Number.isFinite(x) && x > 0 ? x : null;
  }
  function fxAtDate(d, fallback) {
    const hist = state.fxHistory?.EURUSD || [];
    const day = String(d || todayISO()).slice(0, 10);
    let best = null;
    for (const row of hist) {
      const ts = Array.isArray(row) ? row[0] : row.t;
      const val = Number(Array.isArray(row) ? row[1] : row.c);
      if (!Number.isFinite(val) || val <= 0) continue;
      const rd = new Date(Number(ts) * 1000).toISOString().slice(0, 10);
      if (rd <= day) best = val;
      else break;
    }
    return best || fallback || fxRate();
  }
  function toEur(value, currency, fx) {
    const n = Number(value);
    if (!Number.isFinite(n)) return null;
    const rawCur = String(currency || "EUR");
    const cur = rawCur.toUpperCase();
    if (cur === "EUR") return n;
    if (cur === "USD") {
      const rate = Number(fx || fxRate());
      return rate > 0 ? n / rate : null;
    }
    if (cur === "GBX" || rawCur === "GBp") return n / 100;
    return null;
  }
  function quoteUnitEur(symbol) {
    const q = state.quotes[String(symbol || "").toUpperCase()];
    if (!q || q.price == null) return null;
    return toEur(q.price, q.currency, fxRate());
  }
  function octaEntryCostEur(pos) {
    const cost = Number(pos?.cost_total);
    if (Number.isFinite(cost) && cost > 0) return cost;
    const shares = Number(pos?.shares || 0);
    const px = Number(pos?.entry_price || 0);
    const comm = Number(pos?.comm || 0);
    const rate = Number(pos?.fx || fxRate());
    return shares && px && rate ? shares * px / rate + comm : 0;
  }
  function octaEntryUnitEur(pos) {
    const shares = Number(pos?.shares || 0);
    const cost = octaEntryCostEur(pos);
    if (shares && cost) return cost / shares;
    const rate = Number(pos?.fx || fxRate());
    return Number(pos?.entry_price || 0) && rate ? Number(pos.entry_price) / rate : null;
  }
  function octaLiveUnitEur(ticker, pos) {
    const live = quoteUnitEur(ticker);
    if (live != null) return live;
    return octaEntryUnitEur(pos);
  }
  function icon(name) {
    const map = {
      check: '<svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></svg>',
      plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14"/><path d="M5 12h14"/></svg>',
      play: '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>',
      lock: '<svg viewBox="0 0 24 24"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>',
      cloud: '<svg viewBox="0 0 24 24"><path d="M17.5 19H8a5 5 0 1 1 1-9.9A6.5 6.5 0 0 1 21 12.5 3.5 3.5 0 0 1 17.5 19z"/></svg>',
      brain: '<svg viewBox="0 0 24 24"><path d="M9 3a4 4 0 0 0-4 4v.5A4.5 4.5 0 0 0 6 16v1a4 4 0 0 0 7 2.6"/><path d="M15 3a4 4 0 0 1 4 4v.5A4.5 4.5 0 0 1 18 16v1a4 4 0 0 1-7 2.6"/><path d="M12 4v16"/></svg>',
      chart: '<svg viewBox="0 0 24 24"><path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 15l4-5 3 3 5-7"/></svg>',
      refresh: '<svg viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-2.6-6.4"/><path d="M21 3v6h-6"/></svg>',
      edit: '<svg viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
      trash: '<svg viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>',
      upload: '<svg viewBox="0 0 24 24"><path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M4 20h16"/></svg>',
      minus: '<svg viewBox="0 0 24 24"><path d="M5 12h14"/></svg>',
    };
    return map[name] || "";
  }

  function isTradingDay(d) {
    const day = d.getDay();
    const iso = d.toISOString().slice(0, 10);
    return day !== 0 && day !== 6 && !HOLIDAYS.has(iso);
  }
  function isScheduledRefreshDay(d) {
    const day = d.getDay();
    return day !== 0 && day !== 6 && !HOLIDAYS.has(localISO(d));
  }
  function nextRefreshInfo() {
    const now = new Date();
    const target = new Date(now);
    target.setHours(8, 35, 0, 0);
    while (now > target || !isScheduledRefreshDay(target)) {
      target.setDate(target.getDate() + 1);
      target.setHours(8, 35, 0, 0);
    }
    return {
      label: `${localISO(target) === localISO(now) ? "oggi" : dateIT(localISO(target))} ${hhmm(target)}`,
      iso: localISO(target),
    };
  }
  function previousTradingDay(d) {
    const x = new Date(d);
    do { x.setDate(x.getDate() - 1); } while (!isTradingDay(x));
    return x.toISOString().slice(0, 10);
  }
  function expectedSignalDate() {
    const now = new Date();
    const minutes = now.getHours() * 60 + now.getMinutes();
    if (isTradingDay(now) && minutes >= 8 * 60 + 35) return now.toISOString().slice(0, 10);
    return previousTradingDay(now);
  }
  function freshness() {
    const sig = state.octaData?.signal_date || state.octaData?.last_success_run || null;
    const expected = expectedSignalDate();
    const wf = state.freshnessFile;
    if (wf && wf.expected_signal_date === expected && wf.fresh === false) {
      return { cls: "bad", label: "Workflow stale", detail: `Workflow ${timeIT(wf.generated_at)}. Segnale ${dateIT(wf.signal_date)}. Atteso ${dateIT(expected)}` };
    }
    if (!sig) return { cls: "bad", label: "Segnale assente", detail: `Atteso ${dateIT(expected)}` };
    if (sig >= expected) {
      const run = wf?.generated_at ? ` · check ${timeIT(wf.generated_at)}` : "";
      return { cls: "good", label: "Segnale fresco", detail: `Segnale ${dateIT(sig)}. Atteso ${dateIT(expected)}${run}` };
    }
    return { cls: "bad", label: "Segnale vecchio", detail: `Segnale ${dateIT(sig)}. Atteso ${dateIT(expected)}` };
  }
  function liveExternalProfile() {
    const sample = (state.octaData?.candidates || []).find(c => c?.components) || (state.octaData?.signals || []).find(s => s?.components) || {};
    const mode = state.octaData?.external_signal_mode || sample.components?.external_signal_mode || sample.external_signal_mode || "off";
    if (mode === "cached") {
      return {
        cls: "good",
        label: "Esterni pesati live",
        detail: "Profilo cached validato: insider, analyst e PEAD entrano nello score quando la cache li copre.",
      };
    }
    if (mode === "full") {
      return {
        cls: "good",
        label: "Esterni full live",
        detail: "Il motore puo usare provider esterni live oltre alla cache.",
      };
    }
    if (sample.components?.skip_external === true || mode === "off") {
      return {
        cls: "warn",
        label: "Esterni in test",
        detail: "Il file corrente non li pesa ancora nel live; il profilo cached va attivato solo dopo test passati.",
      };
    }
    return {
      cls: "info",
      label: "Esterni n/d",
      detail: "Il dataset corrente non dichiara il profilo esterni.",
    };
  }

  async function init() {
    wireShell();
    await Promise.all([loadOctaData(), loadApexData(), loadVixData(), loadLegacyData(), loadTrackerCloud()]);
    await pullOctaCloud();
    render();
    refreshQuotes().then(render).catch(() => {});
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("./sw.js").catch(() => {});
  }
  async function loadOctaData() {
    try {
      const r = await fetch("data-octa.json?t=" + Date.now(), { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      state.octaData = await r.json();
    } catch (e) {
      state.octaData = { signals: [], candidates: [], regime: {}, engine_error: true, error_detail: String(e.message || e) };
    }
    await loadFreshnessStatus();
  }
  async function loadFreshnessStatus() {
    try {
      const r = await fetch("freshness.json?t=" + Date.now(), { cache: "no-store" });
      state.freshnessFile = r.ok ? await r.json() : null;
    } catch {
      state.freshnessFile = null;
    }
  }
  async function loadApexData() {
    try {
      const r = await fetch("apex-data.json?t=" + Date.now(), { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      state.apexData = await r.json();
    } catch (e) {
      state.apexData = { status: "error", error: String(e.message || e), strategies: {} };
    }
  }
  async function loadVixData() {
    try {
      const r = await fetch(API.vix + "?t=" + Date.now(), { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      state.vixData = await r.json();
    } catch {
      state.vixData = null;
    }
  }
  async function loadLegacyData() {
    try {
      const [legacy, archive] = await Promise.all([
        fetch("data.json?t=" + Date.now(), { cache: "no-store" }).catch(() => null),
        fetch("data-octa-archive.json?t=" + Date.now(), { cache: "no-store" }).catch(() => null),
      ]);
      state.legacyData = legacy?.ok ? await legacy.json() : null;
      state.octaArchive = archive?.ok ? await archive.json() : null;
    } catch {
      state.legacyData = null;
      state.octaArchive = null;
    }
  }
  async function pullOctaCloud() {
    try {
      const r = await fetch(API.octa + "?t=" + Date.now(), { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const cloud = await r.json();
      if (cloud && cloud.updated) {
        const localTs = localStorage.getItem(LS.octaCloudTs) || "";
        const cloudHasPortfolio = Object.keys(cloud.portfolio || {}).length > 0;
        const localEmpty = Object.keys(state.octaPortfolio || {}).length === 0;
        if (!localTs || cloud.updated >= localTs || (cloudHasPortfolio && localEmpty)) {
          state.octaPortfolio = cloud.portfolio || {};
          state.octaHistory = cloud.history || [];
          saveJson(LS.octaPortfolio, state.octaPortfolio);
          saveJson(LS.octaHistory, state.octaHistory);
          localStorage.setItem(LS.octaCloudTs, cloud.updated);
        }
      }
      state.sync.octa = "cloud";
    } catch (e) {
      state.sync.octa = "local";
      state.sync.msg = String(e.message || e);
    }
  }
  async function pushOctaCloud() {
    const updated = new Date().toISOString();
    const headers = { "Content-Type": "application/json" };
    const tok = localStorage.getItem("octa_sync_token") || "";
    if (tok) headers["X-Octa-Token"] = tok;
    const expected = localStorage.getItem(LS.octaCloudTs);
    if (expected) headers["X-Octa-Expected-Updated"] = expected;
    const payload = { portfolio: state.octaPortfolio, history: state.octaHistory, updated };
    saveJson(LS.octaPortfolio, state.octaPortfolio);
    saveJson(LS.octaHistory, state.octaHistory);
    try {
      if (!tok) throw new Error("missing_octa_token");
      const r = await fetch(API.octa, { method: "POST", headers, body: JSON.stringify(payload) });
      if (!r.ok) throw new Error(r.status === 401 ? "bad_octa_token" : "HTTP " + r.status);
      const j = await r.json().catch(() => ({}));
      localStorage.setItem(LS.octaCloudTs, j.updated || updated);
      state.sync.octa = "cloud";
    } catch (e) {
      state.sync.octa = "local";
      state.sync.msg = String(e.message || e);
      const tokenProblem = /octa_token/.test(state.sync.msg);
      toast(tokenProblem ? "OCTA salvato in locale. Inserisci OCTA_SYNC_TOKEN in Setup per sync cloud." : "OCTA salvato in locale. Cloud non disponibile.");
    }
  }

  function b64(buf) { return btoa(String.fromCharCode(...new Uint8Array(buf))); }
  function unb64(s) { return Uint8Array.from(atob(s), c => c.charCodeAt(0)); }
  async function deriveKey(pin, salt) {
    const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(pin), "PBKDF2", false, ["deriveKey"]);
    return crypto.subtle.deriveKey({ name: "PBKDF2", salt, iterations: 150000, hash: "SHA-256" }, base, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
  }
  async function encryptObj(pin, obj, saltRaw) {
    const salt = saltRaw || crypto.getRandomValues(new Uint8Array(16));
    const key = await deriveKey(pin, salt);
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(JSON.stringify(obj)));
    return { salt: b64(salt), iv: b64(iv), enc: b64(ct) };
  }
  async function decryptObj(pin, env) {
    const key = await deriveKey(pin, unb64(env.salt));
    const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(env.iv) }, key, unb64(env.enc));
    return JSON.parse(new TextDecoder().decode(pt));
  }
  async function importAesKey(raw) {
    return crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["encrypt", "decrypt"]);
  }
  async function aesDecBytes(key, ivB64, ctB64) {
    return new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(ivB64) }, key, unb64(ctB64)));
  }
  async function decryptWithAesKey(key, ivB64, encB64) {
    const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(ivB64) }, key, unb64(encB64));
    return JSON.parse(new TextDecoder().decode(pt));
  }
  async function encryptWithAesKey(key, obj) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(JSON.stringify(obj)));
    return { iv: b64(iv), enc: b64(ct) };
  }
  async function rsaUnwrap(privKey, s) {
    return new Uint8Array(await crypto.subtle.decrypt({ name: "RSA-OAEP" }, privKey, unb64(s)));
  }
  async function decryptLegacyPortfolio(pin, env) {
    let dek = null;
    try {
      const pinKey = await deriveKey(pin, unb64(env.pinSalt));
      dek = await aesDecBytes(pinKey, env.dekPin.iv, env.dekPin.ct);
    } catch {}
    if (!dek && state.tracker.master) {
      try {
        const m = state.tracker.master;
        const mKey = await deriveKey(pin, unb64(m.privSalt));
        const privRaw = await aesDecBytes(mKey, m.privIv, m.privEnc);
        const privKey = await crypto.subtle.importKey("pkcs8", privRaw, { name: "RSA-OAEP", hash: "SHA-256" }, false, ["decrypt"]);
        dek = await rsaUnwrap(privKey, env.dekMaster);
      } catch {}
    }
    if (!dek) throw new Error("legacy_pin_failed");
    const dekKey = await importAesKey(dek);
    const data = await decryptWithAesKey(dekKey, env.dataIv, env.dataEnc);
    return { data, dekKey };
  }
  function normalizePortfolioData(data) {
    const d = data && typeof data === "object" ? data : {};
    d.transactions = Array.isArray(d.transactions) ? d.transactions : [];
    d.valueHistory = Array.isArray(d.valueHistory) ? d.valueHistory : [];
    d.instrumentInfo = d.instrumentInfo && typeof d.instrumentInfo === "object" ? d.instrumentInfo : {};
    d.manualPrices = d.manualPrices && typeof d.manualPrices === "object" ? d.manualPrices : {};
    d.benchmark = d.benchmark || null;
    d.bench = d.bench || null;
    d.notes = d.notes || "";
    return d;
  }
  async function loadTrackerCloud() {
    try {
      const r = await fetch(API.portfolios + "?t=" + Date.now(), { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const data = await r.json();
      state.tracker = { portfolios: data.portfolios || [], master: data.master || null, updated: data.updated || null };
      saveJson(LS.trackerCache, state.tracker);
      state.sync.portfolios = "cloud";
    } catch (e) {
      state.tracker = loadJson(LS.trackerCache, { portfolios: [], updated: null });
      state.sync.portfolios = "local";
    }
  }
  async function saveTrackerCloud() {
    const data = { ...state.tracker, updated: new Date().toISOString() };
    state.tracker = data;
    saveJson(LS.trackerCache, data);
    const headers = { "Content-Type": "application/json" };
    const tok = localStorage.getItem("tracker_sync_token") || "";
    if (tok) headers["X-Tracker-Token"] = tok;
    try {
      if (!tok) throw new Error("missing_tracker_token");
      const r = await fetch(API.portfolios, { method: "POST", headers, body: JSON.stringify(data) });
      if (!r.ok) throw new Error(r.status === 401 ? "bad_tracker_token" : "HTTP " + r.status);
      state.sync.portfolios = "cloud";
    } catch (e) {
      state.sync.portfolios = "local";
      const msg = String(e.message || e);
      toast(/tracker_token/.test(msg) ? "Portafogli salvati in locale. Inserisci TRACKER_SYNC_TOKEN in Setup per sync cloud." : "Portafogli salvati in locale. Cloud non disponibile.");
    }
  }
  function downloadJson(filename, data) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function exportTrackerBackup() {
    const count = (state.tracker.portfolios || []).length;
    if (!count) { toast("Nessun portafoglio da esportare."); return; }
    const stamp = new Date().toISOString().slice(0, 10);
    downloadJson(`super-investor-vnext-backup-${stamp}.json`, {
      kind: "super-investor-vnext-tracker-backup",
      version: 1,
      exported_at: new Date().toISOString(),
      encrypted: true,
      note: "Backup cifrato: contiene gli archivi portafoglio gia' criptati, non i PIN.",
      tracker: state.tracker,
    });
    toast(`Backup creato: ${count} portafogli cifrati.`);
  }
  async function importTrackerBackup() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json,application/json";
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        if (data?.kind !== "super-investor-vnext-tracker-backup" || !Array.isArray(data?.tracker?.portfolios)) {
          throw new Error("backup_non_valido");
        }
        const count = data.tracker.portfolios.length;
        if (!confirm(`Importare backup con ${count} portafogli cifrati e sostituire il tracker corrente?`)) return;
        state.tracker = { ...data.tracker, updated: new Date().toISOString() };
        state.openPf = null;
        localStorage.removeItem(LS.trackerOpen);
        saveJson(LS.trackerCache, state.tracker);
        await saveTrackerCloud();
        render();
        toast(`Backup importato: ${count} portafogli.`);
      } catch {
        toast("Backup non valido o non leggibile.");
      }
    };
    input.click();
  }
  async function createPortfolio(name, pin) {
    const env = await encryptObj(pin, normalizePortfolioData({}));
    state.tracker.portfolios.push({ id: "pf_" + Date.now().toString(36), name, created: new Date().toISOString(), ...env });
    await saveTrackerCloud();
  }
  async function openPortfolio(id, pin) {
    const env = state.tracker.portfolios.find(p => p.id === id);
    if (!env) return false;
    try {
      let data;
      let legacy = false;
      let dekKey = null;
      if (env.pinSalt && env.dekPin && env.dataIv && env.dataEnc) {
        const opened = await decryptLegacyPortfolio(pin, env);
        data = opened.data;
        dekKey = opened.dekKey;
        legacy = true;
      } else {
        data = await decryptObj(pin, env);
      }
      state.openPf = { id, name: env.name, pin, data: normalizePortfolioData(data), legacy, dekKey };
      localStorage.setItem(LS.trackerOpen, id);
      await refreshQuotes();
      return true;
    } catch {
      toast("PIN non valido o dati non apribili.");
      return false;
    }
  }
  async function saveOpenPortfolio() {
    if (!state.openPf) return;
    const idx = state.tracker.portfolios.findIndex(p => p.id === state.openPf.id);
    if (idx < 0) return;
    const old = state.tracker.portfolios[idx];
    const dataToSave = normalizePortfolioData(state.openPf.data);
    if (state.openPf.legacy && state.openPf.dekKey) {
      const data = await encryptWithAesKey(state.openPf.dekKey, dataToSave);
      state.tracker.portfolios[idx] = { ...old, dataIv: data.iv, dataEnc: data.enc, updated: new Date().toISOString() };
    } else {
      const env = await encryptObj(state.openPf.pin, dataToSave, old.salt ? unb64(old.salt) : undefined);
      state.tracker.portfolios[idx] = { ...old, ...env, updated: new Date().toISOString() };
    }
    await saveTrackerCloud();
  }
  function holdingsFromTransactions(txs) {
    const map = {};
    let dividends = 0, cash = 0;
    for (const tx of txs || []) {
      const rawType = String(tx.type || "BUY").toUpperCase();
      const type = rawType === "DIVIDEND" ? "DIV" : rawType === "DEPOSIT" ? "CASH" : rawType;
      const sym = String(tx.symbol || "").trim().toUpperCase();
      const qty = Number(tx.qty ?? tx.quantity ?? 0);
      const price = Number(tx.price ?? tx.amount ?? 0);
      if (type === "DIV") { dividends += price; cash += price; continue; }
      if (type === "CASH") { cash += price; continue; }
      if (!sym) continue;
      if (!map[sym]) map[sym] = { symbol: sym, name: tx.name || sym, qty: 0, invested: 0 };
      if (type === "SNAP" || type === "SNAPSHOT" || type === "SYNC") {
        map[sym].qty = qty;
        map[sym].invested = qty * price;
        map[sym].name = tx.name || map[sym].name;
        continue;
      }
      if (type === "BUY") { map[sym].qty += qty; map[sym].invested += qty * price; }
      if (type === "SELL") { map[sym].qty -= qty; map[sym].invested -= Math.min(map[sym].invested, qty * price); cash += qty * price; }
      map[sym].name = tx.name || map[sym].name;
    }
    const holdings = Object.values(map).filter(h => Math.abs(h.qty) > 0.000001);
    return { holdings, dividends, cash };
  }
  function portfolioStats(pf) {
    const { holdings, dividends, cash } = holdingsFromTransactions(pf?.data?.transactions || []);
    let value = cash, invested = 0;
    const info = pf?.data?.instrumentInfo || {};
    for (const h of holdings) {
      const manual = pf?.data?.manualPrices?.[h.symbol];
      const q = state.quotes[h.symbol];
      const resolved = q?.resolved && String(q.resolved).toUpperCase() !== h.symbol ? q.resolved : "";
      const quoteInfo = state.info[h.symbol] || state.info[resolved] || {};
      const meta = info[h.symbol] || info[h.symbol.toUpperCase()] || {};
      h.ticker = resolved;
      h.name = meta.name || quoteInfo.name || (h.name && h.name !== h.symbol ? h.name : "") || resolved || h.symbol;
      h.type = meta.type || quoteInfo.type || "";
      h.sector = meta.sector || quoteInfo.sector || "";
      const px = Number(manual) > 0 ? Number(manual) : quoteUnitEur(h.symbol);
      const unit = px ?? h.invested / Math.max(h.qty, 1);
      h.price = px;
      h.currency = q?.currency || "EUR";
      h.value = h.qty * unit;
      h.avgCost = h.qty ? h.invested / h.qty : 0;
      const prev = q?.prevClose != null ? toEur(q.prevClose, q.currency, fxRate()) : null;
      h.dayPct = px != null && prev ? (px / prev - 1) * 100 : null;
      h.pl = h.value - h.invested;
      h.plPct = h.invested ? h.pl / h.invested * 100 : 0;
      invested += h.invested;
      value += h.value;
    }
    for (const h of holdings) h.weight = value ? h.value / value * 100 : 0;
    return { holdings, value, invested, dividends, cash, gain: value - invested, gainPct: invested ? (value / invested - 1) * 100 : 0 };
  }
  async function refreshQuotes() {
    const set = new Set(Object.keys(state.octaPortfolio || {}));
    MARKET_WATCH.forEach(x => set.add(x.symbol));
    (state.octaData?.signals || []).forEach(s => set.add(s.ticker));
    if (state.openPf) holdingsFromTransactions(state.openPf.data.transactions).holdings.forEach(h => set.add(h.symbol));
    const symbols = [...set].filter(Boolean).slice(0, 60);
    if (!symbols.length) return;
    try {
      const benchmark = state.openPf?.data?.benchmark || "";
      const bulkRange = "5y";
      const r = await fetch(API.quotes, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ symbols, enrich: symbols, priceHistory: symbols, historyRange: bulkRange, fxHistory: true, benchmark }) });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const j = await r.json();
      state.quotes = { ...state.quotes, ...(j.quotes || {}) };
      state.info = { ...(state.info || {}), ...(j.info || {}) };
      state.priceHistory = { ...state.priceHistory, ...(j.priceHistory || {}) };
      Object.keys(j.priceHistory || {}).forEach(s => { state.priceHistoryRange[tickerKey(s)] = bulkRange; });
      state.fx = { ...(state.fx || {}), ...(j.fx || {}) };
      state.fxHistory = { ...(state.fxHistory || {}), ...(j.fxHistory || {}) };
      if (state.openPf && benchmark) state.openPf.data.bench = j.bench || null;
    } catch {}
  }
  function recordOpenPortfolioSnapshot() {
    if (!state.openPf) return false;
    const st = portfolioStats(state.openPf);
    if (!(st.value > 0)) return false;
    const d = todayISO();
    const hist = state.openPf.data.valueHistory || (state.openPf.data.valueHistory = []);
    const v = Math.round(st.value * 100) / 100;
    const last = hist[hist.length - 1];
    if (last && last.d === d) last.v = v;
    else hist.push({ d, v });
    while (hist.length > 1200) hist.shift();
    return true;
  }

  async function refreshAll(message = "Dati aggiornati.") {
    await Promise.all([loadOctaData(), loadApexData(), loadVixData(), loadFreshnessStatus(), loadLegacyData(), loadTrackerCloud(), pullOctaCloud()]);
    await refreshQuotes();
    render();
    toast(message);
  }

  function wireShell() {
    $$(".nav-btn,[data-view]").forEach(btn => btn.addEventListener("click", () => {
      const view = btn.dataset.view;
      if (!view) return;
      state.view = view;
      if (view === "strategy") state.apexFocus = null;
      localStorage.setItem(LS.view, view);
      render();
    }));
    $("#refresh-btn").addEventListener("click", () => refreshAll());
    $("#share-btn").addEventListener("click", async () => {
      const f = freshness();
      const text = `Super Investor vNext: ${f.label}. ${f.detail}`;
      if (navigator.share) await navigator.share({ title: "Super Investor vNext", text, url: location.href }).catch(() => {});
      else navigator.clipboard?.writeText(text).then(() => toast("Testo copiato."));
    });
    $("#info-close").addEventListener("click", () => $("#info-dialog").close());
    $("#trade-form").addEventListener("submit", e => { e.preventDefault(); completeTrade(); });
    $("#apex-exec-form").addEventListener("submit", e => { e.preventDefault(); completeApexExecution(); });
    $("#portfolio-form").addEventListener("submit", async e => {
      e.preventDefault();
      await createPortfolio($("#pf-name").value.trim(), $("#pf-pin").value);
      $("#portfolio-dialog").close();
      render();
    });
    $("#open-pf-form").addEventListener("submit", async e => {
      e.preventDefault();
      const id = state.pendingOpenPf;
      const pin = $("#open-pf-pin").value;
      if (id && pin && await openPortfolio(id, pin)) {
        $("#open-pf-dialog").close();
        render();
      }
    });
    $("#tx-form").addEventListener("submit", async e => {
      e.preventDefault();
      if (!state.openPf) return;
      const sym = $("#tx-symbol").value.trim().toUpperCase();
      const nm = $("#tx-name-input").value.trim();
      if (sym && nm) {
        state.openPf.data.instrumentInfo = state.openPf.data.instrumentInfo || {};
        state.openPf.data.instrumentInfo[sym] = { ...(state.openPf.data.instrumentInfo[sym] || {}), name: nm };
      }
      state.openPf.data.transactions.push({
        id: "tx_" + Date.now().toString(36), type: $("#tx-type").value,
        symbol: sym, name: nm,
        qty: Number($("#tx-qty").value || 0), price: Number($("#tx-price").value || 0), date: $("#tx-date").value || todayISO()
      });
      await saveOpenPortfolio();
      $("#tx-dialog").close();
      await refreshQuotes();
      render();
    });
    $("#import-file").addEventListener("change", handleImportFile);
    $("#import-form").addEventListener("submit", async e => {
      e.preventDefault();
      await applyPortfolioImport();
    });
    document.addEventListener("click", async e => {
      const viewBtn = e.target.closest("[data-view]");
      if (viewBtn && !e.target.closest("[data-action]")) {
        const view = viewBtn.dataset.view;
        state.view = view;
        if (view === "strategy") state.apexFocus = null;
        localStorage.setItem(LS.view, view);
        render();
        return;
      }
      const b = e.target.closest("[data-action]");
      if (!b) return;
      const act = b.dataset.action;
      if (act === "trade") openTrade(b.dataset.signal);
      if (act === "open-pf") openPortfolioDialog(b.dataset.id);
      if (act === "new-pf") { $("#pf-name").value = ""; $("#pf-pin").value = ""; $("#portfolio-dialog").showModal(); }
      if (act === "add-tx") { openTxDialog(); }
      if (act === "refresh-pf") {
        await refreshQuotes();
        const wrote = recordOpenPortfolioSnapshot();
        if (wrote) await saveOpenPortfolio();
        render();
        toast(wrote ? "Prezzi aggiornati e snapshot salvato." : "Prezzi aggiornati.");
      }
      if (act === "import-pf") openImportDialog();
      if (act === "rename-pf") await renamePortfolio();
      if (act === "delete-pf") await deletePortfolio();
      if (act === "delete-tx") await deleteTx(b.dataset.tx);
      if (act === "holding-detail") await openHoldingDetail(b.dataset.symbol);
      if (act === "set-manual-price") await setManualPrice(b.dataset.symbol);
      if (act === "clear-manual-price") await clearManualPrice(b.dataset.symbol);
      if (act === "quick-tx") await quickHoldingTx(b.dataset.symbol, b.dataset.kind);
      if (act === "set-benchmark") await setBenchmark(b.dataset.symbol);
      if (act === "clear-benchmark") await clearBenchmark();
      if (act === "alloc-view") { state.allocView = b.dataset.alloc || "symbol"; render(); }
      if (act === "ai-pf") await askPortfolioAI();
      if (act === "ai-octa") await askOctaAI();
      if (act === "ai-ticker") await askTickerAI(b.dataset.ticker);
      if (act === "ai-apex") await askApexAI(b.dataset.strategy || state.apexFocus || "legit");
      if (act === "export-tracker-backup") exportTrackerBackup();
      if (act === "import-tracker-backup") await importTrackerBackup();
      if (act === "refresh-all") await refreshAll("Controllo completato.");
      if (act === "run-engines") await runEngines(b.dataset.mode || "all");
      if (act === "open-apex") { state.apexFocus = b.dataset.strategy || "legit"; render(); }
      if (act === "back-apex-home") { state.apexFocus = null; render(); }
      if (act === "apex-done") markApexDone(b.dataset.strategy || "legit");
      if (act === "toggle-apex-history") {
        const key = b.dataset.strategy || "legit";
        state.apexHistoryOpen[key] = !state.apexHistoryOpen[key];
        saveJson(LS.apexHistoryOpen, state.apexHistoryOpen);
        render();
      }
      if (act === "octa-detail") await openOctaDetail(b.dataset.ticker);
      if (act === "octa-legend") openOctaLegend();
      if (act === "toggle-radar") { state.radarOpen = !state.radarOpen; render(); }
      if (act === "chart-range") {
        state.chartRanges[b.dataset.chart] = b.dataset.range;
        saveJson(LS.chartRanges, state.chartRanges);
        if (b.dataset.context === "octa-detail" && state.detailTicker) renderOctaDetailBody(state.detailTicker);
        else if (b.dataset.context === "holding-detail" && state.detailHolding) renderHoldingDetailBody(state.detailHolding);
        else render();
      }
      if (act === "repair-local") repairAndReload(state.view);
      if (act === "reset-octa-local") { if (confirm("Azzerare dati locali OCTA in questa vNext?")) { state.octaPortfolio = {}; state.octaHistory = []; state.octaExecuted = {}; saveJson(LS.octaPortfolio, {}); saveJson(LS.octaHistory, []); saveJson(LS.octaExecuted, {}); render(); } }
    });
    document.addEventListener("pointerdown", updateChartMarker);
    document.addEventListener("pointermove", updateChartMarker);
    document.addEventListener("pointercancel", e => {
      const card = e.target.closest?.(".chart-card");
      if (card) hideChartMarker(card);
    }, true);
    document.addEventListener("pointerleave", e => {
      const card = e.target.closest?.(".chart-card");
      if (card) hideChartMarker(card);
    }, true);
  }
  function openPortfolioDialog(id) {
    const pf = (state.tracker.portfolios || []).find(p => p.id === id);
    if (!pf) return;
    state.pendingOpenPf = id;
    $("#open-pf-title").textContent = `Apri ${pf.name}`;
    $("#open-pf-pin").value = "";
    $("#open-pf-dialog").showModal();
    setTimeout(() => $("#open-pf-pin")?.focus(), 40);
  }
  async function renamePortfolio() {
    if (!state.openPf) return;
    const name = prompt("Nuovo nome del portafoglio:", state.openPf.name);
    if (!name || !name.trim()) return;
    const env = state.tracker.portfolios.find(p => p.id === state.openPf.id);
    if (!env) return;
    env.name = name.trim();
    state.openPf.name = env.name;
    await saveTrackerCloud();
    render();
  }
  async function deletePortfolio() {
    if (!state.openPf) return;
    if (!confirm(`Eliminare il portafoglio "${state.openPf.name}" dalla vNext?`)) return;
    state.tracker.portfolios = state.tracker.portfolios.filter(p => p.id !== state.openPf.id);
    state.openPf = null;
    localStorage.removeItem(LS.trackerOpen);
    await saveTrackerCloud();
    render();
  }
  async function deleteTx(id) {
    if (!state.openPf || !id) return;
    state.openPf.data.transactions = (state.openPf.data.transactions || []).filter(tx => tx.id !== id);
    await saveOpenPortfolio();
    await refreshQuotes();
    if (state.detailHolding) renderHoldingDetailBody(state.detailHolding);
    render();
  }
  async function setManualPrice(symbol) {
    if (!state.openPf) return;
    const sym = tickerKey(symbol);
    const cur = state.openPf.data.manualPrices?.[sym];
    const raw = prompt(`Prezzo manuale per ${sym} in euro:`, cur != null ? String(cur) : "");
    if (raw == null) return;
    const val = Number(String(raw).replace(",", "."));
    if (!(val > 0)) { toast("Prezzo non valido."); return; }
    state.openPf.data.manualPrices[sym] = val;
    await saveOpenPortfolio();
    if (state.detailHolding === sym) renderHoldingDetailBody(sym);
    render();
  }
  async function clearManualPrice(symbol) {
    if (!state.openPf) return;
    const sym = tickerKey(symbol);
    delete state.openPf.data.manualPrices[sym];
    await saveOpenPortfolio();
    await refreshQuotes();
    if (state.detailHolding === sym) renderHoldingDetailBody(sym);
    render();
  }
  async function quickHoldingTx(symbol, kind) {
    if (!state.openPf) return;
    const sym = tickerKey(symbol);
    const qtyRaw = prompt(`${kind === "SELL" ? "Quante quote vuoi vendere" : "Quante quote vuoi aggiungere"} di ${sym}?`);
    if (qtyRaw == null) return;
    const qty = Number(String(qtyRaw).replace(",", "."));
    if (!(qty > 0)) { toast("Quantita non valida."); return; }
    const priceRaw = prompt("Prezzo unitario in euro:", "");
    if (priceRaw == null) return;
    const price = Number(String(priceRaw).replace(",", "."));
    if (!(price >= 0)) { toast("Prezzo non valido."); return; }
    const meta = state.openPf.data.instrumentInfo?.[sym] || {};
    state.openPf.data.transactions.push({ id: "tx_q_" + Date.now().toString(36), type: kind || "BUY", symbol: sym, name: meta.name || sym, qty, price, date: todayISO() });
    await saveOpenPortfolio();
    await refreshQuotes();
    if (state.detailHolding === sym) renderHoldingDetailBody(sym);
    render();
  }
  async function setBenchmark(symbol) {
    if (!state.openPf) return;
    let sym = String(symbol || "").trim().toUpperCase();
    if (sym === "__CUSTOM") {
      const raw = prompt("Ticker o ISIN dell'indice di confronto:", "SXR8.DE");
      if (!raw || !raw.trim()) return;
      sym = raw.trim().toUpperCase();
    }
    state.openPf.data.benchmark = sym;
    await refreshQuotes();
    await saveOpenPortfolio();
    render();
  }
  async function clearBenchmark() {
    if (!state.openPf) return;
    state.openPf.data.benchmark = null;
    state.openPf.data.bench = null;
    await saveOpenPortfolio();
    render();
  }
  function openApexExecution(key = "legit") {
    const st = state.apexData?.strategies?.[key];
    const cur = st?.current;
    if (!cur) return;
    state.pendingApexExec = { key, st, cur };
    $("#apex-exec-eyebrow").textContent = st.name;
    $("#apex-exec-title").textContent = `Registra ${cur.asset}`;
    $("#apex-prev-asset").value = state.apexExecuted?.[key]?.asset || cur.previous_asset || "";
    $("#apex-new-asset").value = cur.asset || "";
    $("#apex-capital").value = "";
    $("#apex-price").value = "";
    $("#apex-fee").value = key === "legit" ? "5" : "0";
    $("#apex-exec-date").value = todayISO();
    $("#apex-note").value = cur.reason || "";
    $("#apex-exec-dialog").showModal();
  }
  function markApexDone(key = "legit") {
    openApexExecution(key);
  }
  function completeApexExecution() {
    const pending = state.pendingApexExec;
    if (!pending?.cur || !pending?.st) return;
    const key = pending.key;
    const st = pending.st;
    const cur = pending.cur;
    const prev = $("#apex-prev-asset").value.trim().toUpperCase();
    const next = $("#apex-new-asset").value.trim().toUpperCase() || cur.asset;
    const date = $("#apex-exec-date").value || todayISO();
    const rec = {
      id: "apex_" + Date.now().toString(36),
      strategy_key: key,
      strategy: st.name,
      signal_date: cur.date,
      executed_date: date,
      previous_asset: prev || null,
      asset: next,
      target_asset: cur.asset,
      capital_eur: Number($("#apex-capital").value || 0) || null,
      execution_price: Number($("#apex-price").value || 0) || null,
      fee_eur: Number($("#apex-fee").value || 0) || 0,
      note: $("#apex-note").value.trim(),
      saved_at: new Date().toISOString(),
    };
    state.apexHistory.unshift(rec);
    state.apexHistory = state.apexHistory.slice(0, 300);
    saveJson(LS.apexHistory, state.apexHistory);
    state.apexExecuted[key] = {
      asset: next,
      date: cur.date,
      done_at: new Date().toISOString(),
      strategy: st.name,
      execution_id: rec.id,
    };
    saveJson(LS.apexExecuted, state.apexExecuted);
    $("#apex-exec-dialog").close();
    render();
    toast(`${st.name}: esecuzione salvata nello storico.`);
  }
  async function runEngines(mode = "all") {
    toast("Richiedo run motori su GitHub Actions...");
    try {
      const r = await fetch(API.runEngines, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok || !j.ok) throw new Error(j.error || "run_not_configured");
      toast("Run richiesta. Il deploy arrivera a fine workflow.");
    } catch (e) {
      toast("Run da app non configurata: apro GitHub Actions.");
      window.open(CLOUD_RUNNER.workflow, "_blank", "noopener");
    }
  }
  function hideChartMarker(card) {
    $(".chart-marker", card)?.setAttribute("hidden", "");
    $(".chart-tip", card)?.setAttribute("hidden", "");
  }
  function updateChartMarker(e) {
    const card = e.target.closest?.(".chart-card[data-chart]");
    if (!card) return;
    const scroll = $(".chart-scroll", card);
    const svg = $(".line-chart", card);
    const data = chartStore.get(card.dataset.chart);
    if (!scroll || !svg || !data?.points?.length) return;
    const rect = svg.getBoundingClientRect();
    if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) return;
    const idx = Math.max(0, Math.min(data.points.length - 1, Math.round((e.clientX - rect.left) / rect.width * (data.points.length - 1))));
    const p = data.points[idx];
    const left = (idx / Math.max(1, data.points.length - 1)) * svg.clientWidth;
    const marker = $(".chart-marker", card);
    const tip = $(".chart-tip", card);
    marker.hidden = false;
    tip.hidden = false;
    marker.style.left = `${left}px`;
    tip.style.left = `${Math.max(8, Math.min(svg.clientWidth - 150, left - 62))}px`;
    tip.textContent = `${dateIT(p.d)} · ${data.fmt(Number(p.v))}`;
  }

  function render() {
    $$(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.view === state.view));
    const titles = {
      today: ["Cockpit operativo", "Oggi"],
      octa: ["Strategia QFAS", "OCTA"],
      portfolios: ["Tracker cifrato", "Portafogli"],
      strategy: ["Strategia BTC", "APEX"],
      settings: ["Configurazione locale", "Setup"]
    };
    const [ey, title] = titles[state.view] || titles.today;
    $("#view-eyebrow").textContent = ey;
    $("#view-title").textContent = title;
    renderStatusStrip();
    const root = $("#content");
    root.innerHTML = "";
    if (state.view === "today") root.innerHTML = viewToday();
    if (state.view === "octa") root.innerHTML = viewOcta();
    if (state.view === "portfolios") root.innerHTML = viewPortfolios();
    if (state.view === "strategy") root.innerHTML = viewStrategy();
    if (state.view === "settings") root.innerHTML = viewSettings();
  }
  function isSignalDone(s) {
    if (!s) return false;
    if (state.octaExecuted[s.id]) return true;
    if (s.action === "BUY" && state.octaPortfolio && state.octaPortfolio[s.ticker]) return true;
    if (s.action === "SELL" && state.octaPortfolio && !state.octaPortfolio[s.ticker]) return true;
    return false;
  }
  function renderStatusStrip() {
    const strip = $("#status-strip");
    if (!strip) return;
    const show = false;
    if (!show) {
      strip.hidden = true;
      strip.innerHTML = "";
      return;
    }
    strip.hidden = false;
    if (state.view === "strategy") {
      const keys = apexStrategyKeys();
      const alerts = keys.map(k => apexStrategy(k)?.radar).filter(r => r && r.level && r.level !== "ok");
      const main = apexStrategy(state.apexFocus || "legit") || apexStrategy("legit") || {};
      const cur = main.current || {};
      const bt = main.backtest || {};
      const done = state.apexExecuted?.[main.key || "legit"];
      const doneOk = done && done.date === cur.date && done.asset === cur.asset;
      strip.innerHTML = `
        <div class="status-item ${cur.asset ? "good" : "warn"}"><b>${esc(main.name || "APEX")}</b><span>${cur.asset ? `${apexAssetLabel(main.key || "legit", cur.asset)} · segnale ${dateIT(cur.date)}` : "Segnale non caricato"}</span></div>
        <div class="status-item ${alerts.length ? "warn" : "good"}"><b>${alerts.length ? `${alerts.length} radar` : "Radar ok"}</b><span>${alerts.length ? alerts.map(r => r.radar_asset || r.raw_asset).join(", ") : "Nessun alert operativo: il radar resta informativo"}</span></div>
        <div class="status-item good"><b>${pct(Number(bt.cagr || 0), 1)} CAGR</b><span>${esc(apexTaxLabel(main))} · DD ${pct(Number(bt.max_drawdown || 0), 1)}</span></div>
        <div class="status-item ${doneOk ? "good" : "info"}"><b>Run unico</b><span>Martedi 15:30: Legit, Dex, Degen + OCTA nello stesso workflow</span></div>`;
      return;
    }
    const f = freshness();
    const signals = state.octaData?.signals || [];
    const pending = signals.filter(s => !isSignalDone(s)).length;
    const syncCls = state.sync.octa === "cloud" ? "good" : "warn";
    const pfCls = state.sync.portfolios === "cloud" ? "good" : "warn";
    strip.innerHTML = `
      <div class="status-item ${f.cls}"><b>${esc(f.label)}</b><span>${esc(f.detail)}</span></div>
      <div class="status-item ${pending ? "warn" : "good"}"><b>${pending} da eseguire</b><span>${signals.length} segnali nel file OCTA corrente</span></div>
      <div class="status-item ${syncCls}"><b>OCTA ${state.sync.octa === "cloud" ? "cloud" : "locale"}</b><span>${state.sync.octa === "cloud" ? "Portfolio letto dal cloud" : "Cloud non verificato in locale"}</span></div>
      <div class="status-item ${pfCls}"><b>Portafogli ${state.sync.portfolios === "cloud" ? "cloud" : "locale"}</b><span>${(state.tracker.portfolios || []).length} archivi cifrati</span></div>`;
  }
  function viewToday() {
    const f = freshness();
    const d = state.octaData || {};
    const signals = d.signals || [];
    const pending = signals.filter(s => !isSignalDone(s));
    const buys = pending.filter(s => s.action === "BUY");
    const sells = pending.filter(s => s.action === "SELL");
    const stats = octaStats();
    const apex = todayApexSummary();
    const octaTone = f.cls === "bad" ? "bad" : pending.length ? "warn" : "good";
    const apexTone = apex.needAction ? "warn" : apex.alerts ? "info" : "good";
    const runTone = f.cls === "good" && !d.engine_error ? "good" : "warn";
    const actionText = pending.length ? `${pending.length} azioni da valutare` : "Nessuna azione aperta";
    const top = pending.slice(0, 3).map(signalCard).join("") || `<div class="notice good"><strong>OCTA senza azioni pendenti</strong><br>Il portafoglio registrato e' allineato ai segnali disponibili.</div>`;
    return `
      <section class="panel full today-hero">
        <div>
          <h2>Oggi</h2>
          <p>Prima controlla se i dati sono freschi. Poi guarda se OCTA o APEX chiedono un intervento.</p>
        </div>
        <div class="today-hero-side">
          <span class="badge ${runTone}">${esc(f.label)}</span>
          <div class="toolbar">
            <button class="button primary" data-action="refresh-all">${icon("refresh")}Aggiorna dati</button>
            <button class="button" data-action="run-engines" data-mode="all">${icon("play")}Run tutto</button>
          </div>
        </div>
      </section>
      <section class="today-card-row">
        ${todayDecisionCard("OCTA", octaTone, actionText, `${buys.length} buy · ${sells.length} sell`, `P/L ${eurMaybe(stats.pnl, 0)} · ${pct(stats.pnlPct)}`, "octa")}
        ${todayApexDecisionCard(apexTone, apex)}
        ${todayDecisionCard("Mercato", todayVixTone(), todayMarketHeadline(), "VIX · S&P 500 · BTC · Oro", todayMarketShort(), "")}
      </section>
      <section class="panel wide today-focus">
        <div class="panel-head"><div><h2>Notifiche segnali</h2><p>Solo quello che puo' richiedere una decisione oggi.</p></div><span class="badge ${f.cls}">${dateIT(d.signal_date)}</span></div>
        <div class="signal-list">${top}</div>
      </section>
      <section class="panel sidebar">
        <div class="panel-head"><div><h2>Run e stato</h2><p>Una lettura veloce: fresco, errore motore, cloud.</p></div></div>
        ${todayRunOverview()}
      </section>
      <section class="panel full today-market-panel">
        <div class="panel-head"><div><h2>Mercati da tenere d'occhio</h2><p>Piccolo radar live: non e' un segnale operativo, serve a leggere il contesto.</p></div><span class="badge ${todayVixTone()}">${esc(todayVixLabel())}</span></div>
        ${todayMarketPanel()}
      </section>
      <section class="panel full today-shortcuts">
        <button class="button ghost" data-view="octa">${icon("chart")}Apri OCTA completa</button>
        <button class="button ghost" data-view="strategy">Apri APEX completa</button>
        <button class="button ghost" data-view="portfolios">${icon("lock")}Apri Portafogli</button>
      </section>`;
  }
  function todayDecisionCard(title, cls, main, sub, foot, view) {
    const action = view ? ` data-view="${esc(view)}"` : "";
    const tag = view ? "button" : "article";
    return `<${tag} class="today-card ${cls}"${action}>
      <span>${esc(title)}</span>
      <strong>${esc(main)}</strong>
      <em>${esc(sub)}</em>
      <small>${esc(foot)}</small>
    </${tag}>`;
  }
  function todayApexDecisionCard(cls, apex) {
    const mini = (apex.items || []).map(x => `<div class="today-apex-mini ${esc(x.cls)}">
      <span>${esc(x.name)}</span>
      <strong>${esc(x.asset)}</strong>
      <em>${esc(x.radar)}</em>
    </div>`).join("");
    return `<button class="today-card today-card-apex ${cls}" data-view="strategy">
      <span>APEX</span>
      <strong>${esc(apex.label)}</strong>
      <div class="today-apex-mini-grid">${mini || `<em>Segnali non caricati</em>`}</div>
      <small>${esc(apex.radar)}</small>
    </button>`;
  }
  function todayApexSummary() {
    const keys = apexStrategyKeys();
    const active = keys.map(k => ({ key: k, st: apexStrategy(k) })).filter(x => x.st?.current);
    const needAction = active.filter(({ key, st }) => st.current.changed && !(state.apexExecuted?.[key]?.date === st.current.date && state.apexExecuted?.[key]?.asset === st.current.asset));
    const alerts = active.filter(({ st }) => st.radar?.level && st.radar.level !== "ok");
    const items = active.map(({ key, st }) => {
      const r = st.radar || {};
      const changed = st.current.changed && !(state.apexExecuted?.[key]?.date === st.current.date && state.apexExecuted?.[key]?.asset === st.current.asset);
      const cls = changed ? "warn" : r.level === "alert" ? "bad" : r.level === "watch" ? "warn" : "good";
      return {
        name: (st.name || key).replace(/^APEX\s*/i, ""),
        asset: apexAssetLabel(key, st.current.asset),
        radar: r.level && r.level !== "ok" ? apexRadarLabel(r) : "radar ok",
        cls,
      };
    });
    return {
      needAction: needAction.length,
      alerts: alerts.length,
      label: needAction.length ? `${needAction.length} cambio da registrare` : "Nessun cambio richiesto",
      sub: active.length ? active.map(({ key, st }) => `${st.name}: ${apexAssetLabel(key, st.current.asset)}`).join(" · ") : "Segnale non caricato",
      radar: alerts.length ? `${alerts.length} radar da guardare` : "Tutti i radar allineati",
      items,
    };
  }
  function todayApexMini() {
    const keys = apexStrategyKeys();
    const rows = keys.map(k => {
      const st = apexStrategy(k);
      if (!st?.current) return "";
      const r = st.radar || {};
      const cls = st.current.changed ? "warn" : r.level === "alert" ? "bad" : r.level === "watch" ? "warn" : "good";
      const radar = r.level && r.level !== "ok" ? r.level : "ok";
      return `<button class="today-apex-row ${cls}" data-action="open-apex" data-strategy="${esc(k)}">
        <span>${esc(st.name)}</span>
        <strong>${esc(apexAssetLabel(k, st.current.asset))}</strong>
        <em>radar ${esc(radar)}</em>
      </button>`;
    }).join("");
    return `<div class="today-apex-list">${rows || `<div class="empty">APEX non ancora caricato.</div>`}</div>`;
  }
  function todayRunOverview() {
    const d = state.octaData || {};
    const wf = state.freshnessFile || {};
    const apex = state.apexData || {};
    const f = freshness();
    return `<div class="row-list today-run-list">
      <div class="kv"><span>OCTA</span><strong class="${f.cls === "good" ? "pos" : "neg"}">${esc(f.label)}</strong></div>
      <div class="kv"><span>Data segnale</span><strong>${dateIT(d.signal_date)}</strong></div>
      <div class="kv"><span>Errore motore</span><strong class="${d.engine_error ? "neg" : "pos"}">${d.engine_error ? "si" : "no"}</strong></div>
      <div class="kv"><span>APEX export</span><strong>${apex.generated_at ? timeIT(apex.generated_at) : "n/d"}</strong></div>
      <div class="kv"><span>OCTA cloud</span><strong>${esc(state.sync.octa)}</strong></div>
      <div class="kv"><span>Portafogli cloud</span><strong>${esc(state.sync.portfolios)}</strong></div>
      <div class="kv"><span>Freshness</span><strong>${wf.generated_at ? timeIT(wf.generated_at) : "runtime"}</strong></div>
    </div>`;
  }
  function todayMarketRows() {
    return MARKET_WATCH.map(w => {
      const q = state.quotes[w.symbol.toUpperCase()] || state.quotes[w.symbol];
      const px = quoteUnitEur(w.symbol);
      const prev = q?.prevClose != null ? toEur(q.prevClose, q.currency, fxRate()) : null;
      const chg = px != null && prev ? (px / prev - 1) * 100 : null;
      return { ...w, px, chg };
    });
  }
  function todayMarketHeadline() {
    const vix = Number(state.vixData?.vix);
    if (Number.isFinite(vix)) return `VIX ${vix.toFixed(1)} · ${todayVixLabel()}`;
    const rows = todayMarketRows();
    const live = rows.filter(r => r.px != null);
    if (!live.length) return "Dati live in caricamento";
    const worst = live.slice().sort((a,b) => Number(a.chg || 0) - Number(b.chg || 0))[0];
    const best = live.slice().sort((a,b) => Number(b.chg || 0) - Number(a.chg || 0))[0];
    if (best?.chg != null && Math.abs(best.chg) >= Math.abs(worst?.chg || 0)) return `${best.label} ${pct(best.chg)}`;
    if (worst?.chg != null) return `${worst.label} ${pct(worst.chg)}`;
    return "Prezzi aggiornati";
  }
  function todayMarketShort() {
    const rows = todayMarketRows().filter(r => r.px != null);
    const vix = Number(state.vixData?.vix);
    const vixText = Number.isFinite(vix) ? `VIX ${vix.toFixed(1)}` : null;
    if (!rows.length) return vixText || "Premi Aggiorna dati";
    return [vixText, ...rows.map(r => `${r.label} ${r.chg == null ? eurMaybe(r.px, 0) : pct(r.chg)}`)].filter(Boolean).join(" · ");
  }
  function todayVixTone() {
    const v = Number(state.vixData?.vix);
    if (!Number.isFinite(v)) return "info";
    if (v >= 28) return "bad";
    if (v >= 18) return "warn";
    return "good";
  }
  function todayVixLabel() {
    const v = Number(state.vixData?.vix);
    if (!Number.isFinite(v)) return "VIX n/d";
    if (v >= 40) return "panico";
    if (v >= 28) return "risk-off";
    if (v >= 18) return "attenzione";
    return "mercato calmo";
  }
  function todayMarketPanel() {
    const rows = todayMarketRows();
    const v = Number(state.vixData?.vix);
    const vixTile = `<div class="today-market-tile ${todayVixTone()}">
      <span>VIX</span>
      <strong>${Number.isFinite(v) ? v.toFixed(1) : "n/d"}</strong>
      <em>${esc(todayVixLabel())}${state.vixData?.ts ? ` · ${timeIT(state.vixData.ts)}` : ""}</em>
    </div>`;
    return `<div class="today-market-grid">${vixTile}${rows.map(r => {
      const cls = r.chg == null ? "info" : r.chg >= 0 ? "good" : "bad";
      return `<div class="today-market-tile ${cls}">
        <span>${esc(r.label)}</span>
        <strong>${r.px == null ? "n/d" : eurMaybe(r.px, r.symbol === "BTC-USD" ? 0 : 2)}</strong>
        <em>${r.chg == null ? "variazione n/d" : pct(r.chg)}</em>
      </div>`;
    }).join("")}</div>`;
  }
  function automationPanel() {
    const wf = state.freshnessFile || {};
    const f = freshness();
    const cls = wf.fresh === false || f.cls === "bad" ? "bad" : "good";
    const next = nextRefreshInfo();
    return `<div class="row-list">
      <div class="notice ${cls}"><strong>${esc(f.label)}</strong><br>${esc(f.detail)}</div>
      <div class="kv"><span>Runner attuale</span><strong>${esc(CLOUD_RUNNER.name)}</strong></div>
      <div class="kv"><span>Deploy</span><strong>${esc(CLOUD_RUNNER.deploy)}</strong></div>
      <div class="kv"><span>Refresh vNext</span><strong>${esc(CLOUD_RUNNER.schedule)}</strong></div>
      <div class="kv"><span>Prossimo refresh</span><strong>${esc(next.label)}</strong></div>
      <div class="kv"><span>Requisito</span><strong>PC non richiesto</strong></div>
      <div class="kv"><span>Check freshness</span><strong>${wf.generated_at ? timeIT(wf.generated_at) : "in app"}</strong></div>
      <div class="kv"><span>Expected trading date</span><strong>${dateIT(wf.expected_signal_date || expectedSignalDate())}</strong></div>
      <div class="kv"><span>Workflow message</span><strong>${esc(wf.message || "runtime check")}</strong></div>
      <div class="toolbar"><button class="button primary" data-action="refresh-all">${icon("refresh")}Ricontrolla</button><a class="button ghost" href="${esc(CLOUD_RUNNER.workflow)}" target="_blank" rel="noopener">Actions</a><a class="button ghost" href="${esc(CLOUD_RUNNER.site)}" target="_blank" rel="noopener">Sito cloud</a></div>
    </div>`;
  }
  function healthList() {
    const d = state.octaData || {};
    const wf = state.freshnessFile || {};
    const next = nextRefreshInfo();
    return `<div class="row-list">
      <div class="kv"><span>data-octa.json</span><strong>${d.signal_date ? "caricato" : "assente"}</strong></div>
      <div class="kv"><span>freshness.json</span><strong>${wf.generated_at ? esc(wf.message || "caricato") : "fallback UI"}</strong></div>
      <div class="kv"><span>updated</span><strong>${esc(d.updated || "n/d")}</strong></div>
      <div class="kv"><span>engine_error</span><strong>${d.engine_error ? "si" : "no"}</strong></div>
      <div class="kv"><span>expected_signal_date</span><strong>${dateIT(wf.expected_signal_date || expectedSignalDate())}</strong></div>
      <div class="kv"><span>Runner motore</span><strong>${esc(CLOUD_RUNNER.name)}</strong></div>
      <div class="kv"><span>Prossimo refresh</span><strong>${esc(next.label)}</strong></div>
      <div class="kv"><span>n_candidates</span><strong>${esc(d.n_candidates ?? "n/d")}</strong></div>
      <div class="kv"><span>n_active_funds</span><strong>${esc(d.n_active_funds ?? "n/d")}</strong></div>
      <div class="kv"><span>Valuta UI</span><strong>EUR</strong></div>
      <div class="kv"><span>Cambio EUR/USD</span><strong>${fxRate() ? fxRate().toFixed(4) : "n/d"}</strong></div>
      <div class="kv"><span>OCTA sync</span><strong>${state.sync.octa}</strong></div>
    </div>`;
  }
  function tickerKey(ticker) {
    return String(ticker || "").trim().toUpperCase();
  }
  function isIsin(value) {
    return /^[A-Z]{2}[A-Z0-9]{9}[0-9]$/.test(tickerKey(value));
  }
  function instrumentSubline(h) {
    const bits = [];
    if (h?.ticker && tickerKey(h.ticker) !== tickerKey(h.symbol)) bits.push(h.ticker);
    if (h?.symbol && !isIsin(h.symbol) && tickerKey(h.symbol) !== tickerKey(h.ticker)) bits.push(h.symbol);
    if (h?.type) bits.push(h.type);
    if (h?.sector && h.sector !== h.type) bits.push(h.sector);
    return bits.filter(Boolean).join(" · ");
  }
  function findArchiveTicker(ticker) {
    const t = tickerKey(ticker);
    const d = state.octaArchive || {};
    const buckets = [d.signals, d.candidates].filter(Array.isArray);
    for (const bucket of buckets) {
      const found = bucket.find(x => tickerKey(x.ticker || x.symbol) === t);
      if (found) return found;
    }
    return null;
  }
  function findLegacyTicker(ticker) {
    const t = tickerKey(ticker);
    const d = state.legacyData || {};
    const buckets = [d.portfolio, d.top60, d.exited_stocks].filter(Array.isArray);
    for (const bucket of buckets) {
      const found = bucket.find(x => tickerKey(x.ticker || x.symbol) === t);
      if (found) return found;
    }
    return null;
  }
  function octaItem(ticker) {
    const t = tickerKey(ticker);
    const sig = (state.octaData?.signals || []).find(x => tickerKey(x.ticker) === t);
    const cand = (state.octaData?.candidates || []).find(x => tickerKey(x.ticker) === t);
    const pos = state.octaPortfolio?.[t] ? { ticker: t, sector: state.octaPortfolio[t].sector, score: state.octaPortfolio[t].score } : null;
    const archive = findArchiveTicker(t);
    const legacy = findLegacyTicker(t);
    const merged = { ...(legacy || {}), ...(archive || {}), ...(pos || {}), ...(cand || {}), ...(sig || {}), ticker: t };
    if ((!merged.name || tickerKey(merged.name) === t) && (archive?.name || legacy?.name)) merged.name = archive?.name || legacy?.name;
    if (!merged.opportunity_score && merged.score != null) merged.opportunity_score = merged.score;
    return merged;
  }
  function octaRankMap() {
    const out = {};
    (state.octaData?.candidates || []).forEach((c, i) => {
      const t = tickerKey(c.ticker);
      if (t && !out[t]) out[t] = i + 1;
    });
    return out;
  }
  function statusMeta(status) {
    return STATUS_INFO[status] || { label: status || "Status n/d", cls: "info", desc: "Status non presente nel dataset corrente." };
  }
  function scoreValue(v) {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  function signedDelta(v, dec = 1) {
    const n = scoreValue(v);
    if (n == null) return "n.d.";
    return `${n >= 0 ? "+" : ""}${n.toFixed(dec)}`;
  }
  function pointsLabel(v, dec = 1) {
    const n = scoreValue(v);
    if (n == null) return "n.d.";
    return `${n >= 0 ? "+" : ""}${n.toFixed(dec)} pt`;
  }
  function scoreCell(label, val, tip) {
    const n = scoreValue(val);
    const w = n == null ? 0 : Math.max(0, Math.min(100, n));
    return `<div class="score-cell" title="${esc(tip)}">
      <div class="score-top"><span>${esc(label)}</span><strong>${n == null ? "n.d." : Math.round(n)}</strong></div>
      <div class="score-bar"><span style="width:${w}%"></span></div>
      <p>${esc(tip)}</p>
    </div>`;
  }
  function scoreGrid(item) {
    return `<div class="score-grid">
      ${scoreCell("Fondi", item.radar_score, SCORE_TIPS.radar)}
      ${scoreCell("Ingresso", item.entry_score, SCORE_TIPS.entry)}
      ${scoreCell("Priorita", item.opportunity_score ?? item.score, SCORE_TIPS.opp)}
      ${scoreCell("Forza", item.momentum_pct ?? item.components?.momentum, SCORE_TIPS.momentum)}
    </div>`;
  }
  function componentRows(item) {
    const comp = item.components || {};
    const rows = [
      ["Conviction fondi", comp.conviction, "/100"],
      ["Accumulation", comp.accumulation, "/100"],
      ["Crowding", comp.crowding, "/100"],
      ["Copertura fondi", comp.fund_coverage, "%"],
      ["Filing validi", comp.valid_filings, ""],
      ["Fund skill", comp.fund_skill, "/100"],
      ["Qualita", comp.quality, "/100"],
      ["Valore", comp.value, "/100"],
      ["Beta", comp.beta, "/100"],
    ].filter(([,v]) => v != null).map(([k,v,suffix]) => `<div class="kv"><span>${esc(k)}</span><strong>${Math.round(Number(v))}${esc(suffix)}</strong></div>`).join("");
    return rows || `<div class="notice">Componenti score non disponibili per questo titolo.</div>`;
  }
  function detailList(obj) {
    const entries = Object.entries(obj || {}).filter(([,v]) => v != null && v !== "");
    if (!entries.length) return "";
    return entries.slice(0, 8).map(([k,v]) => `<div class="kv"><span>${esc(k.replace(/_/g, " "))}</span><strong>${esc(typeof v === "object" ? JSON.stringify(v) : v)}</strong></div>`).join("");
  }
  function externalSignalState(item) {
    const comp = item.components || {};
    const mode = comp.external_signal_mode || item.external_signal_mode || state.octaData?.external_signal_mode || "off";
    const delta = scoreValue(comp.external_delta ?? item.external_delta);
    if ((mode === "cached" || mode === "full") && comp.market_shadow_cached) return `pesati nello score (${signedDelta(delta)} pt entry), congressional/squeeze in shadow`;
    if (mode === "cached" || mode === "full") return `pesati nello score (${signedDelta(delta)} pt entry)`;
    if (mode === "quick") return "fuori top80: quick path";
    return "in test, non pesati";
  }
  function externalMetric(label, value, meta, opts = {}) {
    const n = scoreValue(value);
    const bar = opts.delta
      ? Math.min(100, Math.abs(n || 0) / 12 * 100)
      : Math.max(0, Math.min(100, n ?? 0));
    const cls = opts.delta ? ((n || 0) >= 0 ? "pos" : "neg") : "";
    const shown = opts.delta ? signedDelta(n) : (n == null ? "n.d." : `${Math.round(n)}/100`);
    return `<div class="impact-row">
      <div><strong>${esc(label)}</strong><span>${esc(meta)}</span></div>
      <b class="${cls}">${esc(shown)}</b>
      <i><em style="width:${bar}%"></em></i>
    </div>`;
  }
  function externalImpactPanel(item) {
    const comp = item.components || {};
    const mode = comp.external_signal_mode || item.external_signal_mode || state.octaData?.external_signal_mode || "off";
    const analystMeta = comp.analyst_cached ? "cache analyst disponibile" : "neutral 50 se cache assente";
    const insiderMeta = comp.insider_cached ? "Form 4 cached" : "neutral 50 se cache assente";
    const peadMeta = comp.pead_cached ? "earnings window attiva" : "nessun boost PEAD oggi";
    const analystVal = scoreValue(comp.analyst) ?? (mode === "cached" ? 50 : null);
    const insiderVal = scoreValue(comp.insider) ?? (mode === "cached" ? 50 : null);
    const rows = [
      externalMetric("Analyst", analystVal, analystMeta),
      externalMetric("Insider", insiderVal, insiderMeta),
      externalMetric("PEAD", comp.pead, peadMeta, { delta: true }),
      externalMetric("Delta entry", comp.external_delta ?? item.external_delta, mode === "cached" ? "impatto finale cached" : "impatto finale", { delta: true }),
    ];
    if (comp.market_shadow_cached) {
      const congMeta = `${comp.congressional_trades ?? 0} trade, net ${comp.congressional_net ?? 0} - shadow`;
      const shortMeta = comp.short_interest_state === "skipped"
        ? "FINRA saltato: dato non disponibile, peso zero"
        : `${comp.squeeze_shadow || "none"} - shadow, non pesa nel live`;
      rows.push(externalMetric("Congress", comp.congressional_shadow, congMeta));
      rows.push(externalMetric("Short interest", comp.short_interest_shadow, shortMeta));
      rows.push(externalMetric("Delta shadow", comp.market_shadow_delta, "scenario congressional/squeeze, non pesa", { delta: true }));
    }
    const text = mode === "cached"
      ? "Questi segnali extra sono gia dentro al punteggio finale e possono cambiare classifica e portafoglio target."
      : "Questi segnali sono visibili, ma oggi non stanno cambiando il punteggio finale.";
    const shadowText = comp.market_shadow_cached
      ? `<div class="notice info">Congressional e squeeze sono in prova: li vedi per capire l'impatto, ma non spostano ancora soldi o classifica.</div>`
      : "";
    return `<section class="detail-section">
      <h3>Segnali extra</h3>
      <div class="notice ${mode === "cached" ? "good" : "warn"}">${esc(text)}</div>
      ${shadowText}
      <div class="impact-list">${rows.join("")}</div>
    </section>`;
  }
  function tickerHistoryPoints(ticker, item = {}) {
    const t = tickerKey(ticker);
    const hist = state.priceHistory[t] || [];
    const currency = state.quotes[t]?.currency || item.currency || "USD";
    return hist.map(row => {
      const ts = Array.isArray(row) ? row[0] : row.t;
      const close = Number(Array.isArray(row) ? row[1] : row.c);
      if (!Number.isFinite(close)) return null;
      const d = new Date(Number(ts) * 1000).toISOString().slice(0, 10);
      const v = toEur(close, currency, fxAtDate(d));
      return v == null ? null : { d, v };
    }).filter(Boolean);
  }
  function tickerChart(ticker, item, context = "octa-detail") {
    const pts = tickerHistoryPoints(ticker, item);
    if (pts.length < 2) return `<div class="notice">Grafico non disponibile per ${esc(ticker)}. Aggiorna prezzi e riapri il dettaglio.</div>`;
    return lineChart(pts, `Grafico ${tickerKey(ticker)}`, v => eur(v, 2), `ticker-${tickerKey(ticker)}`, { context, height: 190, axisFmt: v => eur(v, Math.abs(v) >= 100 ? 0 : 2) });
  }
  async function ensureTickerData(ticker, range = "5y") {
    const t = tickerKey(ticker);
    if (!t || (state.priceHistory[t]?.length && state.quotes[t])) return;
    try {
      const r = await fetch(API.quotes, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ symbols: [t], enrich: [t], priceHistory: [t], historyRange: range, fxHistory: true }) });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const j = await r.json();
      state.quotes = { ...state.quotes, ...(j.quotes || {}) };
      state.info = { ...(state.info || {}), ...(j.info || {}) };
      state.priceHistory = { ...state.priceHistory, ...(j.priceHistory || {}) };
      if (j.priceHistory?.[t]) state.priceHistoryRange[t] = range;
      state.fx = { ...(state.fx || {}), ...(j.fx || {}) };
      state.fxHistory = { ...(state.fxHistory || {}), ...(j.fxHistory || {}) };
    } catch {
      toast(`Storico ${t} non disponibile adesso.`);
    }
  }
  async function openOctaDetail(ticker) {
    const t = tickerKey(ticker);
    if (!t) return;
    state.detailTicker = t;
    $("#info-eyebrow").textContent = "Dettaglio OCTA";
    $("#info-title").textContent = `${t} - score e dati`;
    $("#info-body").innerHTML = `<div class="notice">Apro la scheda ${esc(t)}...</div>`;
    if (!$("#info-dialog").open) $("#info-dialog").showModal();
    renderOctaDetailBody(t);
    ensureTickerData(t).then(() => {
      if ($("#info-dialog").open && state.detailTicker === t) renderOctaDetailBody(t);
    }).catch(() => {});
  }
  function renderOctaDetailBody(ticker) {
    const t = tickerKey(ticker);
    const item = octaItem(t);
    const pos = state.octaPortfolio?.[t];
    const status = statusMeta(item.entry_status);
    const live = quoteUnitEur(t) ?? toEur(item.current_price ?? item.price, item.currency || "USD", fxRate());
    const fundsTotal = state.octaData?.n_active_funds || state.legacyData?.summary?.data_sources?.funds_loaded || 36;
    const funds = item.n_funds_holding != null
      ? `<strong>${esc(item.n_funds_holding)} su ${esc(fundsTotal)}</strong>`
      : `<strong class="muted">non rilevato</strong>`;
    const topFunds = Array.isArray(item.top_funds) && item.top_funds.length
      ? `<div class="fund-list">${item.top_funds.slice(0, 10).map(f => `<span>${esc(f)}</span>`).join("")}</div>`
      : `<div class="muted">Nessun fondo top nel run corrente.</div>`;
    const posHtml = pos ? (() => {
      const shares = Number(pos.shares || 0);
      const value = shares * Number(octaLiveUnitEur(t, pos) || 0);
      const cost = octaEntryCostEur(pos);
      const pnl = value - cost;
      return `<section class="detail-section">
        <h3>La tua posizione</h3>
        <div class="kv"><span>Quantita</span><strong>${shares.toFixed(4)}</strong></div>
        <div class="kv"><span>Valore stimato</span><strong>${eurMaybe(value)}</strong></div>
        <div class="kv"><span>Carico totale</span><strong>${eurMaybe(cost)}</strong></div>
        <div class="kv"><span>P/L</span><strong class="${pnl >= 0 ? "pos" : "neg"}">${eurMaybe(pnl)} · ${pct(cost ? pnl / cost * 100 : 0)}</strong></div>
      </section>`;
    })() : "";
    $("#info-title").textContent = `${t} - ${item.name && item.name !== t ? item.name : "Dettaglio"}`;
    $("#info-body").innerHTML = `
      <div class="detail-hero">
        <div>
          <button class="ticker-link big" data-action="octa-detail" data-ticker="${esc(t)}">${esc(t)}</button>
          <p>${esc(item.name && item.name !== t ? item.name : item.sector || "")}</p>
        </div>
        <div class="detail-badges">
          <span class="badge ${status.cls}">${esc(status.label)}</span>
          <span class="badge info">Score ${esc(Math.round(scoreValue(item.opportunity_score ?? item.score) ?? 0))}/100</span>
          <span class="badge">Prezzo EUR ${eurMaybe(live, 2)}</span>
        </div>
      </div>
      <div class="notice">${esc(status.desc)}${item.reason ? `<br>${esc(item.reason)}` : ""}</div>
      ${scoreGrid(item)}
      <div class="detail-grid">
        <section class="detail-section">
          <h3>Fondi e segnali</h3>
          <div class="kv"><span>Fondi che lo tengono</span>${funds}</div>
          <div class="kv"><span>Segnale principale</span><strong>${esc(item.main_signal || "Non calcolato")}</strong></div>
          ${topFunds}
          <div style="height:10px"></div>
          ${componentRows(item)}
        </section>
        <section class="detail-section">
          <h3>Rischio e note</h3>
          <div class="kv"><span>Settore</span><strong>${esc(item.sector || "Non classificato")}</strong></div>
          <div class="kv"><span>Rischio principale</span><strong>${esc(item.main_risk || "Non calcolato")}</strong></div>
          <div class="kv"><span>Exit trigger</span><strong>${esc(item.exit_trigger || "Non calcolato")}</strong></div>
          <div class="kv"><span>Segnali esterni</span><strong>${esc(externalSignalState(item))}</strong></div>
          ${detailList(item.insider_detail)}
        </section>
        ${externalImpactPanel(item)}
      </div>
      <section class="detail-section full-detail">${tickerChart(t, item)}</section>
      ${posHtml}
      <div class="detail-actions"><button class="button ghost" data-action="ai-ticker" data-ticker="${esc(t)}">${icon("brain")}Spiega con AI</button></div>
      <p class="detail-source">Lettura semplice: guarda prima status, priorita e prezzo. Fondi/forza/extra spiegano perche il motore lo mette alto o basso.</p>`;
  }
  function openOctaLegend() {
    $("#info-eyebrow").textContent = "Legenda OCTA";
    $("#info-title").textContent = "Motivi, score e azioni";
    $("#info-body").innerHTML = `
      <div class="detail-grid">
        <section class="detail-section">
          <h3>Motivo del segnale</h3>
          ${Object.entries(STATUS_INFO).map(([,v]) => `<div class="legend-row"><span class="badge ${v.cls}">${esc(v.label)}</span></div><p class="legend-desc">${esc(v.desc)}</p>`).join("")}
        </section>
        <section class="detail-section">
          <h3>Score</h3>
          <div class="kv"><span>Fondi</span><strong>presenza e accumulo nei fondi osservati</strong></div>
          <div class="kv"><span>Ingresso</span><strong>se il prezzo e in un punto sensato</strong></div>
          <div class="kv"><span>Priorita</span><strong>classifica finale OCTA</strong></div>
          <div class="kv"><span>Forza</span><strong>quanto corre rispetto agli altri</strong></div>
          <div class="kv"><span>Extra score</span><strong>punti aggiunti o tolti dai segnali extra</strong></div>
        </section>
      </div>
      <section class="detail-section">
        <h3>Interazioni</h3>
        <div class="kv"><span>Ticker o score</span><strong>apre dettaglio titolo</strong></div>
        <div class="kv"><span>Fatto</span><strong>registra l'operazione in euro</strong></div>
        <div class="kv"><span>Grafici</span><strong>scorri con il dito e cambia periodo</strong></div>
        <div class="kv"><span>Radar 40</span><strong>espandibile, secondario rispetto ai segnali</strong></div>
      </section>`;
    if (!$("#info-dialog").open) $("#info-dialog").showModal();
  }
  function radarSummary(cands) {
    const top = cands.slice(0, 8).map((c, i) => {
      const item = octaItem(c.ticker);
      const status = statusMeta(c.entry_status || item.entry_status);
      return `<button class="radar-chip ${status.cls}" data-action="octa-detail" data-ticker="${esc(c.ticker)}">
        <span class="radar-rank">#${i + 1}</span>
        <strong>${esc(c.ticker)}</strong>
        <em>${esc(status.label)}</em>
        <b>score ${Math.round(Number(c.score || 0))}</b>
      </button>`;
    }).join("");
    const sectors = Object.entries(cands.reduce((m,c) => {
      const k = c.sector || "Non classificato";
      m[k] = m[k] || { n: 0, sum: 0 };
      m[k].n += 1; m[k].sum += Number(c.score || 0);
      return m;
    }, {})).sort((a,b) => (b[1].sum / b[1].n) - (a[1].sum / a[1].n)).slice(0, 5)
      .map(([k,v]) => `<div class="legend-row"><span>${esc(k)}</span><strong>score medio ${Math.round(v.sum / v.n)}</strong></div>`).join("");
    return `<div class="radar-summary"><div><h3>Top 8 radar</h3><p class="detail-source">La classifica completa resta sotto. Qui vedi subito chi guida e perche e comprabile o no.</p><div class="radar-chips">${top}</div></div><div><h3>Settori forti</h3>${sectors || `<div class="empty">Settori non disponibili.</div>`}</div></div>`;
  }
  function signalActionLabel(action) {
    return action === "SELL" ? "Vendi" : action === "BUY" ? "Compra" : action || "Segnale";
  }
  function signalCard(s) {
    const done = isSignalDone(s);
    const cls = s.action === "SELL" ? "sell" : "buy";
    const live = quoteUnitEur(s.ticker);
    const px = live ?? toEur(s.current_price, "USD", fxRate());
    const status = statusMeta(s.entry_status);
    return `<article class="signal-card ${cls}">
      <div class="signal-main">
        <div class="signal-title"><button class="ticker-link" data-action="octa-detail" data-ticker="${esc(s.ticker)}">${esc(s.ticker)}</button><span class="badge ${s.action === "SELL" ? "bad" : "good"}">${esc(signalActionLabel(s.action))}</span><button class="badge-button ${status.cls}" data-action="octa-detail" data-ticker="${esc(s.ticker)}">${esc(status.label)}</button>${done ? `<span class="badge good">eseguito</span>` : ""}</div>
        <div class="signal-meta">${esc(s.name || s.sector || "")}<br><strong>Motivo:</strong> ${esc(status.desc)}${s.reason ? `<br><span class="muted">Nota motore: ${esc(s.reason)}</span>` : ""}<br>Prezzo EUR ${eurMaybe(px, 2)} · priorita ${esc(s.score ?? "n/d")}</div>
      </div>
      <div class="toolbar"><button class="signal-score" data-action="octa-detail" data-ticker="${esc(s.ticker)}"><strong>${Math.round(Number(s.score || 0))}</strong><span>priorita</span></button><button class="button primary" data-action="trade" data-signal="${esc(s.id)}" ${done ? "disabled" : ""}>${icon("check")}Fatto</button><button class="button ghost" data-action="ai-ticker" data-ticker="${esc(s.ticker)}">${icon("brain")}AI</button></div>
    </article>`;
  }
  function chartRangeValue(id) {
    return state.chartRanges[id] || "MAX";
  }
  function filterChartRange(points, rangeKey) {
    const clean = (points || []).filter(p => p.d && Number.isFinite(Number(p.v))).sort((a,b) => String(a.d).localeCompare(String(b.d)));
    if (clean.length < 2) return `<div class="empty">Grafico disponibile quando ci sono almeno due punti storici.</div>`;
    const spec = CHART_RANGES.find(r => r[0] === rangeKey) || CHART_RANGES[CHART_RANGES.length - 1];
    if (!spec[2]) return clean;
    const end = new Date(clean[clean.length - 1].d + "T00:00:00Z");
    const start = new Date(end);
    start.setUTCDate(start.getUTCDate() - spec[2]);
    let out = clean.filter(p => new Date(p.d + "T00:00:00Z") >= start);
    if (out.length < 2) out = clean.slice(Math.max(0, clean.length - 2));
    return out;
  }
  function lineChart(points, title, valueFmt, chartId = title.toLowerCase().replace(/[^a-z0-9]+/g, "-"), opts = {}) {
    const rangeKey = chartRangeValue(chartId);
    const clean = filterChartRange(points, rangeKey);
    if (!Array.isArray(clean)) return clean;
    if (clean.length < 2) return `<div class="empty">Grafico disponibile quando ci sono almeno due punti storici.</div>`;
    const compareFiltered = Array.isArray(opts.comparePoints) ? filterChartRange(opts.comparePoints, rangeKey) : [];
    const compareClean = Array.isArray(compareFiltered) ? compareFiltered : [];
    const H = Number(opts.height || 224), padL = 58, padR = 14, padT = 18, padB = 30;
    const W = Number(opts.width || 720);
    const primaryVals = clean.map(p => Number(p.v));
    const compareVals = compareClean.map(p => Number(p.v));
    const vals = primaryVals.concat(compareVals);
    const min = Math.min(...vals), max = Math.max(...vals), range = max - min || 1;
    const xFor = (arr, i) => padL + i * (W - padL - padR) / (arr.length - 1);
    const x = i => xFor(clean, i);
    const y = v => padT + (1 - (v - min) / range) * (H - padT - padB);
    const d = clean.map((p,i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(Number(p.v)).toFixed(1)}`).join(" ");
    const area = `M${x(0).toFixed(1)} ${H-padB} ${clean.map((p,i) => `L${x(i).toFixed(1)} ${y(Number(p.v)).toFixed(1)}`).join(" ")} L${x(clean.length-1).toFixed(1)} ${H-padB} Z`;
    const first = primaryVals[0], last = primaryVals[primaryVals.length - 1];
    const manualChange = Number(opts.changePct);
    const change = Number.isFinite(manualChange) ? manualChange : (first ? (last / first - 1) * 100 : 0);
    const col = change >= 0 ? "#42d392" : "#ff6b6b";
    const fmt = valueFmt || (v => eur(v));
    const axisFmt = opts.axisFmt || compactEur;
    // griglia: SOLO linee nell'SVG. Numeri e date = overlay HTML (nitidi, mai stirati).
    const grid = [0, .25, .5, .75, 1].map(f => {
      const yy = padT + f * (H - padT - padB);
      return `<line x1="${padL}" y1="${yy.toFixed(1)}" x2="${W-padR}" y2="${yy.toFixed(1)}"></line>`;
    }).join("");
    const yLabels = [0, .5, 1].map(f => {
      const val = min + (max - min) * (1 - f);
      const yy = padT + f * (H - padT - padB);
      return `<span style="top:${(yy / H * 100).toFixed(2)}%">${esc(axisFmt(val))}</span>`;
    }).join("");
    const xLabels = [0, .5, 1].map(f => {
      const i = Math.min(clean.length - 1, Math.round((clean.length - 1) * f));
      const leftPct = (x(i) / W * 100).toFixed(2);
      const tx = f === 0 ? "0" : f === 1 ? "-100%" : "-50%";
      return `<span style="left:${leftPct}%;transform:translateX(${tx})">${dateIT(clean[i].d)}</span>`;
    }).join("");
    const dotLeft = (x(clean.length - 1) / W * 100).toFixed(2);
    const dotTop = (y(last) / H * 100).toFixed(2);
    const dates = "";
    const context = opts.context ? ` data-context="${esc(opts.context)}"` : "";
    const rangeTitles = { "1D": "1 giorno", "1W": "1 settimana", "1M": "1 mese", "3M": "3 mesi", "1Y": "1 anno", "5Y": "5 anni", MAX: "Massimo disponibile" };
    const controls = CHART_RANGES.map(([key, label]) => `<button class="${key === rangeKey ? "active" : ""}" data-action="chart-range" data-chart="${esc(chartId)}" data-range="${key}" title="${esc(rangeTitles[key] || label)}" aria-label="${esc(rangeTitles[key] || label)}"${context}>${label}</button>`).join("");
    const comparePath = compareClean.length >= 2
      ? compareClean.map((p,i) => `${i ? "L" : "M"}${xFor(compareClean, i).toFixed(1)} ${y(Number(p.v)).toFixed(1)}`).join(" ")
      : "";
    const compareSvg = comparePath ? `<path d="${comparePath}" fill="none" stroke="${esc(opts.compareColor || "#83a8ff")}" stroke-width="2.2" stroke-dasharray="6 5" vector-effect="non-scaling-stroke"></path>` : "";
    const legend = comparePath ? `<div class="chart-legend"><span><i style="background:${col}"></i>${esc(opts.primaryLabel || "Portafoglio")}</span><span><i class="dash" style="background:${esc(opts.compareColor || "#83a8ff")}"></i>${esc(opts.compareLabel || "Confronto")}</span></div>` : "";
    chartStore.set(chartId, { points: clean, fmt });
    return `<div class="chart-card ${opts.cleanAxes ? "clean-chart" : ""}" data-chart="${esc(chartId)}"><div class="chart-head"><div><h3>${esc(title)}</h3><p>${dateIT(clean[0].d)} - ${dateIT(clean[clean.length-1].d)} · ${clean.length} punti</p></div><span class="badge ${change >= 0 ? "good" : "bad"}">${opts.changeLabel ? esc(opts.changeLabel) : pct(change)}</span></div><div class="chart-ranges">${controls}</div>${legend}<div class="chart-scroll" aria-label="${esc(title)}"><svg class="line-chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"><g class="chart-grid">${grid}</g><path d="${area}" fill="${col}" opacity="0.16"></path><path d="${d}" fill="none" stroke="${col}" stroke-width="3" vector-effect="non-scaling-stroke"></path>${compareSvg}</svg><div class="chart-y-axis">${yLabels}</div><div class="chart-x-axis">${xLabels}</div><div class="chart-dot" style="left:${dotLeft}%;top:${dotTop}%;background:${col}"></div><div class="chart-marker" hidden></div><div class="chart-tip" hidden></div></div><div class="chart-foot"><span>${dateIT(clean[0].d)} · ${fmt(first)}</span><strong>${dateIT(clean[clean.length - 1].d)} · ${fmt(last)}</strong></div></div>`;
  }
  function octaSeries() {
    const entries = Object.entries(state.octaPortfolio || {}).map(([ticker, pos]) => {
      const shares = Number(pos.shares || 0);
      if (!shares) return null;
      const entryDay = String(pos.entry_date || todayISO()).slice(0, 10);
      const hist = state.priceHistory[ticker] || [];
      const history = [];
      if (hist.length) {
        const currency = state.quotes[ticker]?.currency || "USD";
        for (const row of hist) {
          const ts = Array.isArray(row) ? row[0] : row.t;
          const close = Number(Array.isArray(row) ? row[1] : row.c);
          if (!Number.isFinite(close)) continue;
          const d = new Date(Number(ts) * 1000).toISOString().slice(0, 10);
          if (d < entryDay) continue;
          const closeEur = toEur(close, currency, fxAtDate(d, pos.fx));
          if (closeEur != null) history.push({ d, v: closeEur });
        }
      }
      history.sort((a,b) => a.d.localeCompare(b.d));
      return { ticker, pos, shares, entryDay, entry: octaEntryUnitEur(pos), history, i: 0, last: null };
    }).filter(Boolean);
    if (!entries.length) return [];
    const dateSet = new Set([todayISO()]);
    for (const e of entries) {
      dateSet.add(e.entryDay);
      e.history.forEach(p => dateSet.add(p.d));
    }
    const out = [];
    for (const day of [...dateSet].sort()) {
      let total = 0;
      for (const e of entries) {
        if (day < e.entryDay) continue;
        while (e.i < e.history.length && e.history[e.i].d <= day) {
          e.last = e.history[e.i].v;
          e.i += 1;
        }
        const live = day === todayISO() ? octaLiveUnitEur(e.ticker, e.pos) : null;
        const unit = live ?? e.last ?? e.entry;
        if (unit != null) total += e.shares * unit;
      }
      if (total > 0) out.push({ d: day, v: total });
    }
    const stats = octaStats();
    if (stats.value > 0) {
      const today = todayISO();
      const found = out.find(p => p.d === today);
      if (found) found.v = stats.value;
      else out.push({ d: today, v: stats.value });
    }
    return out.sort((a,b) => a.d.localeCompare(b.d));
  }
  function octaPerformanceChart() {
    const pts = octaSeries();
    const stats = octaStats();
    if (pts.length < 2) return `<div class="notice">Andamento OCTA pronto: servono quotazioni storiche, le carico appena disponibili.</div>`;
    return `<div class="octa-chart-block">
      ${lineChart(pts, "Valore portafoglio OCTA", v => eur(v, 0), "octa", { height: 198, changePct: stats.pnlPct, changeLabel: pct(stats.pnlPct), axisFmt: compactEur, cleanAxes: true })}
      <div class="octa-metrics">
        <div class="metric compact"><span>Valore stimato</span><strong>${eurMaybe(stats.value, 0)}</strong></div>
        <div class="metric compact"><span>Investito</span><strong>${eurMaybe(stats.cost, 0)}</strong></div>
        <div class="metric compact"><span>P/L stimato</span><strong class="${stats.pnl >= 0 ? "pos" : "neg"}">${eurMaybe(stats.pnl, 0)} · ${pct(stats.pnlPct)}</strong></div>
        <div class="metric compact"><span>Posizioni</span><strong>${Object.keys(state.octaPortfolio || {}).length}</strong></div>
      </div>
    </div>`;
  }
  function octaStats() {
    let value = 0, cost = 0;
    for (const [t, p] of Object.entries(state.octaPortfolio || {})) {
      const shares = Number(p.shares || 0);
      const px = octaLiveUnitEur(t, p);
      value += shares * Number(px || 0);
      cost += octaEntryCostEur(p);
    }
    const pnl = value - cost;
    return { value, cost, pnl, pnlPct: cost ? pnl / cost * 100 : 0 };
  }
  function octaHoldingsMini() {
    const ranks = octaRankMap();
    const rows = Object.entries(state.octaPortfolio || {}).slice(0, 6).map(([t, p]) => {
      const q = octaLiveUnitEur(t, p);
      const value = Number(p.shares || 0) * Number(q || 0);
      const rank = ranks[tickerKey(t)];
      return `<div class="kv"><span><button class="inline-link" data-action="octa-detail" data-ticker="${esc(t)}">${esc(t)}</button>${rank ? ` <span class="rank-badge">#${rank}</span>` : ""}</span><strong>${eurMaybe(value)}</strong></div>`;
    }).join("");
    return rows || `<div class="empty">Nessuna posizione OCTA registrata.</div>`;
  }
  function backtestMini() {
    return `<div class="row-list"><div class="kv"><span>Profilo validato</span><strong>fast path</strong></div><div class="kv"><span>Segnali esterni live</span><strong>disattivati</strong></div><div class="kv"><span>Fonte</span><strong>backtest.json</strong></div></div>`;
  }
  function signalPills(items, cls) {
    return items.map(([name, desc]) => `<div class="signal-pill ${cls}"><strong>${esc(name)}</strong><span>${esc(desc)}</span></div>`).join("");
  }
  function liveSignalProfilePanel(compact = false) {
    const mode = state.octaData?.external_signal_mode || "off";
    const active = mode === "cached"
      ? [
          ...LIVE_SIGNAL_PROFILE.active,
          ["Insider Form 4", "Cache pesata nello score"],
          ["Earnings / PEAD", "Boost cached se in finestra"],
          ["Analyst", "Consensus cached o neutral"],
        ]
      : LIVE_SIGNAL_PROFILE.active;
    const inactive = mode === "cached"
      ? [
          ["Congressional", "Shadow test: report e cache, peso zero"],
          ["Squeeze", "Shadow test FINRA, moltiplicatore spento"],
        ]
      : LIVE_SIGNAL_PROFILE.inactive;
    const badge = mode === "cached" ? "Profilo completo" : "Profilo rapido";
    const desc = mode === "cached"
      ? "Profilo cached attivo: radar, momentum, filtri tecnici e segnali esterni cached pesano nello score."
      : "Profilo fast path attivo: score da radar 13F, momentum e filtri tecnici.";
    return `<div class="signal-profile ${compact ? "compact" : ""}">
      <div class="signal-profile-head">
        <div>
          <h2>Come decide OCTA</h2>
          <p>${esc(desc)}</p>
        </div>
        <span class="badge ${mode === "cached" ? "good" : "info"}">${esc(badge)}</span>
      </div>
      <div class="signal-profile-grid">
        <section>
          <h3>Pesano davvero</h3>
          <div class="signal-pill-list">${signalPills(active, "on")}</div>
        </section>
        <section>
          <h3>${mode === "cached" ? "In osservazione" : "Presenti ma spenti"}</h3>
          <div class="signal-pill-list">${signalPills(inactive, "off")}</div>
        </section>
      </div>
    </div>`;
  }
  function viewOcta() {
    const d = state.octaData || {};
    const signals = d.signals || [];
    const cands = d.candidates || [];
    const pending = signals.filter(s => !isSignalDone(s));
    const buys = pending.filter(s => s.action === "BUY").length;
    const sells = pending.filter(s => s.action === "SELL").length;
    const stats = octaStats();
    const f = freshness();
    return `
      <section class="panel full octa-hero">
        <div class="panel-head">
          <div><h2>OCTA</h2><p>Prima segnali e portafoglio reale. Radar, storico e motore restano sotto, apribili quando servono.</p></div>
          <div class="toolbar"><button class="button primary" data-action="run-engines" data-mode="all">${icon("play")}Run tutto</button><button class="button ghost" data-action="refresh-all">${icon("refresh")}Aggiorna dati</button><button class="button" data-action="ai-octa">${icon("brain")}AI OCTA</button></div>
        </div>
        <div class="metric-row octa-overview">
          <div class="metric compact"><span>Segnale</span><strong>${dateIT(d.signal_date)}</strong></div>
          <div class="metric compact"><span>Da fare</span><strong>${pending.length}</strong><small>${buys} buy · ${sells} sell</small></div>
          <div class="metric compact"><span>Portafoglio</span><strong>${eurMaybe(stats.value, 0)}</strong></div>
          <div class="metric compact"><span>Risultato</span><strong class="${stats.pnl >= 0 ? "pos" : "neg"}">${pct(stats.pnlPct)}</strong><small>${eurMaybe(stats.pnl, 0)}</small></div>
        </div>
        <div class="octa-status-line">
          <span class="badge ${f.cls}">${esc(f.label)}</span>
          <span class="muted">${esc(d.engine_error ? "engine_error: si" : "engine_error: no")} · ${esc(d.regime?.status || "regime n/d")} · ${esc(cands.length)} candidati radar</span>
        </div>
      </section>
      <section class="panel full"><div class="panel-head"><div><h2>Segnali da gestire</h2><p>Conferma solo quello che hai davvero eseguito sul broker.</p></div><button class="button ghost" data-action="octa-legend">${icon("chart")}Legenda</button></div><div class="signal-list">${signals.map(signalCard).join("") || `<div class="empty">Nessun segnale nel file corrente.</div>`}</div></section>
      <section class="panel full"><div class="panel-head"><div><h2>Portafoglio OCTA</h2><p>Valore, P/L e 8 posizioni registrate, sempre in euro.</p></div><button class="button ghost" data-action="ai-octa">${icon("brain")}Controllo AI</button></div>${octaPerformanceChart()}<div style="height:12px"></div>${octaPortfolioTable()}</section>
      <section class="panel full octa-secondary"><details><summary>Radar 40 e classifica completa</summary><div class="octa-details-body">${radarSummary(cands)}<div style="height:12px"></div>${candidateTable(cands)}</div></details></section>
      <section class="panel full octa-secondary"><details><summary>Come decide OCTA</summary><div class="octa-details-body">${liveSignalProfilePanel(true)}</div></details></section>
      <section class="panel full octa-secondary"><details><summary>Storico operazioni</summary><div class="octa-details-body">${octaHistoryTable()}<div style="height:12px"></div><button class="button ghost" data-action="reset-octa-local">Reset locale</button></div></details></section>`;
  }
  function octaPortfolioTable() {
    const ranks = octaRankMap();
    const rows = Object.entries(state.octaPortfolio || {}).map(([t, p]) => {
      const shares = Number(p.shares || 0);
      const px = octaLiveUnitEur(t, p);
      const value = shares * Number(px || 0);
      const cost = octaEntryCostEur(p);
      const pnl = value - cost;
      const pnlPct = cost ? pnl / cost * 100 : 0;
      const item = octaItem(t);
      const rank = ranks[tickerKey(t)];
      return `<tr><td><div class="holding-title"><button class="table-link" data-action="octa-detail" data-ticker="${esc(t)}">${esc(item.name && item.name !== t ? item.name : t)}</button>${rank ? `<span class="rank-badge">#${rank}</span>` : `<span class="rank-badge muted">fuori radar</span>`}</div><div class="muted">${esc(t)}${p.sector ? " · " + esc(p.sector) : ""}</div></td><td class="right">${shares.toFixed(4)}</td><td class="right">${eurMaybe(px, 2)}</td><td class="right">${eurMaybe(value)}</td><td class="right"><span class="badge ${pnl >= 0 ? "good" : "bad"}">${pct(pnlPct)}</span></td></tr>`;
    }).join("");
    return rows ? `<table class="table"><thead><tr><th>Posizione</th><th class="right">Qta</th><th class="right">Prezzo €</th><th class="right">Valore</th><th class="right">Risultato</th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty">Quando confermi i BUY, il portafoglio appare qui.</div>`;
  }
  function octaHistoryTable() {
    const rows = (state.octaHistory || []).slice(0, 80).map(h => {
      const px = Number(h.price_eur) || toEur(h.price, "USD", h.fx || fxRate());
      const total = Number(h.cost_total || h.proceeds || 0);
      return `<tr><td><strong>${esc(h.ticker)}</strong><div class="muted">${dateIT(h.date)}</div></td><td>${esc(h.action)}</td><td class="right">${Number(h.qty || 0).toFixed(4)}</td><td class="right">${eurMaybe(px, 2)}</td><td class="right">${total ? eurMaybe(total) : "n/d"}</td></tr>`;
    }).join("");
    return rows ? `<table class="table"><thead><tr><th>Ticker</th><th>Azione</th><th class="right">Qta</th><th class="right">Prezzo €</th><th class="right">Totale</th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty">Nessuna operazione OCTA registrata.</div>`;
  }
  function candidateTable(cands) {
    const rows = cands.slice(0, 40).map(c => {
      const item = octaItem(c.ticker);
      const status = statusMeta(c.entry_status);
      const ext = scoreValue(c.external_delta ?? item.external_delta ?? item.components?.external_delta);
      return `<tr><td><button class="table-link" data-action="octa-detail" data-ticker="${esc(c.ticker)}">${esc(c.ticker)}</button><div class="muted">${esc(item.name && item.name !== c.ticker ? item.name : c.sector || "")}</div></td><td class="right">${esc(c.score ?? "")}</td><td><button class="badge-button ${status.cls}" data-action="octa-detail" data-ticker="${esc(c.ticker)}">${esc(status.label)}</button></td><td class="right"><span class="${(ext || 0) >= 0 ? "pos" : "neg"}">${esc(pointsLabel(ext))}</span></td><td class="right hide-sm">${c.momentum_pct != null ? esc(Math.round(Number(c.momentum_pct))) + "/100" : "n.d."}</td></tr>`;
    }).join("");
    return rows ? `<div class="table-note">Extra score = punti aggiunti o tolti dai segnali extra. Forza = momentum relativo del titolo.</div><table class="table"><thead><tr><th>Ticker</th><th class="right">Priorita</th><th>Motivo</th><th class="right">Extra score</th><th class="right hide-sm">Forza</th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty">Radar 40 non disponibile.</div>`;
  }

  const BENCH_PRESETS = [
    { sym: "SXR8.DE", label: "S&P 500" },
    { sym: "EUNL.DE", label: "MSCI World" },
    { sym: "VWCE.DE", label: "Globale" },
    { sym: "XGLE.DE", label: "Bond euro" },
  ];
  function benchName(sym) {
    const s = String(sym || "").toUpperCase();
    return BENCH_PRESETS.find(b => b.sym === s)?.label || s || "Indice";
  }
  function getTargetFor(name) {
    return TARGET_WEIGHTS[String(name || "").trim().toLowerCase()] || null;
  }
  function txType(tx) {
    const raw = String(tx?.type || "BUY").toUpperCase();
    if (raw === "DIVIDEND") return "DIV";
    if (raw === "DEPOSIT") return "CASH";
    return raw;
  }
  function benchPriceAt(bench, day) {
    const hist = bench?.history || [];
    const target = String(day || todayISO()).slice(0, 10);
    let best = null;
    for (const row of hist) {
      const ts = Array.isArray(row) ? row[0] : row.t;
      const close = Number(Array.isArray(row) ? row[1] : row.c);
      if (!Number.isFinite(close)) continue;
      const d = new Date(Number(ts) * 1000).toISOString().slice(0, 10);
      if (d <= target) best = { d, close };
      else break;
    }
    if (!best) return null;
    return toEur(best.close, bench.currency || "EUR", fxAtDate(best.d));
  }
  function benchUnitsAt(txs, bench, asOf) {
    const day = String(asOf || todayISO()).slice(0, 10);
    let units = 0;
    for (const tx of (txs || []).slice().sort((a,b) => String(a.date || "").localeCompare(String(b.date || "")))) {
      const d = String(tx.date || "").slice(0, 10);
      if (d && d > day) continue;
      const type = txType(tx);
      const qty = Number(tx.qty ?? tx.quantity ?? 0);
      const px = Number(tx.price ?? tx.amount ?? 0);
      const amount = type === "CASH" || type === "DIV" ? px : qty * px;
      const bp = benchPriceAt(bench, d || day);
      if (!(amount > 0) || !(bp > 0)) continue;
      if (type === "BUY" || type === "CASH") units += amount / bp;
      if (type === "SELL") units -= amount / bp;
    }
    return Math.max(0, units);
  }
  function benchmarkSeriesForPortfolio(points) {
    const bench = state.openPf?.data?.bench;
    if (!bench?.history?.length) return [];
    const txs = state.openPf?.data?.transactions || [];
    return (points || []).map(p => {
      const px = benchPriceAt(bench, p.d);
      const units = benchUnitsAt(txs, bench, p.d);
      return px && units ? { d: p.d, v: px * units } : null;
    }).filter(Boolean);
  }
  function benchmarkView(st) {
    if (!st.holdings.length) return "";
    const current = state.openPf?.data?.benchmark;
    const bench = state.openPf?.data?.bench;
    if (!current) {
      const chips = BENCH_PRESETS.map(b => `<button class="button ghost" data-action="set-benchmark" data-symbol="${esc(b.sym)}">${esc(b.label)}</button>`).join("");
      return `<section class="detail-section"><div class="panel-head"><div><h3>Confronto indice</h3><p>Stessi flussi investiti in un indice, per capire se il portafoglio sta facendo meglio o peggio.</p></div></div><div class="toolbar">${chips}<button class="button ghost" data-action="set-benchmark" data-symbol="__custom">Altro</button></div></section>`;
    }
    if (!bench?.history?.length || !(st.invested > 0)) {
      return `<section class="detail-section"><div class="panel-head"><div><h3>Confronto con ${esc(benchName(current))}</h3><p>Premi aggiorna prezzi per scaricare lo storico dell'indice.</p></div><button class="button ghost" data-action="clear-benchmark">Cambia</button></div></section>`;
    }
    const bp = benchPriceAt(bench, todayISO());
    const bv = bp ? benchUnitsAt(state.openPf.data.transactions, bench, todayISO()) * bp : 0;
    const gp = st.invested ? (st.value / st.invested - 1) * 100 : 0;
    const gb = st.invested ? (bv / st.invested - 1) * 100 : 0;
    return `<section class="detail-section"><div class="panel-head"><div><h3>Confronto con ${esc(benchName(current))}</h3><p>Calcolato dalla prima operazione disponibile.</p></div><button class="button ghost" data-action="clear-benchmark">Cambia</button></div><div class="row-list">
      <div class="kv"><span>Il tuo portafoglio</span><strong class="${gp >= 0 ? "pos" : "neg"}">${eur(st.value)} · ${pct(gp)}</strong></div>
      <div class="kv"><span>Stessi importi su indice</span><strong class="${gb >= 0 ? "pos" : "neg"}">${eur(bv)} · ${pct(gb)}</strong></div>
    </div></section>`;
  }

  function portfolioArchiveCard(p) {
    const open = state.openPf?.id === p.id;
    return `<article class="pf-card ${open ? "open" : ""}">
      <div>
        <div class="pf-card-title"><h3>${esc(p.name)}</h3><span class="badge">${icon("lock")}PIN</span></div>
        <p>Creato ${timeIT(p.created)}${p.updated ? ` · aggiornato ${timeIT(p.updated)}` : ""}</p>
      </div>
      <button class="button ${open ? "ghost" : "primary"}" data-action="open-pf" data-id="${esc(p.id)}">${open ? "Aperto" : "Apri"}</button>
    </article>`;
  }
  function viewPortfolios() {
    const list = state.tracker.portfolios || [];
    const cards = list.map(portfolioArchiveCard).join("");
    if (!state.openPf) {
      return `<section class="panel full pf-home">
        <div class="pf-home-hero">
          <div>
            <p class="eyebrow">Area riservata</p>
            <h2>Portafogli</h2>
            <p>Archivi cifrati con PIN locale, movimenti, prezzi, grafici, benchmark, import Fineco e analisi AI.</p>
          </div>
          <div class="pf-home-actions">
            <button class="button primary" data-action="new-pf">${icon("plus")}Nuovo portafoglio</button>
            <button class="button ghost" data-action="import-tracker-backup">${icon("upload")}Importa backup</button>
          </div>
        </div>
        <div class="pf-home-stats">
          <div><span>Archivi</span><strong>${list.length}</strong></div>
          <div><span>Sicurezza</span><strong>PIN + cifratura</strong></div>
          <div><span>Cloud</span><strong>${localStorage.getItem("tracker_sync_token") ? "sync attivo" : "locale"}</strong></div>
        </div>
        <div class="pf-card-grid">${cards || `<div class="empty">Nessun portafoglio creato. Crea il primo archivio o importa un backup.</div>`}</div>
      </section>`;
    }
    return `
      <section class="panel sidebar pf-archive-panel">
        <div class="panel-head"><div><h2>Archivi</h2><p>Scegli un portafoglio o creane uno nuovo.</p></div><button class="button primary" data-action="new-pf">${icon("plus")}Nuovo</button></div>
        <div class="row-list">${cards}</div>
      </section>
      <section class="panel wide pf-bank-panel">${openPortfolioView()}</section>`;
  }
  function openPortfolioView() {
    const st = portfolioStats(state.openPf);
    const rows = st.holdings.map(h => `<tr>
      <td><button class="table-link" data-action="holding-detail" data-symbol="${esc(h.symbol)}">${esc(h.name || h.ticker || h.symbol)}</button><div class="muted">${esc(instrumentSubline(h))} · qta ${h.qty.toFixed(4)}</div></td>
      <td class="right hide-sm">${pctWeight(h.weight)}</td>
      <td class="right">${eur(h.value)}</td>
      <td class="right"><span class="badge ${h.pl >= 0 ? "good" : "bad"}">${pct(h.plPct)}</span>${h.dayPct != null ? `<div class="muted">oggi ${pct(h.dayPct)}</div>` : ""}</td>
    </tr>`).join("");
    const bestWorst = st.holdings.length >= 2 ? (() => {
      const sorted = st.holdings.slice().sort((a,b) => b.plPct - a.plPct);
      const best = sorted[0], worst = sorted[sorted.length - 1];
      return `<div class="grid-2 compact-grid"><div class="notice good"><strong>Migliore</strong><br>${esc(best.name || best.symbol)} · ${pct(best.plPct)}</div><div class="notice bad"><strong>Peggiore</strong><br>${esc(worst.name || worst.symbol)} · ${pct(worst.plPct)}</div></div>`;
    })() : "";
    const aiCallout = `<section class="detail-section ai-callout pf-ai-callout"><div><h3>${icon("brain")}Controllo AI</h3><p>Una lettura sintetica su rischio, concentrazione e riequilibri possibili.</p></div><button class="button primary" data-action="ai-pf">Analizza</button></section>`;
    const secondary = `
      <section class="pf-secondary">
        <details><summary>Benchmark e confronto</summary><div class="pf-details-body">${benchmarkView(st) || `<div class="empty">Aggiungi posizioni per confrontare il portafoglio con un indice.</div>`}</div></details>
        <details><summary>Allocazione e pesi</summary><div class="pf-details-body">${allocationView(st.holdings) || ""}${targetWeightsView(st) || ""}${bestWorst || ""}</div></details>
        <details><summary>Movimenti registrati</summary><div class="pf-details-body">${txTable(state.openPf.data.transactions) || `<div class="empty">Nessun movimento registrato.</div>`}</div></details>
        <details><summary>Impostazioni portafoglio</summary><div class="pf-details-body"><div class="toolbar"><button class="button ghost" data-action="rename-pf">${icon("edit")}Rinomina</button><button class="button danger" data-action="delete-pf">${icon("trash")}Elimina</button></div></div></details>
      </section>`;
    return `
      <div class="pf-bank-hero">
        <div>
          <p class="eyebrow">Portafoglio aperto</p>
          <h2>${esc(state.openPf.name)}</h2>
          <p>${st.holdings.length} posizioni · ${state.openPf.data.transactions.length} movimenti · valori in euro</p>
        </div>
        <div class="pf-bank-value">
          <span>Valore stimato</span>
          <strong>${eur(st.value)}</strong>
          <em class="${st.gain >= 0 ? "pos" : "neg"}">${eur(st.gain)} · ${pct(st.gainPct)}</em>
        </div>
      </div>
      <div class="pf-action-bar">
        <button class="button primary" data-action="add-tx">${icon("plus")}Movimento</button>
        <button class="button" data-action="refresh-pf">${icon("refresh")}Prezzi</button>
        <button class="button ghost" data-action="import-pf">${icon("upload")}Importa / aggiorna</button>
        <button class="button ghost" data-action="ai-pf">${icon("brain")}AI</button>
      </div>
      <div class="metric-row pf-metrics"><div class="metric"><span>Investito</span><strong>${eur(st.invested)}</strong></div><div class="metric"><span>Rendimento</span><strong class="${st.gainPct >= 0 ? "pos" : "neg"}">${pct(st.gainPct)}</strong></div><div class="metric"><span>Liquidita</span><strong>${eur(st.cash)}</strong><small>dividendi registrati ${eur(st.dividends)}</small></div><div class="metric"><span>Posizioni</span><strong>${st.holdings.length}</strong></div></div>
      ${portfolioPerformanceChart(st)}
      ${aiCallout}
      <section class="detail-section full-detail pf-positions">
        <div class="panel-head"><div><h3>Posizioni</h3><p>Apri una riga per dettaglio, grafico, prezzo manuale e operazioni rapide.</p></div></div>
        ${rows ? `<table class="table pf-table"><thead><tr><th>Strumento</th><th class="right hide-sm">Peso</th><th class="right">Valore</th><th class="right">Risultato</th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty">Aggiungi il primo movimento.</div>`}
      </section>
      ${secondary}`;
  }
  function portfolioSeriesFromHistory(st) {
    const raw = state.openPf?.data?.valueHistory || [];
    const pts = raw.map(p => ({
      d: String(p.d || p.date || p.ts || "").slice(0, 10),
      v: Number(p.v ?? p.value ?? p.total ?? p.wealth ?? 0),
    })).filter(p => p.d && Number.isFinite(p.v) && p.v > 0);
    if (pts.length >= 2) return pts;
    if (st.value > 0 && st.invested > 0) {
      const firstDate = (state.openPf?.data?.transactions || []).map(t => String(t.date || "").slice(0,10)).filter(Boolean).sort()[0] || todayISO();
      return [{ d: firstDate, v: st.invested }, { d: todayISO(), v: st.value }];
    }
    return [];
  }
  function portfolioPerformanceChart(st) {
    const pts = portfolioSeriesFromHistory(st);
    if (pts.length < 2) return `<div class="empty">Grafico andamento disponibile dopo aver aggiunto movimenti o snapshot valore.</div>`;
    const compare = benchmarkSeriesForPortfolio(pts);
    return lineChart(pts, "Andamento portafoglio", v => eur(v, 0), `portfolio-${state.openPf?.id || "open"}`, { comparePoints: compare, primaryLabel: "Portafoglio", compareLabel: benchName(state.openPf?.data?.benchmark), cleanAxes: true, axisFmt: compactEur, height: 198 });
  }
  function txTable(txs) {
    const info = state.openPf?.data?.instrumentInfo || {};
    const rows = (txs || []).slice().reverse().slice(0, 80).map(tx => {
      const qty = Number(tx.qty ?? tx.quantity ?? 0);
      const px = Number(tx.price ?? tx.amount ?? 0);
      const sym = tickerKey(tx.symbol);
      const q = state.quotes[sym];
      const resolved = q?.resolved && tickerKey(q.resolved) !== sym ? q.resolved : "";
      const quoteInfo = state.info[sym] || state.info[resolved] || {};
      const meta = info[sym] || {};
      const typeLabel = ({ BUY: "Acquisto", SELL: "Vendita", DIV: "Dividendo", CASH: "Cassa", SNAP: "Fotografia" })[String(tx.type || "").toUpperCase()] || tx.type;
      const display = meta.name || quoteInfo.name || tx.name || resolved || sym || typeLabel;
      const subBits = [resolved || (!isIsin(sym) ? sym : ""), dateIT(tx.date)].filter(Boolean);
      const sub = subBits.join(" · ");
      return `<tr><td><strong>${esc(display)}</strong><div class="muted">${esc(sub)}</div></td><td>${esc(typeLabel)}</td><td class="right">${qty.toFixed(4)}</td><td class="right">${px ? eur(px, 2) : "n/d"}</td><td class="right"><button class="mini-action" data-action="delete-tx" data-tx="${esc(tx.id)}" title="Elimina" aria-label="Elimina movimento">${icon("trash")}</button></td></tr>`;
    }).join("");
    return rows ? `<div class="panel-head"><div><h3>Movimenti</h3><p>Ultime operazioni registrate.</p></div></div><table class="table"><thead><tr><th>Strumento</th><th>Tipo</th><th class="right">Qta</th><th class="right">Prezzo €</th><th class="right"></th></tr></thead><tbody>${rows}</tbody></table>` : "";
  }
  function allocationView(holds) {
    if (!holds.length) return "";
    const view = state.allocView || "symbol";
    const groups = {};
    for (const h of holds) {
      const key = view === "type" ? (h.type || "Non classificato") : view === "sector" ? (h.sector || "Non classificato") : (h.name || h.ticker || h.symbol);
      groups[key] = groups[key] || { label: key, value: 0 };
      groups[key].value += h.value;
    }
    const list = Object.values(groups).sort((a,b) => b.value - a.value);
    const total = list.reduce((a,h) => a + h.value, 0) || 1;
    const segs = list.map((h,i) => `<span class="alloc-seg" style="width:${Math.max(1, h.value / total * 100)}%;background:${COLORS[i % COLORS.length]}"></span>`).join("");
    const tabs = [["symbol","Strumenti"],["type","Tipo"],["sector","Settore"]].map(([id,label]) => `<button class="${view === id ? "active" : ""}" data-action="alloc-view" data-alloc="${id}">${label}</button>`).join("");
    const rows = list.map((h,i) => `<div class="legend-row"><span><i class="dot" style="background:${COLORS[i % COLORS.length]}"></i>${esc(h.label)}</span><strong>${pctWeight(h.value / total * 100)}</strong></div>`).join("");
    return `<section class="detail-section"><div class="panel-head"><div><h3>Allocazione</h3><p>Leggibile per strumento, tipo o settore.</p></div><div class="segmented">${tabs}</div></div><div class="alloc-bar">${segs}</div><div>${rows}</div></section>`;
  }
  function targetWeightsView(st) {
    const target = getTargetFor(state.openPf?.name);
    if (!target || !st.holdings.length) return "";
    const band = target.bandTolerancePct || 2;
    const total = st.holdings.reduce((sum, h) => sum + h.value, 0) || 1;
    const byKey = {};
    for (const h of st.holdings) {
      [h.symbol, h.ticker].filter(Boolean).forEach(k => { byKey[String(k).toUpperCase()] = (byKey[String(k).toUpperCase()] || 0) + h.value; });
    }
    const rows = target.items.map(it => {
      const keys = it.matchAny.map(x => String(x).toUpperCase());
      const actualVal = keys.reduce((sum, k) => sum + (byKey[k] || 0), 0);
      const actual = actualVal ? actualVal / total * 100 : 0;
      const delta = actual - it.weight;
      const cls = !actualVal ? "warn" : delta < -band ? "warn" : delta > band ? "bad" : "good";
      const label = !actualVal ? "manca" : delta < -band ? "sotto banda" : delta > band ? "sopra banda" : "in target";
      return `<tr><td><strong>${esc(it.code)}</strong><div class="muted">${esc(it.name)}</div></td><td class="right">${it.weight.toFixed(1)}%</td><td class="right">${actualVal ? actual.toFixed(1) + "%" : "n/d"}</td><td class="right"><span class="badge ${cls}">${esc(label)}</span></td></tr>`;
    }).join("");
    return `<section class="detail-section full-detail"><div class="panel-head"><div><h3>Pesi di riferimento</h3><p>${esc(target.description)} Banda neutra ±${band} punti.</p></div></div><table class="table"><thead><tr><th>Strumento</th><th class="right">Target</th><th class="right">Attuale</th><th class="right">Stato</th></tr></thead><tbody>${rows}</tbody></table></section>`;
  }
  async function openHoldingDetail(symbol) {
    if (!state.openPf) return;
    const sym = tickerKey(symbol);
    state.detailHolding = sym;
    $("#info-eyebrow").textContent = "Dettaglio posizione";
    $("#info-title").textContent = sym;
    $("#info-body").innerHTML = `<div class="notice">Apro la scheda posizione. Se manca lo storico, lo aggiorno in background.</div>`;
    if (!$("#info-dialog").open) $("#info-dialog").showModal();
    renderHoldingDetailBody(sym);
    ensureTickerData(sym).then(() => {
      if (state.detailHolding === sym && $("#info-dialog").open) renderHoldingDetailBody(sym);
    }).catch(() => {});
  }
  function renderHoldingDetailBody(symbol) {
    if (!state.openPf) return;
    const sym = tickerKey(symbol);
    const st = portfolioStats(state.openPf);
    const h = st.holdings.find(x => x.symbol === sym);
    if (!h) {
      $("#info-body").innerHTML = `<div class="empty">Posizione non piu presente nel portafoglio.</div>`;
      return;
    }
    const txs = (state.openPf.data.transactions || []).filter(tx => tickerKey(tx.symbol) === sym);
    const manual = state.openPf.data.manualPrices?.[sym];
    const typeLine = instrumentSubline(h);
    const txRows = txs.slice().reverse().map(tx => `<tr><td>${dateIT(tx.date)}</td><td>${esc(tx.type)}</td><td class="right">${Number(tx.qty ?? tx.quantity ?? 0).toFixed(4)}</td><td class="right">${eur(Number(tx.price ?? tx.amount ?? 0), 2)}</td><td class="right"><button class="mini-action" data-action="delete-tx" data-tx="${esc(tx.id)}" title="Elimina">${icon("trash")}</button></td></tr>`).join("");
    $("#info-title").textContent = h.name || h.ticker || sym;
    $("#info-body").innerHTML = `
      <div class="detail-hero">
        <div><h3>${esc(h.name || h.ticker || sym)}</h3><p>${esc(typeLine)}</p></div>
        <div class="detail-badges"><span class="badge">${eurMaybe(h.price, 2)}</span><span class="badge ${h.pl >= 0 ? "good" : "bad"}">${pct(h.plPct)}</span>${h.dayPct != null ? `<span class="badge ${h.dayPct >= 0 ? "good" : "bad"}">oggi ${pct(h.dayPct)}</span>` : ""}</div>
      </div>
      <div class="metric-row"><div class="metric"><span>Valore</span><strong>${eur(h.value)}</strong></div><div class="metric"><span>Quantita</span><strong>${h.qty.toFixed(4)}</strong></div><div class="metric"><span>PMC</span><strong>${eur(h.avgCost, 2)}</strong></div><div class="metric"><span>P/L</span><strong class="${h.pl >= 0 ? "pos" : "neg"}">${eur(h.pl)}</strong></div></div>
      <section class="detail-section full-detail">${tickerChart(sym, {}, "holding-detail")}</section>
      <section class="detail-section">
        <div class="panel-head"><div><h3>Prezzo manuale</h3><p>Utile per fondi, bond o strumenti senza quotazione automatica.</p></div></div>
        <div class="toolbar"><button class="button ghost" data-action="set-manual-price" data-symbol="${esc(sym)}">${icon("edit")}${manual ? "Modifica" : "Imposta"}</button>${manual ? `<button class="button ghost" data-action="clear-manual-price" data-symbol="${esc(sym)}">Usa quotazione</button><span class="badge">Manuale ${eur(manual, 2)}</span>` : ""}</div>
      </section>
      <section class="detail-section">
        <div class="panel-head"><div><h3>Operazioni rapide</h3><p>Aggiungi o vendi quote senza uscire dal dettaglio.</p></div></div>
        <div class="toolbar"><button class="button primary" data-action="quick-tx" data-kind="BUY" data-symbol="${esc(sym)}">${icon("plus")}Aggiungi quote</button><button class="button ghost" data-action="quick-tx" data-kind="SELL" data-symbol="${esc(sym)}">${icon("minus")}Vendi quote</button></div>
      </section>
      <section class="detail-section full-detail"><h3>Movimenti su questo strumento</h3>${txRows ? `<table class="table"><thead><tr><th>Data</th><th>Tipo</th><th class="right">Qta</th><th class="right">Prezzo €</th><th></th></tr></thead><tbody>${txRows}</tbody></table>` : `<div class="empty">Nessun movimento trovato.</div>`}</section>`;
  }
  function parsePortfolioImport(raw) {
    const txs = [], info = {}, manual = {};
    const date = todayISO();
    let n = 0;
    for (let line of String(raw || "").split(/\r?\n/)) {
      line = line.trim();
      if (!line || line.startsWith("#")) continue;
      const f = line.split("|").map(x => x.trim());
      if (f.length < 3) return { error: "Riga non valida: " + line.slice(0, 60) };
      const sym = tickerKey(f[0]);
      const qty = Number(String(f[1]).replace(",", "."));
      const price = Number(String(f[2]).replace(",", "."));
      if (!sym || !(qty > 0) || !(price >= 0)) return { error: "Dati non validi: " + line.slice(0, 60) };
      n += 1;
      const type = f[3] || "Altro", sector = f[4] || type, name = f[5] || sym;
      txs.push({ id: "tx_imp_" + Date.now().toString(36) + "_" + n, type: "BUY", symbol: sym, name, qty, price, date });
      info[sym] = { type, sector, name };
      const mp = f[6] ? Number(String(f[6]).replace(",", ".")) : NaN;
      if (Number.isFinite(mp) && mp > 0) manual[sym] = mp;
    }
    return { txs, info, manual };
  }
  function importRowsToText(rows) {
    return (rows || []).map(r => [r.symbol, r.quantity, r.price, r.type || "Altro", r.sector || r.type || "Altro", r.name || r.symbol, r.manualPrice ?? ""].join(" | ")).join("\n");
  }
  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || "").split(",")[1] || "");
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }
  function openImportDialog() {
    if (!state.openPf) return;
    state.pendingImportRows = [];
    $("#import-file").value = "";
    $("#import-text").value = "";
    const mode = $("#import-mode");
    if (mode) mode.value = "snapshot";
    $("#import-status").textContent = "Per aggiornare tutto in blocco incolla una riga per strumento: codice | quantita | prezzo carico EUR | tipo | settore | nome | prezzo live manuale.";
    $("#import-dialog").showModal();
  }
  async function handleImportFile() {
    const file = $("#import-file").files?.[0];
    if (!file) return;
    $("#import-status").textContent = "Lettura file in corso...";
    const headers = { "Content-Type": "application/json" };
    const tok = localStorage.getItem("tracker_sync_token") || "";
    if (tok) headers["X-Tracker-Token"] = tok;
    try {
      const dataBase64 = await fileToBase64(file);
      const r = await fetch(API.importFile, { method: "POST", headers, body: JSON.stringify({ filename: file.name, dataBase64 }) });
      const j = await r.json();
      if (!r.ok || !j.ok) throw new Error(j.error || "import_failed");
      state.pendingImportRows = j.rows || [];
      $("#import-text").value = importRowsToText(state.pendingImportRows);
      $("#import-status").textContent = `${state.pendingImportRows.length} strumenti letti dal file. Controlla e poi importa.`;
    } catch (e) {
      $("#import-status").textContent = "Import file non riuscito: " + String(e.message || e);
    }
  }
  async function applyPortfolioImport() {
    if (!state.openPf) return;
    const parsed = parsePortfolioImport($("#import-text").value);
    if (parsed.error) { $("#import-status").textContent = parsed.error; return; }
    if (!parsed.txs.length) { $("#import-status").textContent = "Nessuna riga da importare."; return; }
    const mode = $("#import-mode")?.value || "snapshot";
    if (mode === "snapshot") {
      recordOpenPortfolioSnapshot();
      const current = portfolioStats(state.openPf).holdings.map(h => h.symbol);
      const imported = new Set(parsed.txs.map(tx => tickerKey(tx.symbol)));
      const stamp = Date.now().toString(36);
      const snap = parsed.txs.map((tx, i) => ({
        ...tx,
        id: `tx_snap_${stamp}_${i}`,
        type: "SNAP",
        date: todayISO(),
      }));
      current.filter(sym => !imported.has(sym)).forEach((sym, i) => {
        snap.push({ id: `tx_snap_zero_${stamp}_${i}`, type: "SNAP", symbol: sym, name: state.openPf.data.instrumentInfo?.[sym]?.name || sym, qty: 0, price: 0, date: todayISO() });
      });
      state.openPf.data.transactions.push(...snap);
    } else {
      state.openPf.data.transactions.push(...parsed.txs);
    }
    Object.assign(state.openPf.data.instrumentInfo, parsed.info);
    Object.assign(state.openPf.data.manualPrices, parsed.manual);
    await saveOpenPortfolio();
    $("#import-dialog").close();
    await refreshQuotes();
    render();
    toast(mode === "snapshot" ? `${parsed.txs.length} strumenti aggiornati in blocco.` : `${parsed.txs.length} movimenti importati.`);
  }
  function apexStrategyKeys() {
    const keys = ["legit", "dex", "degen"];
    const strategies = state.apexData?.strategies || {};
    return keys.filter(k => strategies[k]).concat(Object.keys(strategies).filter(k => !keys.includes(k)));
  }
  function apexTaxLabel(st) {
    if (!st) return "Backtest";
    if (st.tax_mode === "declared_annual") return "CAGR netto stimato dichiarativo";
    if (st.tax_mode === "gross" || st.apply_tax === false) return "CAGR lordo";
    return "CAGR netto";
  }
  function apexSafeAsset(key) {
    return key === "degen" ? "XEON" : "CASH";
  }
  function apexAssetLabel(key, code) {
    const st = apexStrategy(key);
    return st?.assets?.[code]?.label || ({ BTC: "Bitcoin", GOLD: "Oro", GOLD2: "Oro 2x", SP500: "S&P 500", CL2: "USA 2x", CASH: "Liquidita", XEON: "Cash attivo" })[code] || code || "n/d";
  }
  function apexAssetClass(code) {
    return ({ BTC: "apex-btc", GOLD: "apex-gold", GOLD2: "apex-gold2", SP500: "apex-sp", CL2: "apex-cl2", CASH: "apex-cash", XEON: "apex-cash" })[code] || "apex-cash";
  }
  function apexAssetIcon(code) {
    return ({ BTC: "B", GOLD: "Au", GOLD2: "2x", SP500: "S&P", CL2: "CL2", CASH: "€", XEON: "€" })[code] || "?";
  }
  function apexStrategy(key = "legit") {
    return state.apexData?.strategies?.[key] || null;
  }
  function apexLookbackLabel(st) {
    const w = Number(st?.lookback_weeks || st?.lookback || 0);
    return w > 0 ? `ultime ${w} settimane` : "finestra momentum del motore";
  }
  function apexDoneBadge(key, st) {
    const done = state.apexExecuted?.[key];
    const cur = st?.current;
    if (done && cur && done.date === cur.date && done.asset === cur.asset) return `<span class="badge good">fatto ${timeIT(done.done_at)}</span>`;
    return `<span class="badge warn">da confermare</span>`;
  }
  function apexMomentumBars(cur) {
    const key = cur?.strategy_key || "legit";
    const st = apexStrategy(key);
    const m = cur?.momentum || {};
    const universe = (st?.universe || ["BTC", "GOLD", "SP500"]).filter(k => k !== apexSafeAsset(key) && k !== "CASH" && k !== "XEON" && (st?.dual ? k !== "SP500" : true));
    const rows = universe.map(k => {
      const v = Number(m[k]);
      const w = Math.max(4, Math.min(100, Math.abs(v) * 3));
      return `<div class="apex-momentum-row"><span>${esc(apexAssetLabel(key, k))}</span><strong class="${v >= 0 ? "pos" : "neg"}">${pct(v, 1)}</strong><i><em style="width:${w}%" class="${v >= 0 ? "good" : "bad"}"></em></i></div>`;
    }).join("");
    return `<p class="detail-source apex-momentum-note">Queste percentuali sono il momentum usato per il segnale: rendimento degli asset nelle ${esc(apexLookbackLabel(st))}. Non sono il rendimento del tuo portafoglio.</p>${rows}`;
  }
  function apexCurrentPanel(key = "legit", primary = false) {
    const st = apexStrategy(key);
    if (!st?.current) return `<section class="panel ${primary ? "full" : ""}"><div class="empty">APEX non ancora generata. Premi run motori o attendi il prossimo export.</div></section>`;
    const cur = st.current;
    cur.strategy_key = key;
    const asset = state.apexData?.assets?.[cur.asset] || {};
    const strategyAsset = st.assets?.[cur.asset] || asset;
    const bt = st.backtest || {};
    const cls = apexAssetClass(cur.asset);
    const changed = cur.changed ? `<span class="badge warn">cambio asset</span>` : `<span class="badge good">confermato</span>`;
    return `<section class="panel ${primary ? "full apex-hero" : "apex-secondary"}">
      <div class="apex-signal ${cls}">
        <div class="apex-token">${esc(apexAssetIcon(cur.asset))}</div>
        <div class="apex-main">
          <div class="panel-head">
            <div>
              <p class="eyebrow">${esc(st.name)} · ${esc(st.label)}</p>
              <h2>${esc(apexAssetLabel(key, cur.asset))}</h2>
              <p>${esc(strategyAsset.product || "Strumento non disponibile")} ${strategyAsset.isin ? "· " + esc(strategyAsset.isin) : ""}</p>
            </div>
            <div class="detail-badges">${changed}${apexDoneBadge(key, st)}</div>
          </div>
          <div class="grid-3">
            <div class="metric compact"><span>Segnale</span><strong>${dateIT(cur.date)}</strong></div>
            <div class="metric compact"><span>Runner</span><strong>${esc(st.run_time)}</strong></div>
            <div class="metric compact"><span>Esecuzione</span><strong>${esc(st.execution)}</strong></div>
          </div>
          <div class="apex-reason">${esc(cur.reason || "Regola applicata dal motore.")}</div>
          <div class="toolbar"><button class="button primary" data-action="apex-done" data-strategy="${esc(key)}">${icon("check")}Registra esecuzione</button><button class="button" data-action="run-engines" data-mode="all">${icon("play")}Run tutto</button><button class="button ghost" data-action="refresh-all">${icon("refresh")}Ricarica dati</button></div>
        </div>
      </div>
      <div style="height:12px"></div>
      <div class="apex-dashboard">
        <section class="detail-section"><h3>Perche ora</h3>${apexMomentumBars(cur)}</section>
        <section class="detail-section"><h3>Numeri testati</h3><div class="row-list">
          <div class="kv"><span>${esc(apexTaxLabel(st))}</span><strong>${pct(Number(bt.cagr || 0), 1)}</strong></div>
          <div class="kv"><span>Max drawdown</span><strong class="neg">${pct(Number(bt.max_drawdown || 0), 1)}</strong></div>
          <div class="kv"><span>Swap/anno</span><strong>${esc(bt.switches_per_year ?? "n/d")}</strong></div>
          <div class="kv"><span>Ulcer</span><strong>${pct(Number(bt.ulcer || 0), 1)}</strong></div>
        </div></section>
      </div>
    </section>`;
  }
  function apexRadarPanel(key = "legit", compact = false) {
    const st = apexStrategy(key);
    const r = st?.radar || {};
    if (!st || !r.level) return `<div class="empty">Radar non disponibile.</div>`;
    const cls = r.level === "alert" ? "bad" : r.level === "watch" ? "warn" : "good";
    const filters = Object.entries(r.filters || {}).map(([asset, f]) => `
      <div class="filter-row ${f.passes ? "good" : "bad"}">
        <span>${esc(apexAssetLabel(key, asset))} SMA${esc(f.weeks)}</span>
        <strong>${f.passes ? "ok" : "sotto trend"} · ${pct(Number(f.distance_pct || 0), 1)}</strong>
      </div>`).join("") || `<div class="muted">Nessun filtro trend attivo su questo asset oggi.</div>`;
    const momentum = r.momentum || {};
    const ranking = (st.universe || []).filter(a => a !== apexSafeAsset(key)).map(a => ({
      asset: a,
      v: Number(momentum[a] || 0),
    })).sort((a,b) => b.v - a.v).map((x, i) => `
      <div class="rank-row"><span>${i + 1}. ${esc(apexAssetLabel(key, x.asset))}</span><strong class="${x.v >= 0 ? "pos" : "neg"}">${pct(x.v, 1)}</strong></div>`).join("");
    return `<section class="detail-section apex-radar-card ${compact ? "compact" : ""}">
      <div class="radar-title">
        <span class="badge ${cls}">${esc(apexRadarLabel(r))}</span>
        <strong>${esc(r.title || "Radar")}</strong>
      </div>
      <div class="radar-signal-line">
        <div><span>Segnale ufficiale</span><strong>${esc(apexAssetLabel(key, r.official_asset))}</strong></div>
        <div><span>Se leggessi oggi</span><strong>${esc(apexAssetLabel(key, r.radar_asset))}</strong></div>
        <div><span>Divergenza radar</span><strong class="${Number(r.edge_pp || 0) >= 0 ? "pos" : "neg"}">${esc(apexRadarEdgeLabel(r))}</strong></div>
      </div>
      ${apexRadarPressureBar(key, r)}
      <p class="detail-source">${esc(r.body || "Radar informativo, non e' un ordine operativo.")} · As of ${dateIT(r.as_of)}</p>
      ${compact ? "" : `<div class="apex-radar-grid"><div><p class="detail-source apex-momentum-note">Classifica radar sulla stessa finestra del motore: ${esc(apexLookbackLabel(st))}.</p>${ranking}</div><div>${filters}</div></div>`}
    </section>`;
  }
  function apexOverviewCard(key) {
    const st = apexStrategy(key);
    if (!st) return "";
    const cur = st.current || {};
    const bt = st.backtest || {};
    const r = st.radar || {};
    const cls = apexAssetClass(cur.asset);
    const alertCls = r.level === "alert" ? "bad" : r.level === "watch" ? "warn" : "good";
    return `<article class="apex-card ${cls}" data-action="open-apex" data-strategy="${esc(key)}">
      <div class="apex-card-top">
        <div class="apex-token small">${esc(apexAssetIcon(cur.asset))}</div>
        <span class="badge ${alertCls}">${esc(apexRadarLabel(r))}</span>
      </div>
      <p class="eyebrow">${esc(st.name)}</p>
      <h2>${esc(apexAssetLabel(key, cur.asset))}</h2>
      <p>${esc(st.label)}</p>
      <div class="apex-card-signal">
        <div><span>Asset ora</span><strong>${esc(apexAssetLabel(key, cur.asset))}</strong></div>
        <div><span>Azione</span><strong>${cur.changed ? "cambio da valutare" : "confermato"}</strong></div>
        <div><span>Radar</span><strong>${esc(apexRadarEdgeLabel(r))}</strong></div>
      </div>
      <div class="apex-card-metrics">
        <div><span>${esc(apexTaxLabel(st))}</span><strong>${pct(Number(bt.cagr || 0), 1)}</strong></div>
        <div><span>Max DD</span><strong class="neg">${pct(Number(bt.max_drawdown || 0), 1)}</strong></div>
        <div><span>Swap/anno</span><strong>${esc(bt.switches_per_year ?? "n/d")}</strong></div>
      </div>
      <div class="apex-card-foot"><span>Segnale ${dateIT(cur.date)}</span><strong>Apri dettaglio</strong></div>
    </article>`;
  }
  function apexAllocationPills(key) {
    const st = apexStrategy(key);
    const alloc = st?.backtest?.allocation || {};
    const total = Object.values(alloc).reduce((a,b) => a + Number(b || 0), 0) || 1;
    return Object.entries(alloc).sort((a,b) => Number(b[1]) - Number(a[1])).map(([asset, weeks]) => `
      <div class="alloc-pill"><span>${esc(apexAssetLabel(key, asset))}</span><strong>${esc(weeks)} sett · ${pctWeight(Number(weeks) / total * 100, 0)}</strong></div>`).join("") || `<div class="empty">Allocazione non disponibile.</div>`;
  }
  function apexAnnualTable(key) {
    const st = apexStrategy(key);
    const rows = (st?.backtest?.annual || []).slice(-10).reverse().map(y => `
      <tr><td><strong>${esc(y.year)}</strong></td><td class="right ${Number(y.return) >= 0 ? "pos" : "neg"}">${pct(Number(y.return), 1)}</td><td class="right neg">${pct(Number(y.drawdown), 1)}</td><td class="right">${eur(Number(y.ending || 0), 0)}</td></tr>`).join("");
    return rows ? `<table class="table"><thead><tr><th>Anno</th><th class="right">Rendimento</th><th class="right">DD anno</th><th class="right">Finale</th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty">Anno per anno non disponibile.</div>`;
  }
  function apexRadarHistoryTable(key) {
    const st = apexStrategy(key);
    const list = (st?.radar_history || []).slice(-14).reverse();
    const rows = list.map(r => {
      const cls = r.level === "alert" ? "bad" : r.level === "watch" ? "warn" : "good";
      const delta = Number(r.edge_pp || 0);
      return `<tr><td><strong>${dateIT(r.as_of)}</strong><div class="muted">${esc(r.body || "")}</div></td><td><span class="badge ${cls}">${esc(r.level || "ok")}</span></td><td>${esc(apexAssetLabel(key, r.official_asset))}</td><td>${esc(apexAssetLabel(key, r.radar_asset))}</td><td class="right ${delta >= 0 ? "pos" : "neg"}">${pct(delta, 1)}</td></tr>`;
    }).join("");
    return rows ? `<table class="table"><thead><tr><th>Giorno</th><th>Radar</th><th>Ufficiale</th><th>Oggi vincerebbe</th><th class="right">Vantaggio</th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty">Storico radar non ancora disponibile.</div>`;
  }
  function apexRadarLabel(r = {}) {
    if (r.level === "alert") return "alert";
    if (r.level === "watch") return "in osservazione";
    return "allineato";
  }
  function apexRadarEdgeLabel(r = {}) {
    const n = Number(r.edge_pp || 0);
    if (!Number.isFinite(n) || Math.abs(n) < 0.05) return "nessuna divergenza";
    return `${n >= 0 ? "+" : ""}${n.toFixed(1)} pt`;
  }
  function apexRadarPressure(r = {}) {
    const n = Math.abs(Number(r.edge_pp || 0));
    if (!Number.isFinite(n) || n < 0.05) return 0;
    return Math.max(6, Math.min(100, n / 8 * 100));
  }
  function apexRadarPressureBar(key, r = {}) {
    const pressure = apexRadarPressure(r);
    const official = apexAssetLabel(key, r.official_asset);
    const radar = apexAssetLabel(key, r.radar_asset);
    const label = pressure ? `${apexRadarEdgeLabel(r)} verso ${radar}` : "segnale e radar allineati";
    return `<div class="apex-pressure">
      <div class="apex-pressure-head"><span>${esc(official)}</span><strong>${esc(label)}</strong><span>${esc(radar)}</span></div>
      <div class="apex-pressure-track"><i style="width:${pressure}%"></i></div>
    </div>`;
  }
  function apexRadarTone(r = {}) {
    return r.level === "alert" ? "bad" : r.level === "watch" ? "warn" : "good";
  }
  function apexRadarMeaning(key, st, r = {}) {
    if (!r.level) return "Radar non disponibile.";
    const official = apexAssetLabel(key, r.official_asset);
    const radar = apexAssetLabel(key, r.radar_asset);
    if (r.level === "ok") return `Il radar legge ancora ${official}: nessuna divergenza utile oggi.`;
    if (r.level === "watch") return `Il radar vede ${radar}, mentre il segnale ufficiale resta ${official}: tienilo d'occhio, ma non cambia posizione da solo.`;
    return `Il radar spinge verso ${radar}, diverso dal segnale ufficiale ${official}: alert da valutare prima del prossimo run.`;
  }
  function apexRadarStatusCard(key) {
    const st = apexStrategy(key);
    const r = st?.radar || {};
    if (!st) return "";
    const cur = st.current || {};
    const tone = apexRadarTone(r);
    return `<article class="apex-radar-status ${tone}" data-action="open-apex" data-strategy="${esc(key)}">
      <div class="apex-radar-status-head">
        <span>${esc(st.name)}</span>
        <b class="badge ${tone}">${esc(apexRadarLabel(r))}</b>
      </div>
      <strong>${esc(apexAssetLabel(key, cur.asset))}</strong>
      <p>${esc(apexRadarMeaning(key, st, r))}</p>
      ${apexRadarPressureBar(key, r)}
      <div class="apex-radar-status-foot">
        <span>Radar ${dateIT(r.as_of || cur.date)}</span>
        <span>${esc(apexRadarEdgeLabel(r))}</span>
      </div>
    </article>`;
  }
  function apexUpdateExplainer() {
    const apex = state.apexData || {};
    return `<div class="apex-update-box">
      <div><span>Ultimo export</span><strong>${apex.generated_at ? timeIT(apex.generated_at) : "n/d"}</strong></div>
      <div><span>Run automatico</span><strong>martedi 15:30 Italia</strong></div>
      <div><span>Aggiorna dati</span><strong>rilegge il segnale pubblicato</strong></div>
      <div><span>Run tutto</span><strong>rigenera OCTA + APEX</strong></div>
    </div>`;
  }
  function apexHomeView() {
    const apex = state.apexData || {};
    const keys = apexStrategyKeys();
    const alerts = keys.map(k => ({ key: k, st: apexStrategy(k), r: apexStrategy(k)?.radar })).filter(x => x.r && x.r.level !== "ok");
    const alertBox = alerts.length
      ? `<div class="apex-alert-strip warn"><strong>${alerts.length} radar da guardare</strong><span>${alerts.map(x => `${esc(x.st.name)}: ${esc(apexAssetLabel(x.key, x.r.radar_asset))}`).join(" · ")}</span></div>`
      : `<div class="apex-alert-strip good"><strong>Radar allineati</strong><span>Nessun motore sta mostrando una divergenza utile dal segnale ufficiale.</span></div>`;
    return `
      <section class="panel full apex-home-hero">
        <div class="panel-head">
          <div><h2>APEX</h2><p>Tre motori separati. Guarda prima cosa devi detenere, poi il radar per capire se sta maturando un cambio.</p></div>
          <div class="toolbar"><button class="button primary" data-action="run-engines" data-mode="all">${icon("play")}Run tutto</button><button class="button ghost" data-action="refresh-all">${icon("refresh")}Aggiorna dati</button></div>
        </div>
        ${alertBox}
        <div class="apex-card-grid">${keys.map(apexOverviewCard).join("")}</div>
      </section>
      <section class="panel full apex-radar-home">
        <div class="panel-head"><div><h2>Radar alert</h2><p>Dice cosa leggerebbe il motore se lo interrogassi ora. E' informativo: il segnale ufficiale cambia solo al run previsto o al run forzato.</p></div><span class="badge info">${esc(apex.generated_at ? "export " + timeIT(apex.generated_at) : "n/d")}</span></div>
        ${apexUpdateExplainer()}
        <div class="apex-radar-status-grid">${keys.map(apexRadarStatusCard).join("")}</div>
      </section>
      <section class="panel full apex-secondary"><details><summary>Operativita e workflow</summary><div class="octa-details-body">${apexRunbookPanel()}</div></details></section>`;
  }
  function apexDetailView(key) {
    const st = apexStrategy(key);
    if (!st) return `<section class="panel full"><div class="empty">Strategia APEX non trovata.</div></section>`;
    return `
      <section class="panel full apex-detail-nav"><div class="toolbar"><button class="button ghost" data-action="back-apex-home">${icon("minus")}Torna ai 3 APEX</button><button class="button primary" data-action="run-engines" data-mode="all">${icon("play")}Run tutto</button><button class="button ghost" data-action="refresh-all">${icon("refresh")}Aggiorna dati</button><button class="button ghost" data-action="ai-apex" data-strategy="${esc(key)}">${icon("brain")}AI</button></div></section>
      ${apexCurrentPanel(key, true)}
      <section class="panel full apex-radar-home"><div class="panel-head"><div><h2>Radar ${esc(st.name)}</h2><p>Confronta il segnale ufficiale con la lettura aggiornata. Se diverge, e' un avviso da guardare, non un ordine automatico.</p></div><span class="badge ${apexRadarTone(st.radar)}">${esc(apexRadarLabel(st.radar))}</span></div>${apexUpdateExplainer()}${apexRadarPanel(key, false)}</section>
      <section class="panel full"><div class="panel-head"><div><h2>Rendimento ${esc(st.name)}</h2><p>Grafico compatto: appoggia il dito per leggere data e valore.</p></div></div>${apexChart(key)}</section>
      <section class="panel full apex-secondary"><details><summary>Metriche complete e tempo sugli asset</summary><div class="grid-2 octa-details-body"><div class="row-list">
        <div class="kv"><span>${esc(apexTaxLabel(st))}</span><strong>${pct(Number(st.backtest?.cagr || 0), 1)}</strong></div>
        <div class="kv"><span>Valore finale da 10k</span><strong>${eur(Number(st.backtest?.final || 0), 0)}</strong></div>
        <div class="kv"><span>Max drawdown</span><strong class="neg">${pct(Number(st.backtest?.max_drawdown || 0), 1)}</strong></div>
        <div class="kv"><span>Calmar</span><strong>${esc(st.backtest?.calmar ?? "n/d")}</strong></div>
        <div class="kv"><span>Ulcer</span><strong>${pct(Number(st.backtest?.ulcer || 0), 1)}</strong></div>
        <div class="kv"><span>Switch totali</span><strong>${esc(st.backtest?.switches ?? "n/d")}</strong></div>
        <div class="kv"><span>Costi/tasse stimate</span><strong>${eur(Number(st.backtest?.taxes_paid || 0), 0)}</strong></div>
      </div><div class="alloc-grid">${apexAllocationPills(key)}</div></div></details></section>
      <section class="panel full apex-secondary"><details><summary>Storico radar</summary><div class="octa-details-body">${apexRadarHistoryTable(key)}</div></details></section>
      <section class="panel full apex-secondary"><details><summary>Anno per anno</summary><div class="octa-details-body">${apexAnnualTable(key)}</div></details></section>
      <section class="panel full apex-secondary"><details><summary>Cambi segnale</summary><div class="octa-details-body">${apexHistoryTable(key)}</div></details></section>
      <section class="panel full apex-secondary"><details><summary>Storico reale registrato</summary><div class="octa-details-body">${apexExecutionHistory(key)}</div></details></section>`;
  }
  function apexChart(key = "legit") {
    const st = apexStrategy(key);
    const pts = st?.backtest?.equity || [];
    if (pts.length < 2) return `<div class="empty">Grafico APEX disponibile dopo il primo export del motore.</div>`;
    return `<div class="notice info apex-chart-note"><strong>Come leggerlo</strong><br>${esc(st.chart_explainer || "Simulazione con capitale iniziale 10.000 EUR.")} Valore finale: ${eur(Number(st.backtest?.final || 0), 0)}.</div>${lineChart(pts, `${st.name}: simulazione 10.000 EUR`, v => eur(v, 0), `apex-${key}`, { height: 190, changeLabel: `${pct(Number(st.backtest?.cagr || 0), 1)} CAGR`, axisFmt: v => compactEur(v), cleanAxes: true })}`;
  }
  function apexHistoryTable(key = "legit") {
    const st = apexStrategy(key);
    const all = st?.changes || [];
    const open = !!state.apexHistoryOpen?.[key];
    const list = (open ? all : all.slice(-6)).slice().reverse();
    const universe = (st?.universe || ["BTC", "GOLD", "SP500"]).filter(k => k !== apexSafeAsset(key) && k !== "CASH" && k !== "XEON" && (st?.dual ? k !== "SP500" : true));
    const head = universe.map(k => `<th class="right">${esc(apexAssetLabel(key, k))}</th>`).join("");
    const rows = list.map(r => `<tr><td><strong>${dateIT(r.date)}</strong><div class="muted">${esc(r.current_marker ? "stato attuale" : r.reason || "")}</div></td><td><span class="badge ${r.changed ? "warn" : "good"}">${esc(apexAssetLabel(key, r.asset))}</span></td>${universe.map(k => `<td class="right">${pct(Number(r.momentum?.[k] || 0), 1)}</td>`).join("")}</tr>`).join("");
    const toggle = all.length > 6 ? `<div class="toolbar apex-history-actions"><button class="button ghost" data-action="toggle-apex-history" data-strategy="${esc(key)}">${open ? "Mostra meno" : `Mostra tutti i ${all.length} cambi`}</button></div>` : "";
    return rows ? `${toggle}<div class="table-note">Le percentuali sono momentum ${esc(apexLookbackLabel(st))}: servono a scegliere l'asset, non sono performance del tuo conto.</div><table class="table"><thead><tr><th>Quando cambia</th><th>Asset</th>${head}</tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty">Nessun cambio segnale disponibile.</div>`;
  }
  function apexExecutionHistory(key = "legit") {
    const rows = (state.apexHistory || []).filter(r => r.strategy_key === key).slice(0, 20).map(r => {
      const moved = r.previous_asset ? `${r.previous_asset} → ${r.asset}` : r.asset;
      const cap = r.capital_eur ? eur(r.capital_eur, 0) : "n/d";
      const px = r.execution_price ? String(r.execution_price) : "n/d";
      return `<tr><td><strong>${dateIT(r.executed_date)}</strong><div class="muted">Segnale ${dateIT(r.signal_date)}</div></td><td>${esc(moved)}</td><td class="right">${cap}</td><td class="right">${esc(px)}</td><td>${esc(r.note || "")}</td></tr>`;
    }).join("");
    return rows ? `<table class="table"><thead><tr><th>Data</th><th>Cambio fatto</th><th class="right">Capitale</th><th class="right">Prezzo</th><th>Note</th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty">Premi Registra esecuzione quando operi: da qui nasce lo storico reale misurabile.</div>`;
  }
  function apexRunbookPanel() {
    return `<section class="panel">
      <div class="panel-head"><div><h2>Operativita</h2><p>Un unico workflow aggiorna OCTA e tutti i motori APEX, cosi eviti deploy separati.</p></div></div>
      <div class="row-list">
        <div class="kv"><span>Run APEX Legit + Dex + Degen</span><strong>martedi 15:30 Italia</strong></div>
        <div class="kv"><span>Finestra azione</span><strong>martedi 15:35-17:20</strong></div>
        <div class="kv"><span>APEX Legit</span><strong>BTC, Oro, S&P 500, cash</strong></div>
        <div class="kv"><span>APEX Dex</span><strong>BTC spot, PAXG, stablecoin</strong></div>
        <div class="kv"><span>APEX Degen</span><strong>BTC, Oro 2x, CL2, XEON</strong></div>
        <div class="kv"><span>Deploy</span><strong>unico workflow: APEX + OCTA</strong></div>
      </div>
    </section>`;
  }
  function viewStrategy() {
    if (state.apexFocus) return apexDetailView(state.apexFocus);
    const next = nextRefreshInfo();
    return `
      ${apexHomeView()}
      <section class="panel"><div class="panel-head"><div><h2>Workflow vNext</h2><p>Separato dalla produzione attuale.</p></div></div><div class="row-list">
        <div class="kv"><span>Runner attivo ora</span><strong>${esc(CLOUD_RUNNER.name)}</strong></div>
        <div class="kv"><span>OCTA refresh</span><strong>${esc(CLOUD_RUNNER.schedule)}</strong></div>
        <div class="kv"><span>APEX refresh</span><strong>martedi 15:30 Italia, tre motori insieme</strong></div>
        <div class="kv"><span>Prossimo refresh</span><strong>${esc(next.label)}</strong></div>
        <div class="kv"><span>Finestra controllo</span><strong>${esc(CLOUD_RUNNER.check)}</strong></div>
        <div class="kv"><span>Deploy</span><strong>${esc(CLOUD_RUNNER.deploy)}</strong></div>
        <div class="kv"><span>Run manuale</span><strong><button class="inline-link" data-action="run-engines" data-mode="all">lancia APEX + OCTA</button></strong></div>
        <div class="kv"><span>PC locale</span><strong>non necessario</strong></div>
      </div></section>
      <section class="panel full"><div class="panel-head"><div><h2>Runbook mattina</h2><p>Controllo rapido quando vuoi capire se OCTA e' pronto.</p></div></div><div class="grid-2">
        <div class="notice good"><strong>OK operativo</strong><br>La barra mostra Segnale fresco, engine_error e' no, e la data segnale coincide con la trading date attesa dopo la finestra mattutina.</div>
        <div class="notice warn"><strong>Se non e' fresco</strong><br>Premi Ricontrolla per ricaricare app, cloud e quotazioni. Se resta vecchio va controllata la run GitHub Actions, non il PC locale.</div>
      </div><div class="row-list">
        <div class="kv"><span>Finestra cloud</span><strong>08:35-08:42</strong></div>
        <div class="kv"><span>Manuale da app</span><strong>check dati attivo</strong></div>
        <div class="kv"><span>Refresh motore</span><strong>${esc(CLOUD_RUNNER.name)}</strong></div>
        <div class="kv"><span>Produzione vecchia</span><strong>non va toccata</strong></div>
        <div class="kv"><span>Deploy manuale</span><strong>solo dopo un pacchetto aggregato</strong></div>
      </div></section>`;
  }
  function viewSettings() {
    const next = nextRefreshInfo();
    const octaWrite = localStorage.getItem("octa_sync_token") ? `<span class="badge good">scrittura attiva</span>` : `<span class="badge warn">solo lettura</span>`;
    const trackerWrite = localStorage.getItem("tracker_sync_token") ? `<span class="badge good">scrittura attiva</span>` : `<span class="badge warn">solo lettura</span>`;
    return `
      <section class="panel"><div class="panel-head"><div><h2>Token sync</h2><p>Restano nel browser locale di questa vNext.</p></div></div><div class="form-grid">
        <label>OCTA_SYNC_TOKEN<input id="set-octa-token" type="password" value="${esc(localStorage.getItem("octa_sync_token") || "")}"></label>
        <label>TRACKER_SYNC_TOKEN<input id="set-tracker-token" type="password" value="${esc(localStorage.getItem("tracker_sync_token") || "")}"></label>
      </div><div style="height:12px"></div><div class="row-list">
        <div class="kv"><span>Scrittura OCTA cloud</span><strong>${octaWrite}</strong></div>
        <div class="kv"><span>Scrittura portafogli cloud</span><strong>${trackerWrite}</strong></div>
      </div><div style="height:12px"></div><div class="toolbar"><button class="button primary" id="save-settings">Salva token locali</button><button class="button ghost" data-action="repair-local">Ripara dati locali</button></div></section>
      <section class="panel"><div class="panel-head"><div><h2>Backup portafogli</h2><p>Esporta o ripristina gli archivi cifrati senza esporre i PIN.</p></div></div><div class="row-list">
        <div class="kv"><span>Portafogli nel tracker</span><strong>${esc((state.tracker.portfolios || []).length)}</strong></div>
        <div class="kv"><span>Ultimo sync</span><strong>${timeIT(state.tracker.updated)}</strong></div>
      </div><div style="height:12px"></div><div class="toolbar"><button class="button primary" data-action="export-tracker-backup">${icon("upload")}Esporta backup</button><button class="button ghost" data-action="import-tracker-backup">Importa backup</button></div></section>
      <section class="panel"><div class="panel-head"><div><h2>Cloud runner</h2><p>Motore e pubblicazione della vNext.</p></div></div><div class="row-list">
        <div class="kv"><span>Runner</span><strong>${esc(CLOUD_RUNNER.name)}</strong></div>
        <div class="kv"><span>Deploy</span><strong>${esc(CLOUD_RUNNER.deploy)}</strong></div>
        <div class="kv"><span>Prossimo refresh</span><strong>${esc(next.label)}</strong></div>
        <div class="kv"><span>Sito</span><strong><a class="text-link" href="${esc(CLOUD_RUNNER.site)}" target="_blank" rel="noopener">vNext Netlify</a></strong></div>
        <div class="kv"><span>Actions</span><strong><a class="text-link" href="${esc(CLOUD_RUNNER.repo)}" target="_blank" rel="noopener">GitHub</a></strong></div>
      </div></section>
      <section class="panel"><div class="panel-head"><div><h2>Percorsi</h2><p>App parallela indipendente.</p></div></div><div class="row-list"><div class="kv"><span>Cartella</span><strong class="code">super-investor-vnext-codex</strong></div><div class="kv"><span>Publish</span><strong class="code">dashboard</strong></div><div class="kv"><span>Functions</span><strong class="code">netlify/functions</strong></div></div></section>`;
  }

  function openTrade(id) {
    const sig = (state.octaData?.signals || []).find(s => s.id === id);
    if (!sig) return;
    state.pendingTrade = sig;
    $("#trade-title").textContent = `${sig.action} ${sig.ticker}`;
    const px = quoteUnitEur(sig.ticker) ?? toEur(sig.current_price || sig.entry_price, "USD", fxRate()) ?? 0;
    $("#trade-price").value = px ? Number(px).toFixed(2) : "";
    $("#trade-fx").value = fxRate() ? fxRate().toFixed(4) : "";
    $("#trade-comm").value = "5";
    $("#trade-date").value = todayISO();
    $("#trade-qty").value = sig.action === "BUY" && px ? (Number(sig.value_target || 6000) / px).toFixed(4) : "";
    $("#trade-dialog").showModal();
  }
  async function completeTrade() {
    const sig = state.pendingTrade;
    if (!sig) return;
    const qty = Number($("#trade-qty").value || 0);
    const priceEur = Number($("#trade-price").value || 0);
    const fx = Number($("#trade-fx").value || fxRate() || 1);
    const comm = Number($("#trade-comm").value || 0);
    const price = priceEur * fx;
    const date = $("#trade-date").value || todayISO();
    if (sig.action === "BUY") {
      const costTotal = qty * priceEur + comm;
      state.octaPortfolio[sig.ticker] = { shares: qty, entry_price: price, entry_date: date, cost_total: costTotal, fx, comm, sector: sig.sector, score: sig.score };
      state.octaHistory.unshift({ action: sig.action, ticker: sig.ticker, qty, price, price_eur: priceEur, cost_total: costTotal, fx, comm, date });
    } else {
      const pos = state.octaPortfolio[sig.ticker];
      const proceeds = qty * priceEur - comm;
      const costBasis = pos ? octaEntryCostEur(pos) * Math.min(1, qty / Math.max(Number(pos.shares || 0), 1)) : 0;
      const pnlEur = proceeds - costBasis;
      state.octaHistory.unshift({ action: sig.action, ticker: sig.ticker, qty, price, price_eur: priceEur, proceeds, cost_total: costBasis, pnl_eur: pnlEur, pnl_pct: costBasis ? pnlEur / costBasis * 100 : 0, fx, comm, date });
      if (pos && qty < Number(pos.shares || 0)) {
        const prevShares = Number(pos.shares || 0);
        pos.shares = prevShares - qty;
        pos.cost_total = octaEntryCostEur(pos) * (pos.shares / prevShares);
      } else {
        delete state.octaPortfolio[sig.ticker];
      }
    }
    state.octaExecuted[sig.id] = { action: sig.action, ticker: sig.ticker, qty, price, price_eur: priceEur, fx, comm, date, executed_at: new Date().toISOString() };
    saveJson(LS.octaExecuted, state.octaExecuted);
    await pushOctaCloud();
    $("#trade-dialog").close();
    render();
  }
  function openTxDialog() {
    $("#tx-type").value = "BUY";
    $("#tx-symbol").value = "";
    $("#tx-name-input").value = "";
    $("#tx-qty").value = "";
    $("#tx-price").value = "";
    $("#tx-date").value = todayISO();
    $("#tx-dialog").showModal();
  }
  async function askTickerAI(ticker) {
    const s = (state.octaData?.signals || []).find(x => x.ticker === ticker) || (state.octaData?.candidates || []).find(x => x.ticker === ticker) || {};
    toast("Analisi AI in corso...");
    try {
      const j = await callAI({ mode: "explain", ticker, context: s });
      showAIAnswer(`AI su ${ticker}`, j.answer || j.error || "Nessuna risposta AI.");
    } catch (e) { showAIAnswer("AI non disponibile", String(e.message || e)); }
  }
  async function askPortfolioAI() {
    if (!state.openPf) return;
    const st = portfolioStats(state.openPf);
    const body = { mode: "pf_rebalance", portfolio: { name: state.openPf.name, value: Math.round(st.value), invested: Math.round(st.invested), gain: eur(st.gain), dividends: Math.round(st.dividends || 0), holdings: st.holdings.map(h => ({ symbol: h.symbol, name: h.name, type: h.type, sector: h.sector, weight: h.weight.toFixed(1), value: Math.round(h.value), pl: pct(h.plPct) })) } };
    toast("Analisi AI in corso...");
    try {
      const j = await callAI(body);
      showAIAnswer(`AI portafoglio ${state.openPf.name}`, j.answer || j.error || "Nessuna risposta AI.");
    } catch (e) { showAIAnswer("AI non disponibile", String(e.message || e)); }
  }
  async function askOctaAI() {
    const stats = octaStats();
    const ranks = octaRankMap();
    const f = freshness();
    const engine = liveExternalProfile();
    const holdings = Object.entries(state.octaPortfolio || {}).map(([t, p]) => {
      const item = octaItem(t);
      const px = octaLiveUnitEur(t, p);
      const value = Number(p.shares || 0) * Number(px || 0);
      const cost = octaEntryCostEur(p);
      return {
        ticker: t,
        name: item.name || t,
        rank: ranks[tickerKey(t)] || null,
        value: Math.round(value),
        pnl: Math.round(value - cost),
        pnlPct: pct(cost ? (value / cost - 1) * 100 : 0),
        score: item.score ?? item.opportunity_score ?? p.score,
        status: item.entry_status || "n/d",
      };
    });
    const signals = (state.octaData?.signals || []).slice(0, 10).map(s => ({
      ticker: s.ticker,
      name: s.name || s.ticker,
      action: s.action,
      score: s.score,
      status: statusMeta(s.entry_status).label,
      done: isSignalDone(s),
    }));
    const topCandidates = (state.octaData?.candidates || []).slice(0, 12).map((c, i) => ({
      rank: i + 1,
      ticker: c.ticker,
      name: octaItem(c.ticker).name || c.ticker,
      score: c.score ?? c.opportunity_score,
      status: statusMeta(c.entry_status).label,
    }));
    const body = {
      mode: "octa_brief",
      octa: {
        signal_date: state.octaData?.signal_date,
        freshness: `${f.label}: ${f.detail}`,
        engine: `${engine.label}: ${engine.detail}`,
        stats: { value: Math.round(stats.value), cost: Math.round(stats.cost), pnl: Math.round(stats.pnl), pnlPct: pct(stats.pnlPct) },
        holdings,
        signals,
        topCandidates,
      },
    };
    toast("Analisi AI OCTA in corso...");
    try {
      const j = await callAI(body);
      showAIAnswer("AI OCTA", j.answer || j.error || "Nessuna risposta AI.");
    } catch (e) { showAIAnswer("AI non disponibile", String(e.message || e)); }
  }
  async function askApexAI(key = "legit") {
    const st = apexStrategy(key);
    if (!st) return;
    const cur = st.current || {};
    const body = {
      mode: "pf_ask",
      question: `Analizza la strategia ${st.name}: segnale attuale ${apexAssetLabel(key, cur.asset)}, radar ${apexRadarLabel(st.radar)}, metriche e rischi. Dimmi cosa devo capire prima di operare.`,
      portfolio: {
        name: st.name,
        value: Math.round(Number(st.backtest?.final || 0)),
        invested: 10000,
        gain: `${pct(Number(st.backtest?.cagr || 0), 1)} CAGR`,
        holdings: [{ symbol: cur.asset || "n/d", name: apexAssetLabel(key, cur.asset), type: "Strategia APEX", sector: st.execution || "n/d", weight: "100", value: Math.round(Number(st.backtest?.final || 0)), pl: `${pct(Number(st.backtest?.max_drawdown || 0), 1)} MaxDD` }],
      },
    };
    toast("Analisi AI APEX in corso...");
    try {
      const j = await callAI(body);
      showAIAnswer(`AI ${st.name}`, j.answer || j.error || "Nessuna risposta AI.");
    } catch (e) { showAIAnswer("AI non disponibile", String(e.message || e)); }
  }
  async function callAI(body) {
    const r = await fetch(API.ai, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || "AI non disponibile");
    return j;
  }
  function formatAIAnswer(text) {
    return esc(text || "").replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
  }
  function showAIAnswer(title, text) {
    $("#info-eyebrow").textContent = "Assistente AI";
    $("#info-title").textContent = title;
    $("#info-body").innerHTML = `<section class="detail-section ai-answer">${formatAIAnswer(text)}</section>`;
    if (!$("#info-dialog").open) $("#info-dialog").showModal();
  }

  document.addEventListener("input", e => {
    if (e.target?.id === "set-octa-token") localStorage.setItem("octa_sync_token", e.target.value);
    if (e.target?.id === "set-tracker-token") localStorage.setItem("tracker_sync_token", e.target.value);
  });
  document.addEventListener("click", e => {
    if (e.target?.id === "save-settings") toast("Token salvati nel browser locale.");
  });

  init();
})();
