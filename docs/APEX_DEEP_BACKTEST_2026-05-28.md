# APEX deep backtest - 2026-05-28

Stato: ricerca quantitativa, nessun deploy.

## Dati

- Fonte: Yahoo Finance chart API, profilo proxy EUR.
- BTC: `BTC-USD / EURUSD=X`.
- Oro: `GC=F / EURUSD=X`.
- S&P 500: `^GSPC / EURUSD=X`.
- Cash: `XEON.MI` quando disponibile.
- Osservazioni settimanali open: 611.
- Periodo: 2014-09-17 -> 2026-05-27.
- Query Yahoo corretta con `period1/period2`; `range=max` puro veniva downsamplato a dati mensili.

Nota importante: per il segnale live Fineco useremo strumenti EUR/intraday. Il backtest lungo usa proxy per avere storia dal 2014; gli strumenti WisdomTree BTC quotati EUR su Yahoo non hanno storia sufficiente.

## Confronto Principale Allineato

Lookback 8 settimane, prezzo open, costo cambio 30 bps, stesso periodo di partenza per benchmark.

| strategia | CAGR | Max DD | Sharpe | Finale 10k |
| --- | --- | --- | --- | --- |
| APEX_8w_open_30bps | 65.64% | -72.1% | 1.189 | 3377524.0 |
| BTC | 59.66% | -79.93% | 1.013 | 2209167.0 |
| GOLD | 13.0% | -17.38% | 0.89 | 40945.0 |
| SP500 | 12.67% | -29.38% | 0.82 | 39597.0 |
| EQUAL_BTC_GOLD_SP500 | 45.61% | -75.92% | 0.927 | 763236.0 |

Nota comparabilita': Claude parte dal 2018. Qui il capitale parte nel 2018, mentre lo storico pre-2018 serve solo a calcolare il primo momentum 8w disponibile.

## Confronto Claude 2018

Periodo richiesto: 2018-01-01 -> 2026-05-27. Benchmark allineati alle stesse date settimanali di APEX 8w/open/30bps.

| strategia | inizio | fine | CAGR | Max DD | Sharpe | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- |
| APEX_8w_open | 2018-01-03 | 2026-05-27 | 38.33% | -66.39% | 0.908 | 152339.0 |
| BTC_BH | 2018-01-03 | 2026-05-27 | 21.83% | -75.75% | 0.623 | 52465.0 |
| EQUAL_BH | 2018-01-03 | 2026-05-27 | 17.51% | -43.93% | 0.725 | 38745.0 |

Varianti candidate nello stesso periodo 2018-oggi. Questa tabella serve a capire se cambiare davvero regola o se tenere APEX 8w come base.

| strategia | CAGR | Max DD | Sharpe | Switch | Finale 10k | BTC% | Cash% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Buffer 2pp 6w | 50.22% | -60.81% | 1.115 | 74 | 304400.0 | 45.0% | 5.0% |
| Confirm2 6w | 47.33% | -53.0% | 1.058 | 56 | 258662.0 | 48.6% | 6.2% |
| Confirm2+buffer 6w | 47.33% | -53.0% | 1.058 | 56 | 258662.0 | 48.6% | 6.2% |
| Pure-relative 8w | 46.2% | -51.7% | 1.042 | 92 | 242466.0 | 44.3% | 5.7% |
| APEX Rev2 6w | 44.26% | -60.32% | 1.027 | 113 | 216676.0 | 46.8% | 6.8% |
| Buffer 5pp 8w | 40.95% | -66.9% | 0.952 | 55 | 178325.0 | 44.7% | 6.2% |
| Confirm2 10w | 41.29% | -49.71% | 0.934 | 47 | 182005.0 | 48.4% | 6.2% |
| APEX Rev2 8w originale | 38.33% | -66.39% | 0.908 | 91 | 152339.0 | 49.3% | 5.7% |
| Buffer 5pp 16w | 37.81% | -49.71% | 0.9 | 34 | 147611.0 | 45.2% | 5.9% |
| APEX Rev2 17w best full | 29.08% | -69.09% | 0.753 | 65 | 85222.0 | 47.9% | 4.1% |

## Scan Lookback

APEX Rev2 originale, prezzo open, costo 30 bps. Top 10 per CAGR.

| lookback | CAGR | Max DD | Sharpe | Switch | BTC% | Cash% |
| --- | --- | --- | --- | --- | --- | --- |
| 17 | 69.41% | -74.34% | 1.208 | 86 | 55.3% | 4.6% |
| 8 | 65.64% | -72.1% | 1.189 | 123 | 54.3% | 6.6% |
| 6 | 64.56% | -67.06% | 1.198 | 154 | 52.5% | 7.3% |
| 15 | 64.25% | -58.25% | 1.161 | 86 | 55.3% | 4.9% |
| 19 | 63.7% | -59.91% | 1.154 | 87 | 56.0% | 3.7% |
| 13 | 62.93% | -62.75% | 1.152 | 92 | 54.1% | 5.9% |
| 18 | 62.76% | -74.85% | 1.141 | 86 | 54.7% | 3.9% |
| 7 | 62.19% | -62.89% | 1.167 | 149 | 53.1% | 7.5% |
| 5 | 62.08% | -70.05% | 1.156 | 172 | 53.9% | 8.9% |
| 16 | 61.01% | -59.96% | 1.135 | 93 | 54.2% | 4.4% |

## Varianti

Prezzo open, costo 30 bps. Varianti ordinate per Sharpe/CAGR.

| variant | lookback | CAGR | Max DD | Sharpe | Switch | BTC% | Cash% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pure_relative | 8 | 71.36% | -59.91% | 1.265 | 124 | 50.5% | 6.6% |
| confirm2 | 6 | 70.24% | -60.98% | 1.263 | 74 | 54.1% | 6.5% |
| confirm2_buffer2 | 6 | 70.24% | -60.98% | 1.263 | 74 | 54.1% | 6.5% |
| buffer_2pp | 6 | 68.95% | -67.47% | 1.253 | 106 | 50.8% | 5.8% |
| buffer_5pp | 8 | 69.0% | -72.53% | 1.229 | 74 | 51.0% | 6.3% |
| buffer_5pp | 6 | 66.33% | -68.46% | 1.226 | 87 | 48.8% | 4.6% |
| confirm2 | 10 | 68.66% | -58.25% | 1.215 | 60 | 54.3% | 7.0% |
| confirm2_buffer2 | 10 | 68.66% | -58.25% | 1.215 | 60 | 54.3% | 7.0% |
| buffer_5pp | 16 | 67.29% | -58.25% | 1.202 | 49 | 51.7% | 5.9% |
| apex_rev2 | 6 | 64.56% | -67.06% | 1.198 | 154 | 52.5% | 7.3% |
| apex_rev2 | 8 | 65.64% | -72.1% | 1.189 | 123 | 54.3% | 6.6% |
| buffer_5pp | 12 | 64.88% | -58.25% | 1.18 | 58 | 50.8% | 5.5% |

## Sottoperiodi

APEX 8w/open/30bps contro BTC buy&hold e paniere equal-weight, benchmark allineati al primo segnale del sottoperiodo.

| periodo | strategia | CAGR | Max DD | Sharpe |
| --- | --- | --- | --- | --- |
| full | APEX_8w_open | 65.64% | -72.1% | 1.189 |
| full | BTC_BH | 59.66% | -79.93% | 1.013 |
| full | EQUAL_BH | 45.61% | -75.92% | 0.927 |
| claude_comparable_2018_now | APEX_8w_open | 38.33% | -66.39% | 0.908 |
| claude_comparable_2018_now | BTC_BH | 21.83% | -75.75% | 0.623 |
| claude_comparable_2018_now | EQUAL_BH | 17.51% | -43.93% | 0.725 |
| cycle_2014_2017 | APEX_8w_open | 177.53% | -39.4% | 1.827 |
| cycle_2014_2017 | BTC_BH | 241.12% | -40.59% | 2.007 |
| cycle_2014_2017 | EQUAL_BH | 144.13% | -17.45% | 2.076 |
| bear_recovery_2018_2020 | APEX_8w_open | 23.6% | -66.39% | 0.65 |
| bear_recovery_2018_2020 | BTC_BH | 21.68% | -75.75% | 0.637 |
| bear_recovery_2018_2020 | EQUAL_BH | 15.06% | -26.9% | 0.742 |
| mania_bear_2021_2023 | APEX_8w_open | 34.41% | -49.07% | 0.86 |
| mania_bear_2021_2023 | BTC_BH | 11.78% | -72.8% | 0.487 |
| mania_bear_2021_2023 | EQUAL_BH | 10.2% | -35.92% | 0.518 |
| recent_2024_2026 | APEX_8w_open | 47.22% | -21.57% | 1.206 |
| recent_2024_2026 | BTC_BH | 21.21% | -47.78% | 0.633 |
| recent_2024_2026 | EQUAL_BH | 25.15% | -20.32% | 1.102 |

## Robustezza Lookback Per Regime

APEX Rev2 originale, prezzo open, costo 30 bps. Classifica per mediana Sharpe/CAGR sui sottoperiodi, non sul periodo totale.

| lookback | median CAGR | min CAGR | median Sharpe | worst DD |
| --- | --- | --- | --- | --- |
| 6 | 44.26% | 32.12% | 1.027 | -60.32% |
| 7 | 40.53% | 26.92% | 0.967 | -55.29% |
| 8 | 38.33% | 23.6% | 0.908 | -66.39% |
| 16 | 33.25% | 2.92% | 0.889 | -53.96% |
| 14 | 35.68% | 8.0% | 0.88 | -53.09% |
| 13 | 34.49% | 17.14% | 0.836 | -55.13% |
| 5 | 32.29% | 22.68% | 0.823 | -63.92% |
| 15 | 30.5% | 7.43% | 0.823 | -49.71% |
| 19 | 29.66% | 9.81% | 0.817 | -59.03% |
| 11 | 29.21% | 12.48% | 0.775 | -56.46% |
| 12 | 31.79% | 2.92% | 0.772 | -55.76% |
| 17 | 29.08% | 16.0% | 0.753 | -69.09% |

## Walk-Forward Annuale

Ogni anno sceglie il lookback migliore sui dati disponibili fino all'anno precedente, poi lo applica all'anno successivo. Confronto con 8w fisso e BTC buy&hold nello stesso anno.

| anno | lb scelto | WF | Static 8w | BTC | WF DD |
| --- | --- | --- | --- | --- | --- |
| 2018 | 22 | -55.74% | -64.96% | -73.05% | -56.1% |
| 2019 | 3 | 5.49% | 213.91% | 96.67% | -52.75% |
| 2020 | 2 | 223.59% | 72.82% | 248.23% | -19.12% |
| 2021 | 2 | -21.23% | 119.45% | 52.21% | -31.84% |
| 2022 | 2 | -60.17% | -35.63% | -61.36% | -60.17% |
| 2023 | 15 | 18.22% | 65.2% | 143.45% | -24.57% |
| 2024 | 15 | 67.2% | 111.67% | 130.84% | -19.92% |
| 2025 | 17 | 1.13% | 13.2% | -16.15% | -27.91% |
| 2026 | 17 | 8.26% | 8.25% | -18.76% | -12.37% |

## Rendimenti Annuali

| anno | APEX | BTC | Equal |
| --- | --- | --- | --- |
| 2014 | -3.74% | -13.31% | -0.88% |
| 2015 | 23.78% | 64.59% | 20.49% |
| 2016 | 87.54% | 122.46% | 54.13% |
| 2017 | 868.34% | 1259.4% | 723.61% |
| 2018 | -64.96% | -73.05% | -69.07% |
| 2019 | 213.91% | 96.67% | 84.09% |
| 2020 | 72.82% | 248.23% | 217.61% |
| 2021 | 119.45% | 52.21% | 51.07% |
| 2022 | -35.63% | -61.36% | -59.71% |
| 2023 | 65.2% | 143.45% | 134.19% |
| 2024 | 111.67% | 130.84% | 127.72% |
| 2025 | 13.2% | -16.15% | -15.38% |
| 2026 | 8.25% | -18.76% | -18.12% |

## Ultimi Segnali

| data | signal | raw | BTC 8w | Oro 8w | SP 8w | cambio |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-03-11 | GOLD | GOLD | -26.45% | 12.88% | -1.87% | no |
| 2026-03-18 | GOLD | GOLD | -14.93% | 3.42% | -0.07% | no |
| 2026-03-25 | GOLD | CASH | -18.07% | -11.18% | -2.45% | no |
| 2026-04-01 | CASH | CASH | -7.88% | -3.17% | -3.31% | si |
| 2026-04-08 | CASH | BTC | 6.36% | -4.15% | -1.55% | no |
| 2026-04-15 | BTC | BTC | 10.42% | -0.14% | 2.25% | si |
| 2026-04-22 | BTC | BTC | 19.46% | -7.74% | 2.98% | no |
| 2026-04-29 | BTC | BTC | 10.77% | -11.20% | 3.42% | no |
| 2026-05-06 | BTC | BTC | 14.72% | -10.94% | 6.49% | no |
| 2026-05-13 | BTC | BTC | 7.02% | -6.19% | 8.77% | no |
| 2026-05-20 | BTC | BTC | 8.91% | -0.95% | 11.76% | no |
| 2026-05-27 | BTC | BTC | 10.48% | -5.45% | 14.12% | no |

## Lettura Tecnica

1. Il lookback 8w resta la base piu pulita e coerente con APEX Rev2, ma non e' il vincitore unico in ogni metrica.
2. Nel confronto 2018 richiesto, `Buffer 2pp 6w` e `Confirm2 6w` battono nettamente l'8w originale; sono candidati veri, non rumore da ignorare.
3. Non li adotterei automaticamente: aggiungono regole, riducono o spostano alcuni drawdown, ma possono essere piu ottimizzati sul periodo 2018-oggi.
4. La versione pure-relative, dove S&P 500 puo battere direttamente BTC, migliora alcune metriche ma cambia l'identita BTC-centrica della strategia. La terrei fuori salvo scelta esplicita.
5. Il lookback 17w e' il migliore sul periodo pieno per CAGR, ma sul confronto 2018 va molto peggio: e' un segnale forte contro l'overfitting.
6. Il drawdown resta enorme: APEX riduce il drawdown rispetto a BTC buy&hold, ma resta una strategia aggressiva.
7. Raccomandazione provvisoria: implementare APEX 8w come versione base verificabile, e affiancare in app una simulazione non-operativa `6w + filtro` per decidere con dati live prima di cambiare regola.

## File Generati

- `output/apex_deep_grid.csv`
- `output/apex_deep_variants.csv`
- `output/apex_deep_claude2018_variants.csv`
- `output/apex_deep_benchmarks.csv`
- `output/apex_deep_subperiods.csv`
- `output/apex_deep_yearly.csv`
- `output/apex_deep_last_signals.csv`
- `output/apex_deep_results.json`
