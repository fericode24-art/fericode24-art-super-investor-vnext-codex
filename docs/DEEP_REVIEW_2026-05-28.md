# Revisione profonda vNext - 2026-05-28

Cartella revisionata: `C:\Users\fedez\OneDrive\Desktop\super-investor-vnext-codex`.

Cartella vecchia/current production: non toccata.

Deploy: non eseguito. Questa revisione lascia solo modifiche locali per il prossimo deploy.

## Fix locale pronto per il prossimo deploy

- `dashboard/app.js`: nella composizione/allocazione dei portafogli i pesi ora usano `pctWeight()` e non mostrano piu il `+` davanti alla percentuale.
- Il `+` resta invece dove serve davvero: rendimento, P/L, variazioni giornaliere.

## Debug eseguito

- `npm.cmd run check`: OK.
- `node --check dashboard/app.js`: OK tramite script `check`.
- `node --check dev-server.mjs`: OK tramite script `check`.
- `node --check netlify/functions/ai.js`: OK.
- `node --check netlify/functions/portfolios.mjs`: OK.
- `node --check netlify/functions/octa-portfolio.mjs`: OK.
- `node --check netlify/functions/quotes.mjs`: OK.
- `http://localhost:5177/app.js`: risponde 200 e serve il fix `pctWeight`.
- `http://localhost:5177/freshness.json`: risponde 200, fresh true.
- Endpoint pubblico Netlify:
  - `freshness.json`: 200, `signal_date=2026-05-28`, `fresh=true`, `engine_error=false`, `signals=0`.
  - `octa-portfolio`: 200, 8 posizioni cloud, updated `2026-05-26T16:40:07.966Z`.
  - `portfolios`: 200, 2 portafogli cifrati, updated `2026-05-27T20:40:55.886Z`.
- GitHub Actions:
  - `gh run list` non utilizzabile da questa shell perche `gh` non e autenticato.
  - API pubblica GitHub ritorna 404, probabilmente repo privato o accesso Actions non pubblico.
  - Ho quindi potuto revisionare il workflow da codice locale, ma non confermare la lista live delle run da GitHub.
- Pytest:
  - I test Python mirati completano le asserzioni (`..... [100%]`) ma il processo non termina e va in timeout.
  - Questo e un problema del test runner locale/ambiente, non una prova di fallimento logico dei test. Va comunque sistemato per CI affidabile.

## Stato OCTA live

Dati locali e pubblici coerenti:

- `dashboard/freshness.json`: fresco per il 28/05/2026.
- `dashboard/data-octa.json`: versione `2.6.0-cached`.
- Candidati totali: 455.
- Segnali attuali: 0.
- Top 40:
  - 22 ticker in profilo `cached`.
  - 18 ticker in profilo `quick`.
  - analyst cached: 0/40.
  - insider cached: 8/40.
  - congressional shadow presente: 22/40.
  - short interest/squeeze live: 0/40.
  - external delta medio: circa -6.42 punti.
  - external delta positivo: 0/40.

Ranking delle posizioni OCTA attuali nel Radar 40:

- MKSI: #1.
- MRVL: #2.
- AMD: #4.
- MU: #5.
- GLW: #6.
- RKLB: #8.
- MTZ: #20.
- HUM: #24.
- INTC: #3, ma non detenuta.
- LRCX: #7, ma non detenuta.

Lettura: lo `0 segnali` non e automaticamente un errore. MTZ e HUM sono ancora dentro il bacino qualita da 40, quindi l'anti-churn puo tenerle. Inoltre il portafoglio attuale sembra gia pieno di Technology e il sector cap puo bloccare nuovi Technology come INTC/LRCX. Il problema vero e che questa spiegazione oggi non viene esposta bene in app.

## Findings principali

### 1. OCTA deve mostrare il target portfolio e il motivo dei no-trade

Il motore calcola `selected_portfolio` nell'audit interno di `qfas/qfas_runner.py`, ma `qfas/qfas_export_octa.py` non lo esporta in `dashboard/data-octa.json`.

Effetto: l'app mostra candidati, posizioni e segnali, ma non mostra chiaramente perche oggi non compra/vende. Questo e il punto piu importante per fidarsi del segnale fresco mattutino.

Proposta:

- esportare `target_portfolio` in `data-octa.json`;
- includere per ogni slot: ticker, score, settore, stato, motivo (`incumbent`, `challenger_fill`, `sub_approved`, sector cap, min hold);
- in app mostrare una sezione semplice: "Tengo / Cambio / Bloccato da vincolo".

### 2. La formula anti-churn va verificata con test dedicato

In `qfas/tax_aware_optimizer.py`, `evaluate_substitution()` approva un challenger se non e troppo piu debole dell'incumbent:

```text
challenger_score >= incumbent_score - margin
```

Per una rotazione normale mi aspetterei invece una logica piu prudente:

```text
challenger_score >= incumbent_score + margin
```

Forse e intenzionale per TLH/tasse, ma il testo UI dice "sostituito da candidato con score migliore". Se il codice puo sostituire con un candidato leggermente peggiore, c'e incoerenza strategica.

Proposta:

- aggiungere test unitari su casi: challenger migliore, peggiore, settore bloccato, min hold, TLH;
- decidere esplicitamente se la sostituzione deve richiedere miglioramento netto o solo mantenere qualita simile;
- allineare UI e reason del segnale alla regola reale.

### 3. External signals sono attivi, ma la copertura reale e debole

Il profilo live e `cached`, non piu "solo momentum". Pero nei top 40:

- analyst risulta mancante su tutti;
- insider copre solo 8/40;
- congressional/squeeze sono shadow e non modificano il ranking finale;
- external delta e sempre negativo nei cached osservati.

Effetto: l'app puo far pensare che analyst/insider lavorino in modo pieno, ma nella realta il peso e attivo con molti fallback neutrali/mancanti.

Proposta:

- mostrare in app una copertura dati per ticker: "insider presente", "analyst non disponibile", "shadow only";
- non chiamare genericamente "profilo completo" se una riga e in `quick` o se manca copertura;
- creare un confronto giornaliero `score_base` vs `score_cached` per capire se i segnali esterni migliorano davvero.

### 4. Documento OCTA audit vecchio non e piu affidabile

`docs/OCTA_SIGNAL_AUDIT.md` dice ancora che il live usa `skip_external_signals=True` e che insider/earnings non entrano nel punteggio.

Oggi il codice usa `external_mode=cached`, quindi quella nota e superata. Va aggiornata o marcata come storica per non confondere decisioni future.

### 5. Workflow mattutino: codice buono, garanzia non assoluta

Il workflow `.github/workflows/octa-vnext-refresh.yml` ha:

- piu cron ravvicinati;
- gate Europe/Rome per ora legale/solare;
- freshness guard;
- generazione `data-octa.json`;
- scrittura `freshness.json`;
- deploy Netlify se i secret sono presenti;
- notifica `ntfy` opzionale.

Questo e molto meglio del PC acceso. Resta pero un limite: GitHub scheduled workflows possono ritardare o saltare. Le triple schedule riducono il rischio, ma non lo azzerano.

Proposta gratis:

- aggiungere un workflow watchdog alle 08:55/09:05 Europe/Rome;
- se `freshness.json` non e fresco, rilanciare lo stesso refresh con `force_run=true`;
- esporre in app "ultimo run GitHub verificato" quando avremo un accesso GitHub leggibile.

### 6. Portafogli: calcolo vendite parziali da correggere

In `dashboard/app.js`, `holdingsFromTransactions()` per una SELL riduce l'investito usando il controvalore venduto:

```js
invested -= Math.min(invested, qty * price)
```

Contabilmente e fragile: in una vendita parziale dovrebbe scaricare il costo medio della quantita venduta, non il prezzo di vendita. Altrimenti P/L residuo e rendimento possono distorcersi dopo vendite in gain/loss.

Proposta:

- su SELL ridurre `invested` di `avgCost * qtySold`;
- salvare P/L realizzato separato;
- far vedere "risultato aperto", "realizzato", "totale".

### 7. Portafogli: dividendi e liquidita vanno resi espliciti

I dividendi entrano in `cash`, ma il risultato principale non li racconta in modo separato. Inoltre l'allocazione usa solo holdings: se c'e cash, le percentuali strumenti possono sembrare 100% della parte investita, non del patrimonio totale.

Proposta:

- aggiungere riga "Liquidita" nell'allocazione quando `cash != 0`;
- mostrare "Dividendi incassati";
- decidere se il rendimento totale deve includere dividendi e realizzato.

### 8. AI visibile, ma serve stato operativo

L'AI e presente in UI su OCTA e portafogli e `netlify/functions/ai.js` passa il syntax check.

Manca pero un indicatore semplice: se manca `GROQ_API_KEY` o la chiamata fallisce, l'utente deve vedere "AI non configurata" o "AI temporaneamente non disponibile", non solo un comportamento opaco.

### 9. Privacy e sicurezza

- Portafogli personali: GET pubblico ma dati cifrati client-side. Accettabile se PIN/password sono forti.
- OCTA portfolio: GET pubblico e non cifrato. Chi conosce l'URL puo leggere ticker/posizioni OCTA.
- POST protetti da token e anti-wipe/optimistic lock: buona base.

Proposta:

- valutare read token anche per OCTA GET, oppure accettare consapevolmente che OCTA sia leggibile da URL pubblico.

### 10. UX/design

Miglioramenti gia presenti in v25:

- badge ridondanti rimossi da molte pagine;
- grafico OCTA mobile piu compatto;
- tap/hover con data e valore;
- rank accanto alle posizioni OCTA;
- AI visibile su OCTA e portafogli.

Da rifinire:

- sezione "perche non cambio" OCTA;
- copertura segnali esterni per ogni ticker;
- legenda piu semplice per cached/quick/shadow;
- liquidita/dividendi/realizzato nei portafogli;
- messaggi piu user-friendly al posto di termini tipo `external_delta`, `cached`, `shadow`.

## Priorita consigliata

1. Deploy del fix `+` sui pesi, insieme al prossimo pacchetto.
2. Esportare e mostrare `target_portfolio` OCTA con motivi di hold/no-trade.
3. Testare e correggere se necessario la formula anti-churn.
4. Mostrare copertura reale analyst/insider/congressional/squeeze.
5. Correggere accounting portafogli: SELL parziali, cash, dividendi, realizzato.
6. Aggiungere watchdog gratuito del refresh mattutino.
7. Sistemare pytest che termina le asserzioni ma non chiude il processo.
8. Decidere policy privacy su OCTA GET pubblico.

## Conclusione

La vNext funziona e il dato del 28/05/2026 e fresco. La criticita piu grande non e "non gira", ma "non spiega abbastanza bene perche non genera segnali quando decide di tenere". Per renderla davvero affidabile al 100% lato utente, il prossimo blocco deve concentrarsi su audit visibile del motore OCTA e contabilita portafogli.
