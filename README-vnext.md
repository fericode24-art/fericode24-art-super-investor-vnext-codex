# Super Investor vNext Codex

Versione parallela, indipendente dalla dashboard attuale.

## Avvio locale

```powershell
cd C:\Users\fedez\OneDrive\Desktop\super-investor-vnext-codex
npm run dev
```

Apri: http://localhost:5177

## Cosa contiene

- UI mobile-first nuova in `dashboard/`.
- Motore QFAS/OCTA copiato in `qfas/`.
- Funzioni Netlify in `netlify/functions/`.
- Workflow separato in `.github/workflows/octa-vnext-refresh.yml` pronto per GitHub Actions.
- Controllo freschezza in `scripts/write_freshness.py` e `dashboard/freshness.json`.

## Regola segnale fresco

La vNext considera fresco il segnale se `dashboard/data-octa.json.signal_date` coincide con la trading date attesa dopo le 09:15 ora italiana, con weekend e holiday USA esclusi.

## Stato attuale

La vNext locale gira su `http://localhost:5177/?repair=1&view=today&v=18`.

- `dashboard/data-octa.json` ha `signal_date=2026-05-27`.
- `dashboard/freshness.json` risulta fresh per la trading date attesa.
- I portafogli letti nel datastore locale vNext sono `Massimo Master` e `Fede Smart`.
- Import file, benchmark, grafici touch e dettaglio strumenti sono disponibili anche in locale.
- Il refresh automatico attivo adesso e' una cron Codex locale alle 08:35 Italia lun-ven: richiede PC acceso, internet attivo e niente sospensione. GitHub Actions e' il target per il runner cloud definitivo.
- Il bottone Ricontrolla nell'app ricarica dati, cloud, freshness e quotazioni. Non esegue il motore OCTA: il refresh del motore resta sul runner Codex locale o sul futuro runner cloud.
- La UI mostra importi e grafici in EUR. Le quotazioni USD vengono convertite con EUR/USD, e il valore FX compare nei controlli rapidi.
- Setup runner GitHub documentato in `docs/GITHUB_RUNNER_SETUP.md`.

## Deploy

La produzione attuale non viene toccata. Per pubblicare questa vNext serve un sito separato o un repo separato con secrets dedicati:

### GitHub Actions secrets

- `NETLIFY_SITE_ID`
- `DASHBOARD_URL`
- `SEC_USER_AGENT`
- `NETLIFY_AUTH_TOKEN` opzionale ma necessario per deploy automatico dal workflow
- `FINNHUB_API_KEY` opzionale
- `NTFY_TOPIC` opzionale per notifiche

### Netlify environment variables

- `OCTA_SYNC_TOKEN`
- `TRACKER_SYNC_TOKEN`
- `GROQ_API_KEY` opzionale per AI

`DASHBOARD_URL` deve puntare al sito vNext, non alla produzione vecchia. In locale il motore usa `http://localhost:5177` come fallback.

## Smoke test rapido

```powershell
npm run check
```

Nel browser:

- apri `/?repair=1&view=octa&v=18`
- apri `/?repair=1&view=portfolios&v=18`
- verifica apertura portafoglio con PIN, dettaglio posizione, import, benchmark e grafici.
