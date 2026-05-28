# GitHub runner vNext

Questa guida porta il refresh OCTA fuori dal PC locale. La dashboard vecchia non viene toccata.

## Repo

Repo consigliato: `super-investor-vnext-codex`.

Il repo deve contenere questa cartella vNext, inclusi:

- `.github/workflows/octa-vnext-refresh.yml`
- `.github/workflows/octa-vnext-prefetch-insider.yml`
- `.github/workflows/octa-vnext-prefetch-earnings.yml`
- `dashboard/`
- `qfas/`
- `data/russell_1000.json`
- `data/backtest/hist_13f_l40.json`
- `data/backtest/sectors_full.json`

Le cache grosse dei prezzi restano fuori git. GitHub Actions rigenera `data/backtest/prices_octa.csv`.

## Secrets GitHub Actions

Configura questi secrets nel repo vNext:

- `DASHBOARD_URL`: URL pubblico Netlify vNext.
- `NETLIFY_SITE_ID`: site id Netlify vNext.
- `SEC_USER_AGENT`: user agent SEC con email reale.

Necessario per pubblicare:

- `NETLIFY_AUTH_TOKEN`: abilita deploy Netlify diretto dal workflow. Senza questo secret il workflow genera e committa il segnale, ma salta il deploy.

Opzionali:

- `FINNHUB_API_KEY`: abilita segnali analyst/earnings quando usati dal motore.
- `NTFY_TOPIC`: invia notifiche refresh/failure.

## Variabili Netlify vNext

Sul sito Netlify vNext configura:

- `OCTA_SYNC_TOKEN`
- `TRACKER_SYNC_TOKEN`

Opzionale:

- `GROQ_API_KEY`

## Orari

Il workflow principale usa due schedule UTC:

- `06:35 UTC`
- `07:35 UTC`

Un gate interno fa passare solo la run che corrisponde alle `08:35 Europe/Rome`, quindi copre sia ora legale sia ora solare senza doppio deploy.

## Test

Prima prova manuale:

1. Apri GitHub Actions.
2. Seleziona `OCTA vNext Daily Refresh`.
3. Premi `Run workflow`.
4. Controlla che generi `dashboard/data-octa.json` e `dashboard/freshness.json`.
5. Controlla il deploy sul sito vNext.

Stato verificato: run manuale GitHub Actions + deploy Netlify completati con successo. Una eventuale automazione locale puo' restare solo come backup temporaneo.
