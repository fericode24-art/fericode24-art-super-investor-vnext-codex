# NotebookLM - Master audio strategie Super Investor

Data: 2026-05-31
App: Super Investor vNext
Sito pubblico: https://super-investor-vnext-codex.netlify.app
Repo ufficiale: fericode24-art/fericode24-art-super-investor-vnext-codex

Questo documento e' pensato per generare una presentazione audio NotebookLM.
Il focus non e' mostrare la UI, ma spiegare bene:

- cosa fa l'app;
- perche esistono le strategie;
- come funzionano OCTA e APEX;
- quali numeri storici sono stati osservati;
- come leggere backtest, drawdown, radar e automazioni;
- cosa non bisogna confondere con una promessa di rendimento.

Nota obbligatoria: Super Investor e' uno strumento informativo e operativo personale.
Non e' consulenza finanziaria, non esegue ordini e non garantisce risultati futuri.
L'utente decide sempre se operare.

---

## 1. Obiettivo della presentazione audio

La presentazione audio deve sembrare un briefing chiaro e ragionato, non una
lettura tecnica di codice.

Tono:

- diretto;
- comprensibile;
- prudente sui risultati futuri;
- concreto sull'uso operativo;
- abbastanza tecnico da essere credibile, ma senza gergo inutile.

Messaggio principale:

Super Investor vNext nasce per non dover rincorrere segnali, file, grafici,
broker e fogli separati. L'app mette in un solo posto:

1. lo stato dei dati;
2. i segnali OCTA;
3. le tre strategie APEX;
4. il portafoglio reale registrato dall'utente;
5. le automazioni che aggiornano i motori.

La priorita' non e' "vedere tanti numeri", ma sapere:

- se i dati sono arrivati;
- se oggi c'e' qualcosa da fare;
- cosa va detenuto;
- perche il motore lo dice;
- quanto e' affidabile il contesto rispetto ai backtest.

---

## 2. Apertura consigliata per l'audio

Testo guida:

"Super Investor vNext e' una dashboard personale per seguire strategie,
segnali e portafogli. Non compra e non vende da sola. Il suo compito e'
dare una risposta semplice a tre domande: i dati di oggi sono freschi? C'e'
qualcosa da fare? Se devo approfondire, dove trovo il motivo?"

"La dashboard si divide in quattro aree: Oggi, OCTA, APEX e Portafogli.
Oggi e' il cockpit rapido. OCTA e' la strategia azionaria. APEX raccoglie
tre strategie di rotazione. Portafogli serve a registrare e controllare la
parte reale, cioe' quello che l'utente ha davvero comprato."

---

## 3. Pagina Oggi - logica strategica

La pagina Oggi e' volutamente sintetica.

Deve rispondere a poche domande:

- OCTA ha un segnale fresco?
- APEX ha un segnale fresco?
- Ci sono nuove azioni da valutare?
- I motori hanno girato senza errore?
- Il contesto di mercato e' calmo o teso?

Elementi principali:

- badge OCTA;
- badge APEX con tutte e tre le strategie;
- badge Mercato, con VIX e principali asset;
- stato run/freschezza dati;
- notifiche operative, non informazioni secondarie.

Principio di design:

La pagina Oggi non deve diventare un report completo. Se l'utente vuole
grafici, storico, Radar 40, ranking o dettagli, entra nelle sezioni dedicate.

---

## 4. OCTA - che cos'e'

OCTA e' la strategia azionaria della dashboard.

L'idea e' costruire una classifica di titoli interessanti usando piu livelli:

- presenza nei fondi osservati;
- accumulo o esposizione dei fondi;
- momentum;
- qualita' del punto di ingresso;
- filtri tecnici;
- segnali extra, quando disponibili;
- ranking finale.

OCTA non e' pensata per comprare tutto. E' pensata per ordinare il mercato e
far emergere le opportunita' piu coerenti con la logica del motore.

---

## 5. OCTA - come leggere i segnali

I vecchi nomi troppo tecnici sono stati semplificati.

Esempi di segnali leggibili:

- Compra: breakout
  Il prezzo sta rompendo verso l'alto. Il motore lo considera comprabile se
  resta alto in classifica.

- Compra: ritracciamento
  Il trend resta buono, ma il prezzo ha respirato. L'idea e' un ingresso piu
  ordinato rispetto all'acquisto sui massimi.

- Compra: ok
  Non ci sono blocchi tecnici evidenti. Si compra solo se score e portafoglio
  lo richiedono.

- Vendi: trend rotto
  Il quadro tecnico si e' indebolito. Il motore segnala uscita o forte
  prudenza.

- Vendi: sostituito
  Il titolo non e' necessariamente "brutto", ma oggi ci sono candidati
  migliori nella rotazione.

Questo linguaggio serve a far capire il motivo senza dover leggere un codice
interno come "fresh momentum" o "rotation out".

---

## 6. OCTA - Radar 40

Radar 40 e' la classifica completa dei migliori candidati del motore OCTA.

Nella lettura audio va spiegato cosi:

"Il Radar 40 non e' la prima cosa da guardare al mattino. Prima conta sapere
se il portafoglio richiede un'azione. Poi, se si vuole capire il contesto,
Radar 40 mostra quali titoli stanno emergendo, con priorita', motivo,
extra score e forza."

Campi importanti:

- Ticker;
- priorita';
- motivo;
- extra score;
- forza.

Extra score:

Indica punti aggiunti o tolti dai segnali extra. Se e' positivo, il titolo ha
un contributo favorevole dai dati extra; se e' negativo, il contributo e'
sfavorevole.

Forza:

E' una lettura relativa del momentum del titolo.

---

## 7. OCTA - portafoglio reale

OCTA non deve solo mostrare segnali. Deve anche permettere di registrare cosa
e' stato fatto.

Funzioni operative:

- vedere le 8 posizioni registrate;
- vedere valore stimato, investito e P/L;
- vedere prezzo live in euro;
- aprire una scheda titolo;
- registrare operazioni;
- segnare un segnale come eseguito;
- usare AI per farsi spiegare un titolo o un segnale.

Il punto e':

"Il segnale del motore e il portafoglio reale non sono la stessa cosa. L'app
serve anche a riconciliare i due mondi."

---

## 8. APEX - visione generale

APEX e' la sezione delle strategie di rotazione.

La logica comune e':

- non detenere mille asset insieme;
- scegliere un asset dominante;
- usare momentum e filtri di trend;
- aggiornare il segnale in automatico;
- mostrare anche un radar informativo per capire se sta maturando un cambio.

APEX contiene tre strategie di pari dignita':

1. APEX Legit;
2. APEX Dex;
3. APEX Degen.

La prima schermata APEX deve far capire subito:

- nome della strategia;
- asset da detenere adesso;
- radar;
- eventuale alert;
- ultimo run;
- se serve o no intervenire.

Poi, cliccando una strategia, si entra nei dettagli.

---

## 9. APEX Legit

APEX Legit e' la versione principale pensata per operativita' tipo Fineco.

Meccanica sintetica:

- universo: BTC, Oro, S&P 500, cash/XEON;
- timing: martedi;
- lookback: 6 settimane;
- buffer: 3 punti percentuali;
- filtro anti-crash: BTC sopra/sotto SMA30;
- fiscalita': modello netto in regime amministrato italiano;
- segnale: un solo asset alla volta.

Perche e' nata:

La strategia nasce da una logica BTC-centrica, ma e' stata migliorata con
test su timing, lookback, buffer, filtro SMA e robustezza.

Punto chiave:

Il filtro SMA su BTC evita di forzare BTC quando il trend di fondo e' rotto.
La correzione importante e' stata il "ripiego SMA": quando BTC viene bocciato
dal filtro, il motore non deve dimenticarsi dell'S&P 500. Deve rivalutare Oro,
S&P 500 e cash, scegliendo l'alternativa valida piu forte.

Numeri storici indicativi:

- circa 42% CAGR netto nei test principali;
- miglioramento verso circa 43% e drawdown intorno a -37% quando il ripiego
  SMA considera anche S&P 500;
- APEX R classica, piu semplice, era intorno a circa 31% netto;
- la variante definitiva e' stata preferita per equilibrio tra rendimento,
  logica e robustezza.

Come comunicarlo:

"APEX Legit e' la gamba principale: aggressiva, ma ancora comprensibile. Non
insegue il mercato ogni giorno; aggiorna il segnale in modo ordinato e usa
un filtro per evitare alcune fasi peggiori di BTC."

---

## 10. APEX Dex

APEX Dex e' una strategia separata.

Non e' una copia di Legit.

Universo:

- BTC spot;
- oro on-chain tramite PAXG;
- stablecoin.

Caratteristiche:

- ambiente DEX;
- operativita' 24/7;
- niente S&P 500;
- logica BTC/Oro/stablecoin;
- fiscalita' non sovrapponibile automaticamente a Fineco;
- da trattare come ramo separato.

Come comunicarlo:

"APEX Dex serve a ragionare su un ambiente diverso, piu crypto-native. Non
va confusa con la strategia Fineco, perche strumenti, orari, costi, rischi e
fiscalita' cambiano."

---

## 11. APEX Degen

APEX Degen e' la strategia piu aggressiva.

Non sostituisce APEX Legit. E' una terza gamba separata.

Universo:

- BTC;
- Gold 2x;
- CL2 / USA 2x;
- XEON o cash difensivo.

Meccanica salvata come riferimento:

- pure relative momentum;
- lookback 6 settimane;
- buffer 5 punti percentuali;
- filtro BTC SMA30;
- versione validata piu realistica: base solo-BTC30;
- radar giornaliero informativo, non operativo.

Nota importante sui numeri:

Una prima ricerca aveva prodotto numeri vicini al 65% annuo, ma la validazione
piu severa con fiscalita' reale su strumenti leveraged ha corretto il dato.
Il riferimento piu prudente da comunicare e':

- circa 58,7% netto dichiarativo reale;
- circa 481.000 euro finali da 10.000 euro iniziali nel periodo testato;
- MaxDD di mercato intorno a -35%;
- strategia molto aggressiva;
- lookback 6 molto sensibile, quindi da non vendere come certezza futura.

Come comunicarlo:

"APEX Degen e' potente, ma non va confusa con una strategia tranquilla. Usa
asset a leva, quindi i numeri storici sono alti, ma anche la sensibilita' a
timing, volatilita' e fiscalita' e' molto piu alta."

---

## 12. Radar APEX

Il radar APEX non e' il segnale ufficiale.

Serve a rispondere a:

- se leggessi il motore oggi, cosa vincerebbe?
- l'asset ufficiale e' ancora coerente?
- c'e' una divergenza da tenere d'occhio?
- un filtro sta iniziando a peggiorare?

La regola operativa resta:

- si opera sul segnale ufficiale;
- il radar e' un avviso;
- il radar non deve generare da solo uno swap.

La barra radar puo' essere spiegata cosi:

"Da una parte c'e' l'asset ufficiale che la strategia dice di detenere. Dall'
altra parte c'e' l'asset che il radar vede piu forte oggi. La barra mostra se
la pressione verso un possibile cambio e' piccola o significativa."

---

## 13. Backtest - come parlarne senza promettere

Il backtest serve a capire come le regole si sarebbero comportate nel passato.

Non e' una promessa.

Metriche importanti:

- CAGR: crescita annua composta storica;
- MaxDD: massimo drawdown storico;
- Calmar: rendimento rapportato al drawdown;
- Ulcer: misura della sofferenza della curva;
- R2/linearita': quanto la curva e' regolare;
- swap/anno: quanto spesso si deve operare;
- anni positivi: quante annate hanno chiuso sopra zero;
- forward/walk-forward: test per capire se una strategia regge fuori dal
  periodo su cui sembra ottimizzata.

Messaggio importante:

"Una strategia non vince solo perche ha il CAGR piu alto. Deve essere
comprensibile, eseguibile, fiscalmente sensata, non troppo fragile e con un
drawdown che l'utente riesce davvero a sopportare."

---

## 14. Automazioni

L'app e' costruita per aggiornarsi senza dipendere dal PC acceso.

OCTA:

- gira ogni mattina feriale;
- usa piu finestre e retry;
- obiettivo: non saltare il segnale fresco.

APEX:

- gira il martedi pomeriggio, intorno alle 15:30 Italia;
- aggiorna Legit, Dex e Degen insieme;
- se necessario puo' essere rilanciato con il bottone Run tutto.

Run manuale:

- il bottone Run tutto forza i motori;
- serve quando l'utente vuole aggiornare tutto subito;
- e' separato dalla semplice lettura/aggiornamento dati.

Filosofia:

"Meglio una run in piu che un segnale mancato."

---

## 15. Portafogli personali

La sezione Portafogli e' la parte tipo home banking personale.

Funzioni da comunicare:

- portafogli cifrati con PIN;
- apertura/creazione portafoglio;
- import da file;
- backup export/import;
- sync cloud;
- prezzo manuale per strumenti senza quotazione;
- modifica composizione;
- quick buy/sell;
- storico movimenti;
- AI sul portafoglio.

Messaggio:

"Le strategie dicono cosa fare. I portafogli mostrano cosa e' stato fatto
davvero."

---

## 16. Fonti consigliate da caricare insieme a questo file

Per una buona Audio Overview, caricare:

1. Questo file.
2. `docs/APEX_DEGEN_DECISION_2026-05-30.md`
3. `docs/APEX_HYBRID_WALKFORWARD_2026-05-29.md`
4. `docs/APEX_STRESS_SELECTION_2026-05-29.md`
5. `docs/APEX_TIMING_SWEEP_2026-05-29.md`
6. `docs/APEX_SP_CONSTRAINT_COMPARE_2026-05-29.md`
7. `docs/OCTA_SIGNAL_AUDIT.md`
8. `docs/DEEP_REVIEW_2026-05-28.md`

Non caricare direttamente tutta la cartella repo: NotebookLM leggerebbe anche
codice, file tecnici e prove, creando confusione.

---

## 17. Prompt pronto per Audio Overview

Usa questo prompt dentro NotebookLM:

"Crea una presentazione audio in italiano, chiara e professionale, su Super
Investor vNext. Spiega prima il problema che risolve l'app, poi le sezioni
Oggi, OCTA, APEX e Portafogli. Dedica una parte importante alle strategie:
OCTA come motore azionario e APEX come insieme di tre strategie, Legit, Dex e
Degen. Spiega la logica dei segnali, il ruolo del radar, le automazioni, e i
principali risultati storici dei backtest. Distingui sempre i risultati
storici dai risultati attesi futuri. Non fare promesse finanziarie. Usa un
linguaggio semplice, ma non banale. Il tono deve essere quello di un briefing
operativo per una persona che usa davvero questa app per controllare segnali e
portafogli."

