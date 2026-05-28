# Super Investor Dashboard v2.2

PWA che ogni giorno seleziona un portafoglio di **12 titoli** (con cash fallback)
aggregando i segnali di **36 hedge fund attivi** e applicando un'architettura di
scoring **two-stage**, con notifiche push solo quando il portafoglio cambia.

## Architettura two-stage

```
36 fondi (13F SEC) ─┐
                    ├─► STAGE 1 — RADAR SCORE (dati lenti, cache 7gg)
                    │   Conviction 40% + Accumulation 30% + Insider Quality 30%
                    │   + modifier Congressional [0,+5] e Short [-15,+15]
                    │
                    └─► STAGE 2 — ENTRY FILTER (dati live, cache 24h)
                        Quality 35% + Value 25% + Momentum 40%
                        + filtri "treno partito" + Quality Red Flags (veto)
                              │
                    COMPOSITO = Radar 60% + Entry 40%
                              │
                    Sector cap 4 · Cash fallback · Tiered weights 1.2/1.0/0.8
                              │
                    Portafoglio 12 (o 8 se mercato affollato)
```

Ogni titolo ha **due punteggi indipendenti**:
- **Opportunity Score** — quanto è interessante
- **Confidence Score** — quanto sono affidabili i dati sottostanti

## Fonti dati (tutte gratuite)

| Fonte | Uso | Affidabilità |
|---|---|---|
| SEC EDGAR 13F | Conviction, Accumulation | Alta (API ufficiale) |
| SEC EDGAR XBRL | Quality, Red Flags | Alta (API ufficiale) |
| Yahoo Finance | Prezzi, momentum, short interest | Buona |
| OpenInsider | Insider Quality Score | Media (scraping) |
| CFTC COT | Market crowdedness | Alta (API ufficiale) |
| FRED (Federal Reserve) | Regime macro / sizing difensivo (v2.3) | Alta (API ufficiale) |
| CapitolTrades | Modifier congressional (+5) | Bassa (degradazione gentile) |

## Quick start

```bash
pip install -r requirements.txt
python pipeline.py --dry-run   # esecuzione di prova (no output, no deploy)
python pipeline.py             # esecuzione reale (output + deploy + notifica se rotazione)
pytest tests/                  # suite di test
```

## Struttura

```
pipeline.py            orchestratore two-stage
config.yaml            tutti i parametri di scoring
scoring/               stage1_radar, stage2_entry, insider_quality,
                       quality_red_flags, confidence, cfg
data_sources/          edgar_xbrl, openinsider, capitol_trades, cftc_cot, short_interest
engine/                sec_edgar (13F), market_data (Yahoo)
data/funds.json        36 fondi curati (CIK verificati)
dashboard/             PWA: Portafoglio / Le Tue / Storico
tests/                 suite pytest
.github/workflows/     cron giornaliero su GitHub Actions
```

## Automazione

GitHub Actions esegue `pipeline.py` ogni giorno (lun-ven 22:30 IT). Se il
portafoglio cambia: deploy automatico su Netlify + push ntfy. Altrimenti: silenzio.

## Limiti noti

- I 13F SEC hanno 45 giorni di ritardo per legge.
- CapitolTrades spesso non risponde da IP cloud → modifier congressional inattivo (segnale minore).
- CUSIP→ticker via fuzzy match: titoli OTC/ADR esotici possono non essere mappati.
- Non è consulenza finanziaria — è un signal aggregator quantitativo.
