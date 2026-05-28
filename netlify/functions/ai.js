// Netlify Function — bottone AI (Groq Llama 3.3 70B + Yahoo Finance RSS).
// RADAR:   POST { mode: "explain"|"ask", ticker, context, question? }
// TRACKER: POST { mode: "pf_rebalance"|"pf_market"|"pf_explain"|"pf_ask",
//                 portfolio, instrument?, question? }
// Risponde con una spiegazione/analisi in italiano semplice.

const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const GROQ_MODEL = "llama-3.3-70b-versatile";

function json(status, obj) {
  return {
    statusCode: status,
    headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
    body: JSON.stringify(obj),
  };
}

async function fetchYahooNews(ticker) {
  try {
    const url = `https://feeds.finance.yahoo.com/rss/2.0/headline?s=${encodeURIComponent(ticker)}&region=US&lang=en-US`;
    const r = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0" } });
    if (!r.ok) return [];
    const xml = await r.text();
    const titles = [...xml.matchAll(/<title>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/title>/g)]
      .map(m => m[1].trim());
    // il primo <title> è il nome del feed → scarta
    return titles.slice(1, 6);
  } catch {
    return [];
  }
}

function contextBlock(ticker, c) {
  c = c || {};
  const comp = c.components || {};
  const lines = [
    `Ticker: ${ticker}`,
    `Nome: ${c.name || "n/d"} — Settore: ${c.sector || "n/d"}`,
    `Prezzo: $${c.price ?? "n/d"} — Market cap: ${c.market_cap ?? "n/d"}`,
    `Opportunity Score: ${c.opportunity_score ?? "n/d"}/100`,
    `Confidence Score: ${c.confidence_score ?? "n/d"}/100`,
    `Entry Status: ${c.entry_status || "n/d"}`,
    `Radar: ${c.radar_score ?? "n/d"} — Entry: ${c.entry_score ?? "n/d"}`,
    `Beta vs mercato: ${c.beta_spy ?? "n/d"}`,
    `Fattori — Conviction ${comp.conviction ?? "?"}, Accumulation ${comp.accumulation ?? "?"}, ` +
      `Insider ${comp.insider ?? "?"}, Quality ${comp.quality ?? "?"}, ` +
      `Value ${comp.value ?? "?"}, Momentum ${comp.momentum ?? "?"}`,
    `Ritorni — 1M ${c.ret_1m ?? "?"}%, 3M ${c.ret_3m ?? "?"}%, 6M ${c.ret_6m ?? "?"}%`,
    `Fondi che lo tengono: ${c.n_funds_holding ?? "?"}`,
    `Nomi dei fondi (dal più autorevole): ${(c.top_funds && c.top_funds.length) ? c.top_funds.join(", ") : "n/d"}`,
    `Segnale sistema: ${c.main_signal || "n/d"}`,
    `Rischio sistema: ${c.main_risk || "n/d"}`,
  ];
  return lines.join("\n");
}

// ─── Voce comune: analista senior ───
// Si applica a TUTTE le interazioni AI (Radar + tracker portafoglio).
const PRO_VOICE = `SEI UN ANALISTA SENIOR PROFESSIONISTA. Italiano chiaro
ma con autorevolezza, prendi posizione netta — niente frasi vaghe da
compitino, niente "valuta i tuoi obiettivi" ripetuto come scaramanzia.
Conosci a fondo asset class, costruzione di portafoglio, factor investing,
duration, cash drag, leva, decorrelazione, ecc.

ATTEGGIAMENTO: ESPRIMI GIUDIZI NETTI ("questo portafoglio è troppo
conservativo per chi ha 30 anni di orizzonte", "c'è eccessiva concentrazione
sul tema X", "il monetario al 36% è cash drag importante"). Indica
DIREZIONI DI MOSSA CONCRETE ("ridurrei la quota Pictet al 15%",
"alleggerirei l'ETF leveraged", "introdurrei un'esposizione obbligazionaria
globale più diversificata", "diversificherei geograficamente fuori dagli
USA"). Va bene sbilanciarsi.

LIMITI CHIARI: niente ordini operativi con numeri specifici di compra/vendi
("vendi 500 quote di X a 50€"). Niente previsioni di prezzo specifiche
("salirà a 200€"). Niente riferimenti a notizie recenti del mercato.

USA SEMPRE I NOMI degli strumenti (non gli ISIN/sigle: i nomi sono nei dati,
citali per esteso). Riconosci immediatamente cosa è ogni strumento:
- fondi monetari (es. Pictet Short-Term Money) = liquidità a brevissimo,
  rischio minimo, NON azioni che possono crollare
- BTP / Bund / OAT / Austria = titoli di Stato, rischio basso-medio
- ETF azionari = panieri di azioni
- ETF leveraged = leva (amplifica guadagni e perdite)
- ETC su oro / Bitcoin = materie prime / crypto
- ETF obbligazionari = panieri di obbligazioni

DISCLAIMER FINALE OBBLIGATORIO (in fondo, dopo una riga "---"):
"Sono un'AI: le mie analisi e raccomandazioni possono contenere errori o
interpretazioni discutibili. Le decisioni finali e l'esecuzione di operazioni
restano sempre tue."

LUNGHEZZA: esaustiva ma senza filler. Sezioni in **grassetto** quando aiuta.`;

function explainPrompt(ticker, context, news) {
  const newsBlock = news.length ? news.map(n => `- ${n}`).join("\n") : "- nessuna news disponibile";
  return `Analizza ${ticker} come faresti in una nota di ricerca per un cliente.

DATI DEL SISTEMA su ${ticker}:
${contextBlock(ticker, context)}

NEWS RECENTI (fonte: Yahoo Finance):
${newsBlock}

Scrivi un'analisi in sezioni con titolo in grassetto:

**Che cosa fa l'azienda**
Cosa fa concretamente, business model, posizionamento competitivo.
2-3 frasi dense.

**Chi ci ha puntato**
${(context && context.n_funds_holding) ? `${context.n_funds_holding} grandi fondi` : "I grandi fondi"} la tengono.
Se nell'elenco riconosci nomi noti (Berkshire Hathaway/Buffett, Pershing
Square/Ackman, Tiger Global, Coatue, Greenlight/Einhorn, Appaloosa/Tepper,
Scion/Burry, ecc.) citane 1-2 spiegando in mezza frase chi sono. Non
inventare nomi: usa solo l'elenco fornito.

**Perché è in lista — la mia lettura**
Spiega perché il sistema l'ha selezionata usando i fattori (convinzione dei
fondi, accumulazione, qualità dei conti, valutazione, momentum). Aggiungi
il TUO giudizio netto: è una scelta forte, debole, opportunistica?

**Quadro complessivo**
Verdetto deciso: setup interessante / opportunistico / speculativo / da
maneggiare con cautela. Spiega perché.

${PRO_VOICE}`;
}

function askPrompt(ticker, context, question, news) {
  const newsBlock = news.length ? news.map(n => `- ${n}`).join("\n") : "- nessuna news";
  return `Domanda specifica su ${ticker}.

DATI DEL SISTEMA su ${ticker}:
${contextBlock(ticker, context)}

NEWS RECENTI:
${newsBlock}

DOMANDA DELL'UTENTE: "${question}"

Rispondi entrando nel merito di QUESTI dati e di QUESTO titolo. Sbilanciati
con un giudizio chiaro. Se la domanda è su una decisione (comprare /
mantenere / vendere), prendi posizione spiegando il perché, senza dare
ordini specifici con numeri precisi e senza previsioni di prezzo.

${PRO_VOICE}`;
}

// ─── Modalità TRACKER: assistente sul portafoglio ───
function pfContextBlock(p) {
  p = p || {};
  const holds = (p.holdings || []).map(h => {
    const nm = h.name || h.symbol;
    const cat = [h.type, h.sector && h.sector !== h.type ? h.sector : ""]
      .filter(Boolean).join(", ") || "n/d";
    return `  - ${nm} (sigla ${h.symbol}, ${cat}): ` +
      `peso ${h.weight}%, valore ${h.value}€, rendimento ${h.pl}`;
  }).join("\n") || "  - nessuna posizione aperta";
  return [
    `Nome portafoglio: ${p.name || "senza nome"}`,
    `Valore attuale: ${p.value ?? "n/d"}€`,
    `Capitale investito (netto): ${p.invested ?? "n/d"}€`,
    `Guadagno/perdita totale: ${p.gain ?? "n/d"}`,
    `Dividendi incassati: ${p.dividends ?? 0}€`,
    `Rendimento annuo (TIR): ${p.xirr ?? "n/d"}`,
    p.benchmark ? `Confronto: con gli stessi importi l'indice ${p.benchmark} avrebbe reso ${p.benchGain}` : "",
    `Numero di strumenti diversi: ${(p.holdings || []).length}`,
    `Posizioni:`,
    holds,
  ].filter(Boolean).join("\n");
}

function pfPrompt(mode, body) {
  const ctx = pfContextBlock(body.portfolio);
  if (mode === "pf_rebalance") {
    return `Analizzi un portafoglio reale di un investitore e ne valuti l'EQUILIBRIO.

DATI:
${ctx}

Scrivi un'analisi a fondo in sezioni con titolo in grassetto. Sbilanciati,
non scrivere il compitino:

**Composizione effettiva**
Cosa contiene davvero il portafoglio. Usa i NOMI degli strumenti. Calcola
le quote per asset class in %: azionario, obbligazionario/titoli di Stato,
monetario/liquidità, materie prime, crypto.

**Cosa funziona**
Punti di forza concreti, con i nomi degli strumenti.

**Cosa NON funziona**
Debolezze vere e rischi reali. Cash drag, concentrazione, leva eccessiva,
sovraesposizione geografica, mancanza di diversificazione — quel che vedi
davvero, con i nomi.

**Cosa farei io adesso**
Indicazioni di riequilibrio CONCRETE e DECISE: quale asset class ridurrei,
quale aumenterei, in quale direzione muoverei il mix. Va bene dire
"ridurrei la quota Pictet al 15%", "alleggerirei il leveraged",
"introdurrei un'esposizione obbligazionaria globale diversificata". Niente
ordini con numeri esatti di compra/vendi a prezzo specifico.

**Verdetto**
2-3 frasi nette: che portafoglio è (conservativo / bilanciato / aggressivo /
squilibrato), per chi è adatto, cosa rischia.

${PRO_VOICE}`;
  }
  if (mode === "pf_market") {
    return `Descrivi il PROFILO DI ESPOSIZIONE di un portafoglio reale.

DATI:
${ctx}

Analisi dettagliata in sezioni con titolo in grassetto:

**Asset class e pesi**
Pesi % e nomi degli strumenti per ciascuna asset class.

**Esposizione geografica e tematica**
Mondo / USA / Europa / mercati emergenti e temi (tech, healthcare,
infrastrutture, immobiliare, oro, factor, momentum, value, ecc.). Cita gli
strumenti.

**Profilo di rischio**
Volatilità attesa, sensibilità al mercato, duration se rilevante, leva.
Verdetto netto: conservativo, bilanciato o aggressivo, e perché.

**Cosa funziona del MIX e cosa zoppica**
Forze e debolezze dell'insieme, non dei singoli strumenti. Sbilanciati.

${PRO_VOICE}`;
  }
  if (mode === "pf_explain") {
    return `Sei un analista che spiega in modo COMPLETO uno strumento finanziario.

Strumento: "${body.instrument || ""}"
${body.instrumentName ? "Nome completo: " + body.instrumentName : ""}

Scrivi una spiegazione ESAUSTIVA (non un riassuntino):

**Che strumento è esattamente**
Nome completo, emittente, tipo specifico. Se è un ETF, indica l'indice
replicato (es. MSCI World, S&P 500, MSCI EM, settoriale specifico). Se è
un fondo, di che categoria (monetario, obbligazionario, azionario tematico).
Se è un'azione, cosa fa l'azienda. Se è oro fisico, ETC su materia prima.

**Cosa contiene / a cosa è esposto**
Cosa c'è dentro davvero: ampiezza del paniere (es. ~600 titoli), top
holdings tipiche, geografia, settori, durata media se obbligazionario.

**Come si comporta**
Volatilità tipica, rendimento atteso di lungo periodo, comportamento in
fasi di mercato diverse (cresce in espansione, soffre in recessione, decorrela
dall'azionario, ecc.), eventuali leve/specificità (leveraged, hedged,
valuta, duration).

**Ruolo in un portafoglio**
A cosa serve di solito: motore di crescita, parcheggio di liquidità,
decorrelazione, copertura inflazione, scommessa tattica. Per chi è adatto.

${PRO_VOICE}`;
  }
  // pf_ask — domanda libera
  return `Sei un analista che risponde a una domanda specifica su un portafoglio reale.

DATI DEL PORTAFOGLIO:
${ctx}

DOMANDA: "${body.question || ""}"

Rispondi in modo DIRETTO ed ESAUSTIVO. Entra nel merito di QUESTI dati e di
QUESTI strumenti specifici, citandoli PER NOME. Se la domanda chiede una
decisione, dai un giudizio chiaro su pro e contro (senza ordini "compra X /
vendi Y" e senza previsioni di prezzo) e indica concretamente cosa avrebbe
senso valutare. Niente frasi generiche da compitino, niente "consulta un
consulente": l'utente ti sta usando proprio per questo.

${PRO_VOICE}`;
}

function octaContextBlock(o) {
  o = o || {};
  const stats = o.stats || {};
  const holdings = (o.holdings || []).map(h => {
    const rank = h.rank ? `#${h.rank}` : "fuori radar";
    return `  - ${h.name || h.ticker} (${h.ticker}, ${rank}): valore ${h.value} EUR, risultato ${h.pnl} EUR (${h.pnlPct}), score ${h.score ?? "n/d"}, stato ${h.status || "n/d"}`;
  }).join("\n") || "  - nessuna posizione aperta";
  const signals = (o.signals || []).map(s => {
    return `  - ${s.action} ${s.name || s.ticker} (${s.ticker}): score ${s.score ?? "n/d"}, stato ${s.status || "n/d"}, ${s.done ? "gia registrato" : "da valutare"}`;
  }).join("\n") || "  - nessun segnale";
  const top = (o.topCandidates || []).map(c => {
    return `  - #${c.rank} ${c.name || c.ticker} (${c.ticker}): score ${c.score ?? "n/d"}, stato ${c.status || "n/d"}`;
  }).join("\n") || "  - top candidate non disponibili";
  return [
    `Data segnale: ${o.signal_date || "n/d"}`,
    `Freshness: ${o.freshness || "n/d"}`,
    `Motore: ${o.engine || "n/d"}`,
    `Valore OCTA: ${stats.value ?? "n/d"} EUR`,
    `Costo OCTA: ${stats.cost ?? "n/d"} EUR`,
    `Risultato OCTA: ${stats.pnl ?? "n/d"} EUR (${stats.pnlPct || "n/d"})`,
    `Posizioni aperte:`,
    holdings,
    `Segnali correnti:`,
    signals,
    `Classifica radar:`,
    top,
  ].join("\n");
}

function octaPrompt(body) {
  const ctx = octaContextBlock(body.octa);
  return `Analizza la strategia OCTA come assistente operativo del mattino.

DATI:
${ctx}

Rispondi in italiano semplice e pratico, in sezioni brevi:

**Stato del mattino**
Dimmi se il segnale sembra fresco, se ci sono azioni da fare e cosa controllare prima.

**Portafoglio OCTA**
Valuta le 8 posizioni: classifica attuale, risultato, eventuali posizioni fuori radar o deboli.

**Cosa guarderei adesso**
Priorita concrete: quali segnali meritano attenzione, quali rischi pesano, quali cose sono solo rumore.

**Verdetto**
3-5 punti netti, senza ordini operativi numerici e senza previsioni di prezzo.

${PRO_VOICE}`;
}

async function callGroq(key, prompt, maxTokens, extra) {
  try {
    const r = await fetch(GROQ_URL, {
      method: "POST",
      headers: { "Authorization": `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model: GROQ_MODEL,
        messages: [{ role: "user", content: prompt }],
        temperature: 0.3,
        max_tokens: maxTokens,
      }),
    });
    const data = await r.json();
    if (!r.ok) return json(502, { error: "Servizio AI non disponibile, riprova" });
    return json(200, Object.assign({
      answer: data.choices?.[0]?.message?.content || "Nessuna risposta generata.",
    }, extra || {}));
  } catch (e) {
    return json(502, { error: "Servizio AI non raggiungibile" });
  }
}

exports.handler = async (event) => {
  if (event.httpMethod === "OPTIONS") return json(200, {});
  if (event.httpMethod !== "POST") return json(405, { error: "Solo POST" });

  let body;
  try { body = JSON.parse(event.body || "{}"); }
  catch { return json(400, { error: "JSON non valido" }); }

  const key = process.env.GROQ_API_KEY;
  if (!key) return json(500, { error: "GROQ_API_KEY non configurata" });

  const mode = body.mode;
  if (mode === "octa_brief") {
    return await callGroq(key, octaPrompt(body), 1400, {});
  }

  // ─── Modalità TRACKER (assistente portafoglio) ───
  if (typeof mode === "string" && mode.startsWith("pf_")) {
    if (mode === "pf_explain" && !body.instrument)
      return json(400, { error: "strumento mancante" });
    if (mode === "pf_ask" && !body.question)
      return json(400, { error: "domanda mancante" });
    return await callGroq(key, pfPrompt(mode, body), 1600, {});
  }

  // ─── Modalità RADAR (spiega/chiedi su un ticker) ───
  const { ticker, context, question } = body;
  if (!ticker) return json(400, { error: "ticker mancante" });

  const news = await fetchYahooNews(ticker);
  const prompt = (mode === "ask" && question)
    ? askPrompt(ticker, context, question, news)
    : explainPrompt(ticker, context, news);
  return await callGroq(key, prompt, mode === "ask" ? 1100 : 1600,
    { ticker, news_count: news.length });
};
