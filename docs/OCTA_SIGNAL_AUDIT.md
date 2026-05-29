# OCTA vNext signal audit

Stato audit: 2026-05-28.

Nota 2026-05-28 pomeriggio: questa nota e' storica e descrive lo stato precedente al profilo `2.6.0-cached`. Il live attuale non e' piu il fast path puro con `skip_external_signals=True`: ora il refresh usa `external_mode=cached`. Per la revisione aggiornata vedere `docs/DEEP_REVIEW_2026-05-28.md`.

Questa nota separa i segnali realmente usati dal motore live vNext dai segnali presenti nel codice ma non agganciati al profilo attivo.

## Profilo live attivo

Il refresh GitHub Actions chiama `qfas.qfas_export_octa --mode decision`.

In `qfas/qfas_export_octa.py` il decision cycle viene lanciato con:

```python
skip_external_signals=True
```

Questo significa che la vNext live oggi usa il profilo fast path validato finora. Il prefetch notturno insider/earnings puo' generare cache corrette, ma quelle cache non entrano ancora nel punteggio live finche questo flag resta attivo.

## Usati nel punteggio live

| Area | Stato | Dove |
|---|---|---|
| 13F radar score | Attivo | `qfas/signal_decay_scorer.py`, `qfas/qfas_runner.py` |
| Conviction dei fondi | Attivo | ranking cross-sectional di `raw_conviction` |
| Accumulation | Attivo | variazioni 13F filtrate in `signal_decay_scorer` |
| Crowding | Attivo | moltiplicatore crowding nel radar |
| Momentum prezzi | Attivo | `compute_momentum_pct` in `realtime_trigger_engine.py` |
| Entry status tecnico | Attivo | `classify_entry_status` |
| VIX/regime e sizing | Attivo | `qfas_export_octa.py`, `tax_aware_optimizer.py` |
| Portafoglio reale utente | Attivo | `fetch_portfolio_from_cloud` e posizioni OCTA cloud |
| Vincoli optimizer | Attivo | 8 slot, settore, anti-churn, drawdown/TLH |

Nel profilo attivo l'`entry_score` usato da `qfas_runner.py` e' il momentum, poi viene combinato con il radar score via:

```text
opportunity_score = 50% radar + 50% entry
```

## Presenti ma non usati dal live attuale

| Segnale | Stato reale | Motivo |
|---|---|---|
| Insider Form 4 | Prefetch/cache presente | Saltato da `skip_external_signals=True` |
| Earnings 8-K dates | Prefetch/cache presente | Saltato perche PEAD non viene calcolato in fast path |
| PEAD surprise | Codice presente | Richiede surprise, normalmente `FINNHUB_API_KEY`; non usato in fast path |
| Analyst composite | Codice presente | Richiede provider esterno; non usato in fast path |
| Congressional trades | Codice presente | Scraping fragile; non usato in fast path |
| Short squeeze/FINRA | Codice presente | Non usato in fast path |

Nota importante: `data/backtest/insider_cache.json` e `data/backtest/earnings_cache.json` sono utili come preparazione, ma oggi non cambiano i BUY/SELL live.

## Workflow secondari

I workflow:

- `.github/workflows/octa-vnext-prefetch-insider.yml`
- `.github/workflows/octa-vnext-prefetch-earnings.yml`

ora sono pensati come manutenzione cache e test controllato:

- validano `SEC_USER_AGENT` prima di partire;
- permettono dispatch manuale con `top_n` ridotto;
- validano che la cache prodotta sia JSON coerente;
- scrivono un summary leggibile nella pagina GitHub Actions.

Questi workflow non deployano il sito. Aggiornano solo le cache se cambiano.

## Raccomandazione

Non attiverei tutto il blocco esterno in produzione di colpo.

La via piu pulita e':

1. lasciare il refresh 08:35 con fast path attuale finche la vNext deve essere affidabile;
2. creare un esperimento separato `use_cached_signals_only`;
3. nell'esperimento attivare solo insider Form 4 cached e earnings 8-K cached;
4. lasciare fuori analyst, congressional e squeeze finche non hanno un controllo qualita dedicato;
5. confrontare backtest e output giornalieri contro il profilo attuale prima di cambiare il live.

Decisione pratica: le cache vanno mantenute, ma per ora sono materiale di test, non segnali live.
