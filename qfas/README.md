# OCTA / QFAS vNext

Sistema di selezione OCTA per 8 azioni USA mid/large cap, basato su 13F, crowding, accumulation, momentum e stato tecnico di ingresso.

## Architettura

- `qfas_config.py`: parametri, signal availability map e configurazione.
- `fund_universe.py`: universo fondi 13F.
- `data_ingestion.py`: parser SEC 13F/Form 4/8-K e provider esterni.
- `signal_decay_scorer.py`: Radar Score.
- `realtime_trigger_engine.py`: Entry Score e rinormalizzazione.
- `tax_aware_optimizer.py`: selezione 8 slot e rotazioni.
- `qfas_runner.py`: orchestratore decision cycle.
- `qfas_export_octa.py`: genera `dashboard/data-octa.json`.
- `qfas_download_prices.py`: warm cache prezzi OCTA 15 mesi.
- `qfas_prefetch_insider.py`: cache Form 4.
- `qfas_prefetch_earnings.py`: cache 8-K earnings.

## Workflow GitHub Actions

| Workflow | Cron | Cosa fa |
|---|---|---|
| `octa-vnext-refresh.yml` | 08:35 Europe/Rome lun-ven via gate UTC | Decision cycle + deploy vNext + ntfy |
| `octa-vnext-prefetch-insider.yml` | 05:00 UTC lun-ven | Form 4 cache 200 ticker |
| `octa-vnext-prefetch-earnings.yml` | 05:30 UTC lun-ven | 8-K Item 2.02 cache 200 ticker |

## Esecuzione locale

```bash
python -m qfas.qfas_download_prices
python -m qfas.qfas_export_octa --mode decision
python -m qfas.qfas_prefetch_insider --top-n 200
python -m qfas.qfas_prefetch_earnings --top-n 200
```

## Segnali

Audit dettagliato: `../docs/OCTA_SIGNAL_AUDIT.md`.

| Segnale | Stato vNext |
|---|---|
| Radar Score 13F + decay + crowding | Attivo |
| Momentum cross-sectional | Attivo |
| VIX regime | Attivo |
| Insider flow | Cache notturna presente, non usata dal live fast path |
| Earnings / PEAD | Cache notturna presente, non usata dal live fast path |
| Analyst composite | Codice presente, non usato dal live fast path |
| Congressional / squeeze | Shadow test: cache/report presenti, peso zero nel live finche non validato |

## Quick test OCTA vNext

1. Apri il `DASHBOARD_URL` vNext, non la produzione vecchia.
2. Vai su OCTA.
3. Verifica `Segnale fresco`, `engine_error=no` e data segnale uguale alla trading date attesa.
4. Controlla score, status, grafico, fondi holder e bottoni di conferma.
5. La cron GitHub vNext rigenera alle 08:35 Europe/Rome; eventuali rotazioni possono essere notificate via `ntfy`.
