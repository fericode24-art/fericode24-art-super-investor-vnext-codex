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
- Workflow separato in `.github/workflows/octa-vnext-refresh.yml` attivo su GitHub Actions.
- Controllo freschezza in `scripts/write_freshness.py` e `dashboard/freshness.json`.

## Regola segnale fresco

La vNext considera fresco il segnale se `dashboard/data-octa.json.signal_date` coincide con la trading date attesa dopo le 08:35 ora italiana, con weekend e holiday USA esclusi.

## Stato attuale

La vNext locale gira su `http://localhost:5177/?repair=1&view=today&v=19`.

- `dashboard/data-octa.json` e `dashboard/freshness.json` vengono rigenerati dal workflow GitHub Actions.
- I portafogli letti nel datastore locale vNext sono `Massimo Master` e `Fede Smart`.
- Import file, benchmark, grafici touch e dettaglio strumenti sono disponibili anche in locale.
- Il refresh automatico attivo adesso e' GitHub Actions alle 08:35 Italia lun-ven, con deploy Netlify vNext. Non richiede PC acceso.
- Il bottone Ricontrolla nell'app ricarica dati, cloud, freshness e quotazioni. Non esegue il motore OCTA: il refresh del motore resta sul runner GitHub Actions.
- La UI mostra importi e grafici in EUR. Le quotazioni USD vengono convertite con EUR/USD, e il valore FX compare nei controlli rapidi.
- Setup runner GitHub documentato in `docs/GITHUB_RUNNER_SETUP.md`.
- Audit segnali OCTA documentato in `docs/OCTA_SIGNAL_AUDIT.md`.

## Deploy

La produzione attuale non viene toccata. Per pubblicare questa vNext serve un sito separato o un repo separato con secrets dedicati:

### GitHub Actions secrets

- `NETLIFY_SITE_ID`
- `DASHBOARD_URL`
- `SEC_USER_AGENT`
- `NETLIFY_AUTH_TOKEN` necessario per deploy automatico dal workflow
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

- apri `/?repair=1&view=octa&v=19`
- apri `/?repair=1&view=portfolios&v=19`
- verifica apertura portafoglio con PIN, dettaglio posizione, import, benchmark e grafici.
