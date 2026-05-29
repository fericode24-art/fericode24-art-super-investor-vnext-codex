# APEX stress selection - 2026-05-29

Stato: ricerca quantitativa. Nessun deploy.

## Sintesi decisionale

Filtro applicato: massimo 15 swap/anno.

Il miglior candidato grezzo resta `Buffer 5pp 5w` con segnale `venerdi open`: e' primo per CAGR lordo, primo per netto fiscale tra i candidati stressati, ha il drawdown massimo piu basso tra i top 5 e pochi swap/anno.

La seconda lettura e' piu prudente: `Pure Relative 7w` e' la curva piu lineare, ma fa piu swap e perde la tesi BTC-centrica originale. `Confirm2+Buffer2 90d` e' interessante come daily ed e' piu stabile sul lookback, ma non batte il miglior weekly e ha drawdown/ulcer piu pesanti.

Avviso importante: il test di plateau segnala che molti vincitori hanno un picco molto preciso sul lookback. Quindi la scelta finale non deve essere fatta solo sul CAGR. APEX Rev2 8w originale resta un benchmark obbligatorio, ma nei test non e' il miglior candidato.

## Top 5 Per CAGR Con Vincolo Swap

| Segnale | Strategia | CAGR | Out CAGR | Max DD | Sharpe | Calmar | Sw/anno | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| venerdi open | Buffer 5pp 5w | 53.95% | 51.42% | -43.11% | 1.229 | 1.251 | 7.4 | 373.548 |
| martedi close | Buffer 3pp 6w | 53.03% | 65.32% | -61.38% | 1.155 | 0.864 | 7.5 | 355.678 |
| martedi close | Pure Relative 7w | 51.87% | 68.13% | -50.70% | 1.145 | 1.023 | 12.9 | 333.595 |
| daily open | Confirm2+Buffer2 90d | 51.33% | 71.83% | -63.37% | 1.769 | 0.81 | 10.7 | 324.508 |
| lunedi open | Buffer 5pp 8w | 51.17% | 56.33% | -51.47% | 1.156 | 0.994 | 5.6 | 320.989 |

## APEX Rev2 Originale Come Ancora

| Segnale | Strategia | CAGR | Out CAGR | Max DD | Sharpe | Calmar | Sw/anno | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mercoledi open | APEX 8w | 38.33% | 55.32% | -66.39% | 0.908 | 0.577 | 10.8 | 152.339 |
| mercoledi close | APEX 8w | 43.91% | 70.31% | -58.74% | 0.981 | 0.747 | 10.6 | 212.321 |

## Stress Robustezza Dei Candidati

| Segnale | Strategia | CAGR | Max DD | R2 linea | Ulcer | Tempo DD>20 | Tempo DD>40 | Peggior anno | Anni + / - | Sw/anno |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| venerdi open | Buffer 5pp 5w | 53.95% | -43.11% | 0.905 | 18.67% | 28.5% | 5.2% | -40.0% | 7 / 2 | 7.4 |
| martedi close | Buffer 3pp 6w | 53.03% | -61.38% | 0.913 | 24.30% | 32.1% | 13.0% | -59.6% | 7 / 2 | 7.5 |
| martedi close | Pure Relative 7w | 51.87% | -50.70% | 0.948 | 21.27% | 33.3% | 9.1% | -45.7% | 7 / 2 | 12.9 |
| daily open | Confirm2+Buffer2 90d | 51.33% | -63.37% | 0.937 | 25.40% | 36.2% | 13.0% | -53.6% | 7 / 2 | 10.7 |
| lunedi open | Buffer 5pp 8w | 51.17% | -51.47% | 0.916 | 24.57% | 44.9% | 14.1% | -36.5% | 7 / 2 | 5.6 |
| mercoledi open | APEX 8w | 38.33% | -66.39% | 0.901 | 29.59% | 47.2% | 19.1% | -65.1% | 7 / 2 | 10.8 |
| mercoledi close | APEX 8w | 43.91% | -58.74% | 0.923 | 27.20% | 48.1% | 13.9% | -57.2% | 7 / 2 | 10.6 |

## Ranking Robustezza Tra I Top 5

Punteggio piu basso = migliore. Il ranking combina CAGR, drawdown, linearita', ulcer index, tempo sotto -40%, out-of-sample e numero swap.

| Rank | Segnale | Strategia | Score | CAGR | Max DD | R2 linea | Ulcer | Out CAGR | Sw/anno |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | martedi close | Pure Relative 7w | 20 | 51.87% | -50.70% | 0.948 | 21.27% | 68.13% | 12.9 |
| 2 | venerdi open | Buffer 5pp 5w | 21 | 53.95% | -43.11% | 0.905 | 18.67% | 51.42% | 7.4 |
| 3 | martedi close | Buffer 3pp 6w | 25 | 53.03% | -61.38% | 0.913 | 24.30% | 65.32% | 7.5 |
| 4 | daily open | Confirm2+Buffer2 90d | 25 | 51.33% | -63.37% | 0.937 | 25.40% | 71.83% | 10.7 |
| 5 | lunedi open | Buffer 5pp 8w | 29 | 51.17% | -51.47% | 0.916 | 24.57% | 56.33% | 5.6 |

## Stabilita' Parametro E Timing

`Plateau` = media/min dei lookback vicini allo stesso timing. `Timing` = media/min della stessa strategia/lookback su altri momenti di lettura. Se qui il numero crolla, il candidato puo essere overfit.

| Segnale | Strategia | CAGR | Plateau medio | Plateau min | Timing medio | Timing min | Nota |
| --- | --- | --- | --- | --- | --- | --- | --- |
| venerdi open | Buffer 5pp 5w | 53.95% | 40.82% | 32.23% | 40.29% | 30.22% | fragile |
| martedi close | Buffer 3pp 6w | 53.03% | 39.25% | 29.23% | 38.93% | 30.78% | fragile |
| martedi close | Pure Relative 7w | 51.87% | 39.03% | 25.07% | 38.10% | 27.09% | fragile |
| daily open | Confirm2+Buffer2 90d | 51.33% | 44.52% | 42.13% | 45.50% | 39.67% | ok |
| lunedi open | Buffer 5pp 8w | 51.17% | 33.93% | 22.43% | 39.89% | 34.64% | fragile |

## Netto Fiscale Stimato

Modello fiscale semplificato Italia con liquidazione finale, costo swap 0,30%. Serve per confronto, non per dichiarazione fiscale.

| Segnale | Strategia | Netto 10k | CAGR netto | DD netto | Tasse | Swap |
| --- | --- | --- | --- | --- | --- | --- |
| venerdi open | Buffer 5pp 5w | 169.308 | 42.47% | -44.69% | 59.714 | 61 |
| martedi close | Buffer 3pp 6w | 160.665 | 39.63% | -60.79% | 56.126 | 62 |
| martedi close | Pure Relative 7w | 145.502 | 37.99% | -49.76% | 52.967 | 107 |
| daily open | Confirm2+Buffer2 90d | 145.435 | 36.04% | -63.89% | 51.567 | 89 |
| lunedi open | Buffer 5pp 8w | 152.819 | 35.37% | -51.47% | 52.566 | 46 |
| mercoledi open | APEX 8w | 80.908 | 28.56% | -66.13% | 27.500 | 90 |
| mercoledi close | APEX 8w | 103.290 | 32.18% | -59.46% | 35.657 | 88 |

## Sensibilita' Ai Costi

| Strategia | Costo bps | CAGR | Max DD | Finale 10k | Switch |
| --- | --- | --- | --- | --- | --- |
| venerdi open / Buffer 5pp 5w | 10 | 56.24% | -42.19% | 422.967 | 62 |
| venerdi open / Buffer 5pp 5w | 30 | 53.95% | -43.11% | 373.548 | 62 |
| venerdi open / Buffer 5pp 5w | 60 | 50.56% | -44.46% | 309.886 | 62 |
| venerdi open / Buffer 5pp 5w | 100 | 46.14% | -46.33% | 241.339 | 62 |
| martedi close / Buffer 3pp 6w | 10 | 55.35% | -60.75% | 403.541 | 63 |
| martedi close / Buffer 3pp 6w | 30 | 53.03% | -61.38% | 355.678 | 63 |
| martedi close / Buffer 3pp 6w | 60 | 49.61% | -62.36% | 294.174 | 63 |
| martedi close / Buffer 3pp 6w | 100 | 45.15% | -63.70% | 228.181 | 63 |
| martedi close / Pure Relative 7w | 10 | 55.83% | -49.89% | 414.204 | 108 |
| martedi close / Pure Relative 7w | 30 | 51.87% | -50.70% | 333.595 | 108 |
| martedi close / Pure Relative 7w | 60 | 46.09% | -52.02% | 240.919 | 108 |
| martedi close / Pure Relative 7w | 100 | 38.70% | -53.73% | 155.863 | 108 |
| daily open / Confirm2+Buffer2 90d | 10 | 54.61% | -62.18% | 388.647 | 90 |
| daily open / Confirm2+Buffer2 90d | 30 | 51.33% | -63.37% | 324.508 | 90 |
| daily open / Confirm2+Buffer2 90d | 60 | 46.52% | -65.09% | 247.421 | 90 |
| daily open / Confirm2+Buffer2 90d | 100 | 40.32% | -67.28% | 172.119 | 90 |
| lunedi open / Buffer 5pp 8w | 10 | 52.88% | -51.08% | 352.691 | 47 |
| lunedi open / Buffer 5pp 8w | 30 | 51.17% | -51.47% | 320.989 | 47 |
| lunedi open / Buffer 5pp 8w | 60 | 48.64% | -52.06% | 278.597 | 47 |
| lunedi open / Buffer 5pp 8w | 100 | 45.32% | -52.82% | 230.500 | 47 |

## Plateau Lookback Vicino Ai Vincitori

Questa tabella serve a capire se il risultato dipende da un singolo parametro fortunato.

| Base | Lookback | CAGR | Max DD | Sw/anno | Finale 10k |
| --- | --- | --- | --- | --- | --- |
| venerdi open / Buffer 5pp 5w | 4 | 40.43% | -48.05% | 8.5 | 172.772 |
| venerdi open / Buffer 5pp 5w | 5 | 53.95% | -43.11% | 7.4 | 373.548 |
| venerdi open / Buffer 5pp 5w | 6 | 32.23% | -56.23% | 7.4 | 104.295 |
| venerdi open / Buffer 5pp 5w | 7 | 36.68% | -56.30% | 6.7 | 137.606 |
| martedi close / Buffer 3pp 6w | 4 | 38.18% | -58.15% | 11.4 | 150.996 |
| martedi close / Buffer 3pp 6w | 5 | 38.44% | -62.32% | 9.2 | 153.385 |
| martedi close / Buffer 3pp 6w | 6 | 53.03% | -61.38% | 7.5 | 355.678 |
| martedi close / Buffer 3pp 6w | 7 | 29.23% | -63.57% | 7.9 | 86.038 |
| martedi close / Buffer 3pp 6w | 8 | 37.37% | -67.34% | 7.1 | 143.725 |
| martedi close / Pure Relative 7w | 6 | 38.24% | -59.99% | 14.5 | 151.561 |
| martedi close / Pure Relative 7w | 7 | 51.87% | -50.70% | 12.9 | 333.595 |
| martedi close / Pure Relative 7w | 8 | 40.94% | -55.55% | 11.7 | 178.258 |
| martedi close / Pure Relative 7w | 9 | 25.07% | -65.14% | 11.3 | 65.400 |
| daily open / Confirm2+Buffer2 90d | 80 | 42.19% | -69.01% | 13.5 | 192.329 |
| daily open / Confirm2+Buffer2 90d | 85 | 42.38% | -67.16% | 12.4 | 194.476 |
| daily open / Confirm2+Buffer2 90d | 90 | 51.33% | -63.37% | 10.7 | 324.508 |
| daily open / Confirm2+Buffer2 90d | 95 | 44.56% | -53.12% | 10.4 | 220.968 |
| daily open / Confirm2+Buffer2 90d | 100 | 42.13% | -54.78% | 11.1 | 191.624 |
| lunedi open / Buffer 5pp 8w | 6 | 33.03% | -58.99% | 7.9 | 109.798 |
| lunedi open / Buffer 5pp 8w | 7 | 32.25% | -69.73% | 6.8 | 104.510 |
| lunedi open / Buffer 5pp 8w | 8 | 51.17% | -51.47% | 5.6 | 320.989 |
| lunedi open / Buffer 5pp 8w | 9 | 22.43% | -73.44% | 6.3 | 54.656 |
| lunedi open / Buffer 5pp 8w | 10 | 30.76% | -62.32% | 6.0 | 95.004 |

## Decisione Provvisoria

1. Miglior rendimento/rischio operativo: `Buffer 5pp 5w`, segnale `venerdi open`, ma con flag di overfit sul lookback.
2. Miglior robustezza tra i top 5: `Pure Relative 7w`, segnale `martedi close`, soprattutto per linearita' curva.
3. Miglior stabilita' daily: `Confirm2+Buffer2 90d daily open`, ma paga drawdown piu profondo e complessita' maggiore.
4. Candidato operativo piu calmo: `Buffer 5pp 8w`, segnale `lunedi open`, ma il plateau e' fragile.
5. APEX Rev2 originale 8w: da tenere come benchmark obbligatorio, non come scelta finale automatica.

Conclusione prudente: non promuoverei ancora nessuna strategia senza walk-forward/rolling validation finale. Se devo scegliere un candidato da portare al prossimo step, porto `Buffer 5pp 5w venerdi open`; se devo scegliere la piu lineare/robusta, porto `Pure Relative 7w martedi close`.

## File Collegati

- Prompt pronto per confronto esterno: `docs\APEX_STRATEGY_SELECTION_PROMPT_2026-05-29.md`.
- Dati macchina: `output\apex_stress_selection_results.json`.
