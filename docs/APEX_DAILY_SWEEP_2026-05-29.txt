# APEX daily sweep - 2026-05-29

Stato: ricerca quantitativa, nessun deploy.

## Metodo

- Periodo: 2018-01-01 -> 2026-05-29.
- Frequenza: daily, solo giorni lunedi-venerdi.
- Prezzi testati: open e close.
- Lookback: 10 -> 100 sedute, passo 5.
- Varianti: APEX, Buffer 1/2/3/5pp, Confirm2, Confirm2+Buffer2, Pure Relative.
- Griglia principale: mark-to-market con costo cambio 30 bps.
- Tabella fiscale: solo candidati migliori, con liquidazione finale.
- Nota: daily e' molto piu' esposto a rumore, quindi la classifica assoluta va trattata con piu' sospetto rispetto al weekly.

## Vincitori Daily

| frequenza | prezzo | strategia | famiglia | lookback | CAGR | Out CAGR | Max DD | Sharpe | Out Sharpe | Switch | Sw/anno | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| daily | open | Confirm2+Buffer2 90d | confirm_buffer | 90 | 51.33% | 71.83% | -63.37% | 1.769 | 2.934 | 90 | 10.7 | 324508.0 |
| daily | close | Buffer 5pp 65d | buffer | 65 | 50.68% | 61.87% | -61.04% | 1.725 | 2.522 | 89 | 10.6 | 313044.0 |

## Top Daily Mark-to-Market

| frequenza | prezzo | strategia | famiglia | lookback | CAGR | Out CAGR | Max DD | Sharpe | Out Sharpe | Switch | Sw/anno | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| daily | open | Confirm2+Buffer2 90d | confirm_buffer | 90 | 51.33% | 71.83% | -63.37% | 1.769 | 2.934 | 90 | 10.7 | 324508.0 |
| daily | close | Buffer 5pp 65d | buffer | 65 | 50.68% | 61.87% | -61.04% | 1.725 | 2.522 | 89 | 10.6 | 313044.0 |
| daily | close | Buffer 5pp 60d | buffer | 60 | 49.3% | 54.83% | -65.44% | 1.685 | 2.277 | 91 | 10.8 | 289830.0 |
| daily | open | Buffer 5pp 60d | buffer | 60 | 48.12% | 60.54% | -63.64% | 1.711 | 2.613 | 88 | 10.5 | 271028.0 |
| daily | open | Buffer 2pp 85d | buffer | 85 | 47.76% | 50.12% | -62.83% | 1.681 | 2.096 | 112 | 13.3 | 265565.0 |
| daily | close | Buffer 5pp 80d | buffer | 80 | 46.76% | 62.53% | -63.15% | 1.579 | 2.522 | 74 | 8.8 | 250873.0 |
| daily | open | Buffer 5pp 80d | buffer | 80 | 46.18% | 65.46% | -65.29% | 1.626 | 2.761 | 74 | 8.8 | 242676.0 |
| daily | open | Confirm2 95d | confirm | 95 | 46.13% | 57.43% | -56.03% | 1.591 | 2.415 | 158 | 18.8 | 242006.0 |
| daily | open | Buffer 5pp 65d | buffer | 65 | 45.8% | 56.56% | -61.44% | 1.651 | 2.481 | 93 | 11.1 | 237481.0 |
| daily | open | Buffer 3pp 85d | buffer | 85 | 45.64% | 53.31% | -63.38% | 1.606 | 2.237 | 94 | 11.2 | 235271.0 |
| daily | open | Buffer 5pp 95d | buffer | 95 | 44.77% | 61.86% | -55.01% | 1.56 | 2.571 | 68 | 8.1 | 223648.0 |
| daily | close | Confirm2+Buffer2 95d | confirm_buffer | 95 | 44.67% | 57.47% | -57.63% | 1.484 | 2.239 | 86 | 10.2 | 222384.0 |
| daily | open | Confirm2+Buffer2 95d | confirm_buffer | 95 | 44.56% | 52.95% | -53.12% | 1.559 | 2.243 | 87 | 10.4 | 220968.0 |
| daily | open | Buffer 1pp 100d | buffer | 100 | 44.55% | 61.31% | -57.31% | 1.54 | 2.539 | 125 | 14.9 | 220868.0 |
| daily | open | Confirm2 100d | confirm | 100 | 44.54% | 56.14% | -57.66% | 1.523 | 2.295 | 166 | 19.8 | 220695.0 |

## Top Daily Out-of-Sample

| frequenza | prezzo | strategia | famiglia | lookback | CAGR | Out CAGR | Max DD | Sharpe | Out Sharpe | Switch | Sw/anno | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| daily | open | Buffer 5pp 75d | buffer | 75 | 42.09% | 71.48% | -71.31% | 1.486 | 3.089 | 77 | 9.2 | 191155.0 |
| daily | open | Confirm2+Buffer2 75d | confirm_buffer | 75 | 44.45% | 70.73% | -66.72% | 1.562 | 3.019 | 110 | 13.1 | 219620.0 |
| daily | open | Buffer 1pp 70d | buffer | 70 | 39.96% | 69.84% | -71.82% | 1.413 | 2.993 | 178 | 21.2 | 168460.0 |
| daily | open | Confirm2+Buffer2 90d | confirm_buffer | 90 | 51.33% | 71.83% | -63.37% | 1.769 | 2.934 | 90 | 10.7 | 324508.0 |
| daily | open | Buffer 5pp 90d | buffer | 90 | 39.93% | 70.5% | -64.41% | 1.375 | 2.903 | 76 | 9.0 | 168114.0 |
| daily | open | Confirm2 80d | confirm | 80 | 42.04% | 67.88% | -69.78% | 1.462 | 2.871 | 183 | 21.8 | 190691.0 |
| daily | open | Buffer 2pp 60d | buffer | 60 | 43.68% | 65.74% | -64.04% | 1.549 | 2.855 | 160 | 19.0 | 209972.0 |
| daily | close | Buffer 3pp 75d | buffer | 75 | 38.0% | 69.37% | -67.59% | 1.281 | 2.813 | 100 | 11.9 | 149581.0 |
| daily | open | Buffer 3pp 70d | buffer | 70 | 39.65% | 64.58% | -69.37% | 1.408 | 2.793 | 117 | 13.9 | 165334.0 |
| daily | open | Confirm2+Buffer2 80d | confirm_buffer | 80 | 42.19% | 65.28% | -69.01% | 1.485 | 2.779 | 113 | 13.5 | 192329.0 |
| daily | close | Buffer 2pp 75d | buffer | 75 | 34.63% | 68.35% | -68.22% | 1.16 | 2.773 | 126 | 15.0 | 121571.0 |
| daily | open | Buffer 5pp 80d | buffer | 80 | 46.18% | 65.46% | -65.29% | 1.626 | 2.761 | 74 | 8.8 | 242676.0 |
| daily | open | Buffer 2pp 70d | buffer | 70 | 40.02% | 63.6% | -69.23% | 1.42 | 2.748 | 139 | 16.5 | 169024.0 |
| daily | open | Buffer 1pp 80d | buffer | 80 | 41.52% | 64.74% | -63.55% | 1.454 | 2.741 | 164 | 19.5 | 184799.0 |
| daily | close | Buffer 1pp 70d | buffer | 70 | 33.58% | 67.26% | -71.88% | 1.121 | 2.724 | 190 | 22.6 | 113825.0 |

## Vista Fiscale Daily

| prezzo | strategia | netto 10k | CAGR netto | Max DD | Sharpe | Switch | Sw/anno | tasse |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| open | Confirm2+Buffer2 90d | 145435.0 | 36.04% | -63.89% | 1.219 | 89 | 10.6 | 51567.0 |
| close | Buffer 5pp 65d | 144788.0 | 37.28% | -61.34% | 1.242 | 88 | 10.5 | 51565.0 |
| close | Buffer 5pp 60d | 133455.0 | 35.95% | -65.65% | 1.205 | 90 | 10.7 | 50991.0 |
| open | Buffer 5pp 60d | 128670.0 | 34.07% | -63.85% | 1.19 | 87 | 10.4 | 45746.0 |
| close | Buffer 5pp 80d | 119840.0 | 34.22% | -63.7% | 1.134 | 73 | 8.7 | 41532.0 |
| open | Buffer 2pp 85d | 119835.0 | 32.94% | -63.32% | 1.138 | 111 | 13.2 | 47974.0 |
| open | Buffer 5pp 80d | 119763.0 | 32.93% | -65.98% | 1.138 | 73 | 8.7 | 41222.0 |
| open | Buffer 5pp 65d | 116699.0 | 32.52% | -61.85% | 1.152 | 92 | 11.0 | 41377.0 |
| open | Buffer 3pp 85d | 112176.0 | 31.9% | -63.86% | 1.105 | 93 | 11.1 | 39512.0 |
| open | Confirm2 95d | 108135.0 | 31.33% | -56.81% | 1.064 | 157 | 18.7 | 39852.0 |
| open | Confirm2+Buffer2 75d | 106214.0 | 31.05% | -67.15% | 1.073 | 109 | 13.0 | 38731.0 |
| open | Buffer 2pp 60d | 99586.0 | 30.05% | -64.84% | 1.048 | 159 | 18.9 | 37568.0 |
| open | Buffer 5pp 75d | 97664.0 | 29.74% | -71.78% | 1.033 | 76 | 9.0 | 32810.0 |
| open | Buffer 5pp 55d | 95301.0 | 29.37% | -59.87% | 1.034 | 83 | 9.9 | 36420.0 |
| open | Buffer 1pp 85d | 92449.0 | 28.9% | -67.63% | 0.998 | 145 | 17.3 | 37153.0 |

## Confronto Con Weekly

Ancora mark-to-market, costo switch incluso.

| frequenza | timing | strategia | CAGR | Max DD | Sharpe | Switch | Sw/anno | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| weekly | mercoledi close | APEX 8w | 43.91% | -58.74% | 0.981 | 89 | 10.6 | 212321.0 |
| weekly | mercoledi open | Buffer 2pp 6w | 50.22% | -60.81% | 1.115 | 74 | 8.8 | 304400.0 |
| weekly | martedi close | Buffer 3pp 6w | 53.03% | -61.38% | 1.155 | 63 | 7.5 | 355678.0 |
| weekly | venerdi open | Buffer 5pp 5w | 53.95% | -43.11% | 1.229 | 62 | 7.4 | 373548.0 |

## Lettura Tecnica

1. Daily puo' trovare vincitori molto forti, ma aumenta il rischio di data mining.
2. Gli swap non crescono in modo lineare solo perche' controlli ogni giorno: i buffer frenano molto. Senza buffer, le versioni pure o APEX corte possono superare facilmente 20-30 cambi/anno.
3. Se una daily vince con lookback corto e tanti switch, va considerata fragile finche' non passa test piu severi.
4. Per una strategia reale su Fineco, weekly resta piu pulita operativamente. Daily ha senso solo se il vantaggio netto resta forte dopo tasse, spread, ritardi e stress test.

## File Generati

- `output/apex_daily_sweep_grid.csv`
- `output/apex_daily_sweep_tax_top.csv`
- `output/apex_daily_sweep_results.json`
