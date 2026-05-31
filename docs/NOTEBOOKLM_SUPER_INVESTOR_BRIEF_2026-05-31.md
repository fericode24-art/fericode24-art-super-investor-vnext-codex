# Super Investor vNext - Brief per NotebookLM

Data documento: 2026-05-31
App pubblica: https://super-investor-vnext-codex.netlify.app
Repo ufficiale: fericode24-art/fericode24-art-super-investor-vnext-codex

Questo documento e' pensato come fonte principale per NotebookLM.
Obiettivo: generare una presentazione audio e una presentazione video dell'app Super Investor vNext, spiegando in modo chiaro cosa fa, come funzionano OCTA e APEX, quali dati usa, quali risultati storici sono stati osservati nei backtest, e quali limiti/rischi restano.

Nota importante: l'app e le strategie sono strumenti informativi e di supporto decisionale. Non eseguono ordini e non sono consulenza finanziaria. La decisione finale di operare resta sempre dell'utente.

---

## 1. Executive summary

Super Investor vNext e' una dashboard personale per seguire tre aree:

1. Oggi
   - Vista sintetica della giornata.
   - Controlla se i dati sono freschi.
   - Mostra se ci sono segnali OCTA o APEX da valutare.
   - Mostra un piccolo radar di mercato con VIX, S&P 500, Bitcoin e Oro.

2. OCTA
   - Strategia azionaria basata su ranking, grandi fondi, momentum, filtri tecnici e segnali extra.
   - Produce segnali di acquisto/vendita.
   - Tiene traccia del portafoglio OCTA reale registrato dall'utente.
   - Mostra Radar 40, top candidati, motivi operativi e dettagli titolo.

3. APEX
   - Sezione con tre strategie separate:
     - APEX Legit
     - APEX Dex
     - APEX Degen
   - Ogni strategia ruota il capitale su un singolo asset alla volta.
   - Il segnale viene calcolato automaticamente e puo' essere forzato manualmente.
   - La vista principale mostra tre badge: asset da detenere, radar, alert e stato operativo.

4. Portafogli
   - Area per portafogli personali.
   - Supporta portafogli cifrati con PIN, import, aggiornamento composizione, prezzi manuali, movimenti, backup, sync cloud e AI.

La filosofia dell'app e': poche informazioni essenziali nella pagina Oggi, dettagli solo quando servono, e strumenti operativi per registrare cio' che e' stato realmente fatto.

---

## 2. Cosa deve comunicare la presentazione audio

La presentazione audio dovrebbe sembrare un briefing chiaro, non una lettura tecnica.

Tono consigliato:
- semplice;
- concreto;
- leggermente prudente;
- orientato all'uso reale;
- evitare eccesso di termini tecnici;
- spiegare quando un numero e' backtest e quando e' dato operativo.

Struttura consigliata per l'audio:

1. Apertura
   - "Super Investor vNext e' una dashboard personale per controllare segnali, strategie e portafogli in un solo posto."
   - "Non compra e non vende da sola. Aiuta a capire cosa fare e quando."

2. Problema che risolve
   - Evitare di aprire mille fonti diverse.
   - Sapere se il segnale del giorno e' arrivato davvero.
   - Capire se ci sono azioni da fare.
   - Tenere storico e portafoglio reale nello stesso ambiente.

3. Pagina Oggi
   - Controllo rapido di OCTA, APEX e mercato.
   - Stato run/freschezza dati.
   - Notifiche di segnali nuovi.
   - VIX e asset chiave come contesto.

4. OCTA
   - Strategia azionaria.
   - Ranking dei titoli.
   - Segnali comprensibili: breakout, ritracciamento, laterale, trend rotto, sostituito.
   - Radar 40 come lista dei migliori candidati.
   - Possibilita' di registrare cosa e' stato eseguito realmente.

5. APEX
   - Tre strategie BTC-centriche o crypto/asset rotation.
   - Ogni strategia ha un asset da detenere ora.
   - Il momentum grande indica la forza sulle ultime 6 settimane.
   - Il radar mostra cosa leggerebbe il motore se interrogato oggi.
   - Il radar e' informativo, non cambia automaticamente la posizione.

6. Portafogli
   - Home banking personale.
   - Portafogli cifrati, import, prezzi, movimenti, AI.
   - Obiettivo: capire valore, investito, risultato, posizioni e modifiche da fare.

7. Automazione
   - OCTA gira tutte le mattine feriali con finestre e retry.
   - APEX gira il martedi pomeriggio.
   - C'e' anche un bottone "Run tutto" per forzare OCTA + APEX.
   - Scelta progettuale: meglio una run doppia che saltare un segnale.

8. Chiusura
   - "L'app e' un cockpit operativo: prima mostra se c'e' qualcosa da fare, poi permette di entrare nei dettagli."
   - "La parte piu importante non e' vedere tanti numeri, ma sapere quali numeri contano oggi."

---

## 3. Cosa deve comunicare la presentazione video

NotebookLM Video Overview puo' generare una presentazione visuale stile spiegazione/slideshow. Non va intesa come screen recording perfetto dell'app. Per un video demo veramente fedele servirebbero screenshot o registrazioni dello schermo.

Storyboard consigliato:

1. Slide 1 - Titolo
   - "Super Investor vNext"
   - Sottotitolo: "Segnali, strategie e portafogli in un'unica dashboard operativa."

2. Slide 2 - Mappa dell'app
   - Oggi
   - OCTA
   - APEX
   - Portafogli
   - Setup / Automazioni

3. Slide 3 - Pagina Oggi
   - Evidenziare che e' una pagina di controllo rapido.
   - Mostrare tre macro-blocchi:
     - OCTA: serve intervenire?
     - APEX: cosa detenere?
     - Mercato: VIX e contesto.

4. Slide 4 - OCTA in 30 secondi
   - Strategia azionaria.
   - Radar 40.
   - Segnali con motivi leggibili.
   - Registrazione operazioni reali.

5. Slide 5 - Come leggere un segnale OCTA
   - "Compra: breakout" = prezzo rompe verso l'alto.
   - "Compra: ritracciamento" = trend sano con prezzo che ha respirato.
   - "Aspetta: laterale" = manca conferma.
   - "Vendi: trend rotto" = uscita o prudenza.
   - "Vendi: sostituito" = rotazione verso candidati migliori.

6. Slide 6 - APEX: tre motori
   - APEX Legit: versione principale Fineco.
   - APEX Dex: BTC spot / PAXG / stablecoin.
   - APEX Degen: versione aggressiva con BTC, Oro 2x, USA 2x, XEON.

7. Slide 7 - Come leggere APEX
   - Asset attuale.
   - Momentum ultime 6 settimane.
   - Movimento dal cambio asset quando disponibile.
   - Radar giornaliero informativo.
   - Storico segnali e backtest.

8. Slide 8 - Automazioni
   - OCTA: mattina feriale, finestre e retry.
   - APEX: martedi 15:30 Italia.
   - Run manuale: aggiorna tutto.
   - Principio: meglio ridondanza che mancato segnale.

9. Slide 9 - Portafogli
   - Portafogli cifrati.
   - Import / aggiornamento composizione.
   - Prezzi manuali.
   - Movimenti.
   - AI sul portafoglio.

10. Slide 10 - Messaggio finale
   - "La dashboard non sostituisce il giudizio, lo organizza."
   - "Prima dice se c'e' qualcosa da fare. Poi mostra perche'."

---

## 4. OCTA - logica semplice

OCTA e' la strategia azionaria della dashboard.

L'idea e':
- osservare un universo di titoli;
- dare priorita' ai titoli con score migliore;
- usare i dati dei fondi osservati;
- usare momentum e filtri tecnici;
- evitare ingressi quando il prezzo e' troppo tirato, laterale o con trend rotto;
- mantenere una lista operativa di segnali.

### Componenti principali

1. Fondi
   - Indica quanto un titolo e' presente nei fondi osservati.
   - Non basta che un titolo sia famoso: conta se entra nei portafogli qualificati.

2. Ingresso
   - Dice se il prezzo e' in un punto sensato.
   - Un buon titolo puo' essere scartato se il prezzo e' troppo esteso o se il trend si rompe.

3. Priorita
   - E' il punteggio finale che ordina i candidati.
   - Aiuta a capire quali titoli meritano attenzione oggi.

4. Forza
   - Indica quanto il titolo sta correndo rispetto agli altri.

5. Segnali extra
   - Analyst, insider, PEAD, congressional, squeeze e altri segnali possono essere visibili.
   - Alcuni possono essere pesati nel motore, altri solo mostrati in prova/shadow.

### Linguaggio operativo dei segnali

- Compra: breakout
  Il prezzo sta rompendo verso l'alto.

- Compra: ritracciamento
  Il trend e' ancora buono, ma il prezzo ha respirato. Potrebbe essere un ingresso piu ordinato.

- Compra: ok
  Non ci sono divieti tecnici. Il titolo si compra solo se il portafoglio e lo score lo richiedono.

- Aspetta: laterale
  Il titolo e' in una fase senza direzione chiara.

- Aspetta: tirato
  Il prezzo ha gia corso molto. Il rischio e' comprare troppo tardi.

- Vendi: trend rotto
  Il trend tecnico si e' rotto. Serve uscire o ridurre rischio.

- Evita: rischio alto
  Il motore vede troppi rischi o un veto tecnico.

- Vendi: sostituito
  Il titolo esce perche ci sono candidati migliori nella rotazione.

### Radar 40

Radar 40 e' la classifica dei migliori candidati OCTA.
Non e' la cosa piu importante nella pagina Oggi; e' una sezione da aprire quando si vuole analizzare piu a fondo.

Nella vista Radar 40:
- Top 8 mostra subito i principali candidati.
- La tabella completa mostra priorita, motivo, extra score e forza.
- Extra score significa punti aggiunti o tolti da segnali extra.
- Forza significa momentum relativo.

---

## 5. APEX - visione generale

APEX e' la sezione delle strategie di rotazione.

L'idea e':
- non avere tante posizioni contemporaneamente;
- detenere un solo asset alla volta per ogni strategia;
- scegliere l'asset con logica momentum/filtro;
- aggiornare il segnale in automatico;
- mostrare un radar giornaliero informativo.

La sezione APEX contiene tre strategie di pari dignita':

1. APEX Legit
2. APEX Dex
3. APEX Degen

La prima schermata APEX deve far capire subito:
- nome strategia;
- asset da detenere;
- stato radar;
- se c'e' una notifica o un alert;
- ultimo run;
- possibilita' di entrare nel dettaglio.

---

## 6. APEX Legit

APEX Legit e' la versione principale pensata per operativita' tipo Fineco.

Caratteristiche:
- Universo: Bitcoin, Oro, S&P 500, Cash.
- Logica: momentum rotation con buffer.
- Lookback: 6 settimane.
- Buffer: 3 punti percentuali.
- Filtro anti-crash: BTC sopra/sotto media a 30 settimane.
- Timing: martedi 15:30 Italia.
- Esecuzione teorica: martedi 15:35-17:20 su Fineco/Xetra.

Interpretazione:
- La percentuale grande mostrata nell'app e' il momentum usato dal motore.
- Quella percentuale si riferisce alle ultime 6 settimane.
- Non e' il rendimento del portafoglio dell'utente.
- Se disponibile, la piccola percentuale sotto indica il movimento dal cambio asset precedente.

Risultati storici validati:
- Circa 42% CAGR netto nei test principali.
- Max drawdown intorno a -40%.
- Variante con ripiego SMA corretto migliora la logica rispetto alla versione monca.
- APEX R classica era piu semplice ma meno performante.

Messaggio da comunicare:
APEX Legit e' la strategia principale: aggressiva ma ancora comprensibile, con regole abbastanza semplici e un filtro anti-crash su BTC.

---

## 7. APEX Dex

APEX Dex e' una strategia separata, pensata per ambiente DEX.

Universo:
- BTC spot
- PAXG o equivalente oro tokenizzato
- Stablecoin

Caratteristiche:
- Non e' identica ad APEX Legit.
- Non usa S&P 500.
- Non e' modellata nello stesso modo fiscale di Fineco.
- Va considerata come blocco separato.

Uso nell'app:
- Deve avere grafico dedicato.
- Deve avere storico dedicato.
- Deve avere radar dedicato.
- Il run puo' essere eseguito insieme ad APEX Legit per risparmiare deploy.

Messaggio da comunicare:
APEX Dex e' interessante, ma non va confusa con la versione Fineco. E' una strategia per strumenti e contesto operativo diversi.

---

## 8. APEX Degen

APEX Degen e' la strategia piu aggressiva.

Universo:
- Bitcoin
- Oro 2x
- USA 2x / CL2
- XEON come cash attivo

Caratteristiche:
- Versione leveraged.
- Piu rendimento potenziale.
- Piu rischio.
- Pensata come terza gamba separata, non come sostituto di APEX Legit.

Versione scelta:
- Pure-relative 6w.
- Buffer 5 punti.
- Filtro BTC SMA30.
- Nessun filtro CL2-SMA10, perche nei test non ha migliorato abbastanza.

Risultati storici validati:
- Netto dichiarativo reale intorno a 58%.
- Max drawdown intorno a -35%.
- Lookback 6 molto forte ma da trattare con prudenza, perche puo' essere una zona precisa del passato.

Messaggio da comunicare:
APEX Degen e' potente ma va trattata come strategia aggressiva. Non sostituisce Legit; affianca Legit come gamba piu rischiosa.

---

## 9. Radar APEX

Il radar APEX non e' il segnale ufficiale.

Serve a rispondere alla domanda:
"Se interrogassi il motore oggi, starebbe gia' spingendo verso un cambio?"

Stati:
- Radar ok: il radar e' coerente col segnale ufficiale.
- Watch: c'e' una divergenza da osservare.
- Alert: divergenza piu forte, da valutare prima del prossimo run.

Il radar non cambia automaticamente l'asset.
Il segnale ufficiale cambia al run previsto o al run manuale.

---

## 10. Automazioni

Automazioni principali:

1. OCTA
   - Finestra mattutina feriale.
   - Orari indicativi: 08:35, 08:45, 08:55, 09:10, 09:30 Italia.
   - Obiettivo: avere segnale fresco la mattina.
   - Ci sono retry per aumentare affidabilita'.

2. APEX
   - Martedi 15:30 Italia.
   - Run unico per Legit, Dex e Degen.
   - Disegnato per non saltare solo perche OCTA era gia fresco al mattino.

3. Run manuale
   - Bottone "Run tutto".
   - Lancia OCTA + APEX insieme.
   - Utile se si vuole forzare aggiornamento o verificare la pipeline.

Principio operativo:
Meglio una run doppia che una run mancata.

---

## 11. Portafogli

La sezione Portafogli deve comportarsi come un piccolo home banking personale.

Funzioni:
- creare/aprire portafoglio cifrato con PIN;
- importare dati;
- aggiornare una composizione in blocco;
- registrare acquisti/vendite;
- impostare prezzi manuali;
- esportare/importare backup;
- sync cloud;
- AI sul portafoglio.

Informazioni principali:
- valore totale;
- investito;
- rendimento;
- liquidita';
- posizioni;
- allocazione;
- movimenti.

Principio UX:
La prima schermata deve essere semplice; i dettagli devono aprirsi quando richiesti.

---

## 12. Backtest e risultati: come spiegarli correttamente

I backtest servono a capire come le regole si sarebbero comportate nel passato.
Non garantiscono risultati futuri.

Regole di comunicazione:
- distinguere sempre backtest da rendimento reale;
- dire se il risultato e' lordo o netto;
- dire se il regime fiscale e' amministrato o dichiarativo;
- dire se ci sono strumenti a leva;
- dire quanti swap/anno medi ci sono;
- dire il MaxDD, non solo il CAGR.

Numeri da citare con prudenza:

- APEX Legit
  Circa 42% CAGR netto nei test principali, MaxDD circa -40%.

- APEX Degen
  Circa 58% netto dichiarativo reale nei test, MaxDD circa -35%.

- APEX Dex
  Interessante come strategia DEX/lorda, ma non direttamente confrontabile con Fineco/regime amministrato.

Frase consigliata:
"Il dato piu importante non e' solo chi ha il CAGR piu alto, ma quale strategia mantiene una curva piu robusta, con drawdown gestibile e logica meno fragile."

---

## 13. Prompt per NotebookLM - Audio Overview

Usare questo prompt nelle istruzioni dell'Audio Overview:

Genera una presentazione audio in italiano su Super Investor vNext.
Deve sembrare un briefing chiaro per il proprietario dell'app, non una pubblicita'.
Spiega:
1. cosa fa l'app;
2. perche la pagina Oggi deve essere semplice;
3. come funziona OCTA;
4. come leggere i segnali OCTA;
5. come funziona APEX con Legit, Dex e Degen;
6. cosa significa momentum ultime 6 settimane;
7. cosa significa radar APEX;
8. come funzionano le automazioni;
9. quali risultati storici sono stati osservati;
10. quali limiti e rischi restano.

Stile:
- concreto;
- semplice;
- tecnico solo quando serve;
- niente promesse di rendimento;
- ricordare che l'app non esegue ordini;
- evidenziare differenza tra segnale, radar e portafoglio reale.

Durata ideale: 12-18 minuti.

---

## 14. Prompt per NotebookLM - Video Overview

Usare questo prompt nelle istruzioni del Video Overview:

Crea una presentazione video in italiano, stile slideshow professionale, su Super Investor vNext.
Il video deve spiegare l'app come se fosse un prodotto operativo personale.

Struttura:
1. Titolo e scopo dell'app.
2. Mappa: Oggi, OCTA, APEX, Portafogli.
3. Pagina Oggi: segnali, freschezza dati, mercato.
4. OCTA: strategia azionaria e segnali leggibili.
5. APEX: tre strategie separate e radar.
6. Automazioni: mattina OCTA, martedi APEX, run manuale.
7. Portafogli: gestione reale e cifrata.
8. Risultati storici e limiti.
9. Conclusione: cockpit decisionale, non consulenza.

Usa grafica pulita, pochi testi per slide, titoli brevi.
Non trasformare i backtest in promesse.
Non dire che l'app compra o vende automaticamente.

---

## 15. Fonti consigliate da caricare in NotebookLM

Non caricare tutta la cartella del progetto.
Caricare invece queste fonti pulite:

1. Questo documento:
   docs/NOTEBOOKLM_SUPER_INVESTOR_BRIEF_2026-05-31.md

2. Per APEX:
   docs/APEX_DEGEN_DECISION_2026-05-30.md
   docs/APEX_HYBRID_WALKFORWARD_2026-05-29.md
   docs/APEX_STRESS_SELECTION_2026-05-29.md
   docs/APEX_TIMING_SWEEP_2026-05-29.md

3. Per audit app/OCTA:
   docs/DEEP_REVIEW_2026-05-28.md
   docs/OCTA_SIGNAL_AUDIT.md

4. Facoltativo:
   HANDOFF.md
   Solo se vuoi dare contesto di progetto e decisioni operative.

5. Per video piu fedele all'app:
   aggiungere screenshot manuali delle quattro sezioni:
   - Oggi
   - OCTA
   - APEX home
   - APEX dettaglio
   - Portafogli

NotebookLM puo' generare Video Overview dalle fonti, ma se vuoi un vero video dimostrativo dell'interfaccia servono screenshot o una registrazione schermo. Senza immagini, il video sara' piu una presentazione concettuale che un walkthrough fedele.

---

## 16. Mini glossario

- Segnale: decisione ufficiale del motore.
- Radar: lettura informativa, non vincolante.
- Momentum: rendimento relativo in una finestra temporale.
- Lookback: periodo usato per calcolare il momentum.
- Buffer: margine minimo richiesto per cambiare asset.
- SMA: media mobile usata come filtro trend.
- MaxDD: massimo drawdown storico.
- CAGR: rendimento annuo composto nel backtest.
- Ulcer: misura della profondita' e durata dei drawdown.
- Freshness: stato di aggiornamento dei dati.
- Run manuale: aggiornamento forzato dei motori.

---

## 17. Messaggio finale da far passare

Super Investor vNext non e' una semplice dashboard piena di dati.
E' un cockpit operativo:

- dice se i dati sono arrivati;
- dice se c'e' qualcosa da fare;
- spiega perche;
- conserva lo storico;
- collega segnali, portafogli e AI;
- separa sintesi e dettaglio.

La direzione corretta e':
meno rumore in alto,
piu chiarezza nei segnali,
piu dettaglio solo quando l'utente lo apre.

