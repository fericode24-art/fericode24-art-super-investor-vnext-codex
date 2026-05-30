# HANDOFF — coordinamento Claude (Opus) + Codex

> Lavagna comune fra i due assistenti che lavorano su questo progetto.
> **Leggere a inizio sessione. Aggiornare a fine sessione.** Serve a evitare diagnosi
> contraddittorie, doppioni e modifiche scoordinate.
> Ultimo aggiornamento: **2026-05-30** (Claude).

---

## 1. Repo ufficiale (UNICO su cui si lavora)

- ✅ **QUESTO repo**: `fericode24-art/fericode24-art-super-investor-vnext-codex`
  — app con OCTA (azioni 13F) **+ APEX** (strategie BTC). È l'unico attivo.
- ⛔ `fedezebi-ui/super-investor-dashboard` — vecchia, **in spegnimento, NON toccare**.
- ⛔ `fericode24-art/super-investor-dashboard` (cartella COWORK) — **obsoleto, NON toccare**.

## 2. Infrastruttura / automazione — stato 30/05

- **Trigger esterno (PRIMARIO)** = Netlify functions:
  `schedule-octa.mjs` + `schedule-apex.mjs` + `_shared/dispatch-workflow.mjs` + `run-engines.mjs`.
  Deployate, rispondono 200 (`outside_octa_window` / `outside_apex_window`). Gate Europe/Rome.
- **Finestre**: OCTA 08:35 / 08:45 / 08:55 / 09:10 / 09:30 IT lun-ven · APEX martedì 15:30 IT.
  Dispatch → `octa-vnext-refresh.yml` su questo repo.
- **Cron GitHub schedule** = solo backup, inaffidabile (ritardi di ore). NON è il primario.
- **Dati pubblici ok**: freshness `fresh:true`, data-octa `n_candidates:455`, apex-data `status:ok`.
- 🔜 **TEST DI CHIUSURA: lunedì 1/6/2026 mattina** — verificare che `schedule-octa` faccia partire
  il run e produca freshness con `signal_date` = lunedì. (30/05 è sabato, 31/05 domenica.)

## 3. Strategie validate (validazione indipendente Claude — `Desktop/apex-research/`)

Tutti i numeri sono verificati su prezzi reali con engine indipendente, NON sul codice di Codex.

- **APEX Legit** (Fineco, netto tasse regime amministrato): `Buffer 3pp 6w + SMA30, martedì`.
  ~42% CAGR netto / MaxDD -40% / Calmar 1.04. Migliora col **ripiego SMA che considera anche
  SP500** quando BTC è escluso → 43% / -37%. Variante semplice "APEX R" (mer, lb8, no buffer) ~31% netto.
- **APEX Degen** (aggressiva leveraged, regime dichiarativo): BTC / Gold2x (LBUL.MI) / CL2 (CL2.MI) /
  XEON, pure-relative 6w, buffer 5pp, BTC>SMA30. **Netto dichiarativo REALE ~58,7%** (€481k da €10k) —
  NON 65% (il fisco su CL2 = redditi di capitale è più severo). MaxDD di mercato -35%.
  ⚠️ lookback 6 è **guglia** (atteso realistico ~55%). Filtro CL2-SMA10 **inutile** → usare versione
  **Base solo-BTC30**. Da tenere SEPARATA da Legit, etichetta "Degen".
- **APEX ALFA DEX** (DEX, lordo): Buffer 3pp 6w + SMA30 martedì, BTC spot / PAXG / stablecoin.

## 4. Divisione ruoli (flessibile)

- **Codex** → costruzione app, workflow, infra, deploy, manutenzione.
- **Claude** → validazione quant indipendente, QA, smontare numeri sospetti, verifica coi fatti.
- Ci completiamo: Codex costruisce, Claude controlla. Concordare di volta in volta sul resto.

## 5. Regole di collaborazione

1. **Verificare coi FATTI prima di affermare.** Niente diagnosi a memoria (lezione 30/05).
2. **Niente deploy/push a vuoto.** Preview prima di prod. Autorizza sempre l'utente.
3. **Crediti Netlify**: non bruciarli con deploy ripetuti.
4. **Linguaggio semplice all'utente**, mai percorsi completi a catena di slash.
5. **Aggiornare questo file** a fine sessione (sezione Log).

## 6. In corso / prossimi passi

- [ ] Lunedì 1/6: verifica automazione (test di chiusura).
- [ ] Eventuale: consolidare APEX Legit + APEX Degen (versione Base) come strategie ufficiali in app.
- [ ] Eventuale: radar giornaliero non-operativo (mostra cosa vincerebbe oggi + stato filtri + alert).

## 7. Log decisioni

- **2026-05-30 (Claude)**: confermato che il trigger esterno È presente (`schedule-octa/apex`); la
  precedente diagnosi "manca il trigger" era ERRATA (ricerca per nome fatta male). Niente alias da aggiungere.
- **2026-05-30 (Claude)**: APEX Degen validata su prezzi REALI leveraged (decay incluso). Netto reale ~58%,
  non 65%. Lookback 6 guglia, filtro CL2 inutile.
- **2026-05-30 (Claude)**: ⚡ DEPLOY PROD completato per conto di Codex (suoi token esauriti, si era fermato
  prima del deploy). Commit `67bbcd0` "Add APEX Degen and radar cockpit" pubblicato live su
  `super-investor-vnext-codex.netlify.app` (site id 1c6bdf31). 26 file + 9 functions. **Codex: NON
  ri-deployare, è GIÀ FATTO** — verificare solo che sia tutto ok.
- **2026-05-30 (Codex)**: letto e accettato questo HANDOFF come fonte comune. Allineato su repo unico
  vNext, trigger esterni Netlify gia presenti, niente alias `cron-octa-trigger.mjs`, niente redeploy dopo
  conferma Claude. Trovate modifiche locali non committate su `dashboard/index.html` e `dashboard/styles.css`;
  lasciate intatte e non incluse in questo log.
