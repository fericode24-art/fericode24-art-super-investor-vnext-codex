# APEX timing sweep - 2026-05-29

Stato: ricerca quantitativa, nessun deploy.

## Metodo

- Periodo: 2018-01-01 -> 2026-05-29.
- Fonte: Yahoo Finance proxy EUR gia' usati per APEX.
- Timing testati: lunedi-venerdi, open e close.
- Strategie testate: APEX, Buffer 1/2/3/5pp, Confirm2, Confirm2+Buffer2, Pure Relative.
- Lookback testati: 4 -> 20 settimane.
- Griglia principale: mark-to-market con costo cambio 30 bps, non fiscalmente liquidata.
- Tabella fiscale: solo sui migliori candidati, con modello fiscale Italia semplificato e liquidazione finale.
- Nota: `Confirm2+Buffer2` qui usa la logica corretta. Nei report precedenti era accidentalmente uguale a Confirm2 per un ordine sbagliato nel codice.

## Vincitori Per Timing

| timing | strategia | famiglia | lookback | CAGR | Out CAGR | Max DD | Sharpe | Out Sharpe | Calmar | Switch | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lunedi open | Buffer 5pp 8w | buffer | 8 | 51.17% | 56.33% | -51.47% | 1.156 | 1.418 | 0.994 | 47 | 320989.0 |
| lunedi close | Buffer 5pp 8w | buffer | 8 | 41.5% | 69.42% | -67.93% | 0.961 | 1.507 | 0.611 | 53 | 184334.0 |
| martedi open | Buffer 5pp 5w | buffer | 5 | 49.63% | 65.08% | -53.63% | 1.113 | 1.478 | 0.925 | 67 | 294490.0 |
| martedi close | Buffer 3pp 6w | buffer | 6 | 53.03% | 65.32% | -61.38% | 1.155 | 1.557 | 0.864 | 63 | 355678.0 |
| mercoledi open | Buffer 2pp 6w | buffer | 6 | 50.22% | 66.76% | -60.81% | 1.115 | 1.58 | 0.826 | 74 | 304400.0 |
| mercoledi close | Confirm2 7w | confirm | 7 | 48.51% | 75.62% | -61.0% | 1.027 | 1.747 | 0.795 | 55 | 276493.0 |
| giovedi open | Pure Relative 5w | pure | 5 | 49.35% | 69.24% | -52.47% | 1.107 | 1.756 | 0.941 | 123 | 289971.0 |
| giovedi close | Buffer 5pp 5w | buffer | 5 | 47.47% | 52.58% | -40.04% | 1.118 | 1.404 | 1.186 | 64 | 260742.0 |
| venerdi open | Buffer 5pp 5w | buffer | 5 | 53.95% | 51.42% | -43.11% | 1.229 | 1.397 | 1.251 | 62 | 373548.0 |
| venerdi close | Confirm2 4w | confirm | 4 | 40.48% | 55.35% | -59.51% | 0.952 | 1.4 | 0.68 | 73 | 173264.0 |

## Top Globale Mark-to-Market

Ordinato per capitale finale, costo switch incluso, senza liquidazione fiscale finale.

| timing | strategia | famiglia | lookback | CAGR | Out CAGR | Max DD | Sharpe | Out Sharpe | Calmar | Switch | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| venerdi open | Buffer 5pp 5w | buffer | 5 | 53.95% | 51.42% | -43.11% | 1.229 | 1.397 | 1.251 | 62 | 373548.0 |
| martedi close | Buffer 3pp 6w | buffer | 6 | 53.03% | 65.32% | -61.38% | 1.155 | 1.557 | 0.864 | 63 | 355678.0 |
| martedi close | Pure Relative 7w | pure | 7 | 51.87% | 68.13% | -50.7% | 1.145 | 1.547 | 1.023 | 108 | 333595.0 |
| lunedi open | Buffer 5pp 8w | buffer | 8 | 51.17% | 56.33% | -51.47% | 1.156 | 1.418 | 0.994 | 47 | 320989.0 |
| lunedi open | APEX 8w | apex | 8 | 50.65% | 56.94% | -64.12% | 1.119 | 1.401 | 0.79 | 90 | 311856.0 |
| venerdi open | Pure Relative 5w | pure | 5 | 50.5% | 58.61% | -48.3% | 1.168 | 1.493 | 1.045 | 124 | 308915.0 |
| mercoledi open | Buffer 2pp 6w | buffer | 6 | 50.22% | 66.76% | -60.81% | 1.115 | 1.58 | 0.826 | 74 | 304400.0 |
| mercoledi open | Buffer 3pp 6w | buffer | 6 | 50.11% | 70.35% | -62.16% | 1.113 | 1.636 | 0.806 | 65 | 302618.0 |
| lunedi open | Buffer 2pp 8w | buffer | 8 | 49.69% | 64.11% | -65.14% | 1.117 | 1.527 | 0.763 | 64 | 295607.0 |
| martedi open | Buffer 5pp 5w | buffer | 5 | 49.63% | 65.08% | -53.63% | 1.113 | 1.478 | 0.925 | 67 | 294490.0 |
| lunedi open | Buffer 5pp 11w | buffer | 11 | 49.55% | 55.65% | -51.61% | 1.12 | 1.39 | 0.96 | 44 | 293209.0 |
| giovedi open | Pure Relative 5w | pure | 5 | 49.35% | 69.24% | -52.47% | 1.107 | 1.756 | 0.941 | 123 | 289971.0 |
| mercoledi open | Buffer 5pp 6w | buffer | 6 | 49.32% | 62.77% | -62.0% | 1.101 | 1.512 | 0.795 | 61 | 289444.0 |
| venerdi open | Buffer 2pp 5w | buffer | 5 | 49.3% | 64.33% | -48.68% | 1.143 | 1.594 | 1.013 | 88 | 288887.0 |
| mercoledi open | Pure Relative 7w | pure | 7 | 49.14% | 64.0% | -51.11% | 1.116 | 1.535 | 0.961 | 105 | 286542.0 |

## Top Per Out-of-Sample

Ordinato per Sharpe 2023-2026, poi CAGR 2023-2026.

| timing | strategia | famiglia | lookback | CAGR | Out CAGR | Max DD | Sharpe | Out Sharpe | Calmar | Switch | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| giovedi close | Pure Relative 6w | pure | 6 | 36.2% | 77.88% | -60.99% | 0.903 | 1.895 | 0.594 | 125 | 133755.0 |
| giovedi open | APEX 5w | apex | 5 | 45.87% | 81.99% | -55.74% | 1.037 | 1.89 | 0.823 | 128 | 237847.0 |
| venerdi open | Pure Relative 6w | pure | 6 | 36.37% | 76.21% | -61.15% | 0.906 | 1.829 | 0.595 | 128 | 135031.0 |
| giovedi close | APEX 6w | apex | 6 | 33.11% | 73.23% | -62.81% | 0.85 | 1.799 | 0.527 | 120 | 110308.0 |
| venerdi open | APEX 6w | apex | 6 | 35.02% | 75.2% | -60.49% | 0.88 | 1.798 | 0.579 | 119 | 124265.0 |
| giovedi open | Buffer 1pp 5w | buffer | 5 | 46.03% | 72.11% | -52.86% | 1.052 | 1.795 | 0.871 | 96 | 240132.0 |
| venerdi open | Buffer 1pp 6w | buffer | 6 | 45.6% | 74.6% | -59.02% | 1.067 | 1.788 | 0.773 | 93 | 234013.0 |
| giovedi open | Pure Relative 5w | pure | 5 | 49.35% | 69.24% | -52.47% | 1.107 | 1.756 | 0.941 | 123 | 289971.0 |
| mercoledi close | Buffer 1pp 5w | buffer | 5 | 41.7% | 70.95% | -58.38% | 0.977 | 1.747 | 0.714 | 106 | 186479.0 |
| mercoledi close | Confirm2 7w | confirm | 7 | 48.51% | 75.62% | -61.0% | 1.027 | 1.747 | 0.795 | 55 | 276493.0 |
| martedi open | Confirm2 6w | confirm | 6 | 40.93% | 87.61% | -62.61% | 0.928 | 1.737 | 0.654 | 54 | 178137.0 |
| giovedi open | Buffer 5pp 5w | buffer | 5 | 42.46% | 69.1% | -59.16% | 0.994 | 1.729 | 0.718 | 65 | 195039.0 |
| mercoledi close | Buffer 3pp 5w | buffer | 5 | 44.21% | 67.95% | -56.34% | 1.019 | 1.727 | 0.785 | 75 | 216047.0 |
| giovedi open | APEX 8w | apex | 8 | 45.92% | 75.74% | -65.48% | 1.013 | 1.72 | 0.701 | 80 | 238633.0 |
| venerdi open | Buffer 1pp 8w | buffer | 8 | 38.08% | 76.18% | -65.96% | 0.922 | 1.714 | 0.577 | 70 | 149911.0 |

## Focus Lunedi Close

Questa e' la domanda specifica: cosa succede se il segnale viene letto lunedi sera?

| timing | strategia | famiglia | lookback | CAGR | Out CAGR | Max DD | Sharpe | Out Sharpe | Calmar | Switch | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lunedi close | Buffer 5pp 8w | buffer | 8 | 41.5% | 69.42% | -67.93% | 0.961 | 1.507 | 0.611 | 53 | 184334.0 |
| lunedi close | Buffer 5pp 4w | buffer | 4 | 40.94% | 51.77% | -55.35% | 0.975 | 1.282 | 0.74 | 78 | 178198.0 |
| lunedi close | Buffer 3pp 8w | buffer | 8 | 40.31% | 64.61% | -66.66% | 0.943 | 1.436 | 0.605 | 60 | 171647.0 |
| lunedi close | Buffer 5pp 5w | buffer | 5 | 40.23% | 56.67% | -66.04% | 0.959 | 1.345 | 0.609 | 66 | 170842.0 |
| lunedi close | Buffer 3pp 4w | buffer | 4 | 39.98% | 55.31% | -59.38% | 0.949 | 1.338 | 0.673 | 95 | 168276.0 |
| lunedi close | Confirm2 10w | confirm | 10 | 39.31% | 50.11% | -55.66% | 0.891 | 1.212 | 0.706 | 43 | 161634.0 |
| lunedi close | Confirm2+Buffer2 10w | confirm_buffer | 10 | 39.16% | 48.52% | -55.66% | 0.889 | 1.183 | 0.704 | 39 | 160255.0 |
| lunedi close | Pure Relative 15w | pure | 15 | 38.96% | 42.27% | -55.66% | 0.916 | 1.17 | 0.7 | 70 | 158257.0 |
| lunedi close | Confirm2 7w | confirm | 7 | 38.58% | 65.21% | -67.21% | 0.873 | 1.409 | 0.574 | 46 | 154738.0 |
| lunedi close | Confirm2+Buffer2 7w | confirm_buffer | 7 | 38.5% | 65.21% | -67.38% | 0.872 | 1.409 | 0.571 | 45 | 153979.0 |
| lunedi close | Buffer 5pp 14w | buffer | 14 | 38.11% | 44.29% | -55.66% | 0.902 | 1.218 | 0.685 | 34 | 150376.0 |
| lunedi close | Buffer 1pp 13w | buffer | 13 | 37.73% | 53.78% | -55.79% | 0.909 | 1.275 | 0.676 | 54 | 146920.0 |

## Confronto Mercoledi

Mercoledi close, cioe' la lettura piu vicina al motore Claude.

| timing | strategia | famiglia | lookback | CAGR | Out CAGR | Max DD | Sharpe | Out Sharpe | Calmar | Switch | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mercoledi close | Confirm2 7w | confirm | 7 | 48.51% | 75.62% | -61.0% | 1.027 | 1.747 | 0.795 | 55 | 276493.0 |
| mercoledi close | Buffer 5pp 4w | buffer | 4 | 46.43% | 45.94% | -46.48% | 1.06 | 1.231 | 0.999 | 72 | 245596.0 |
| mercoledi close | Confirm2+Buffer2 7w | confirm_buffer | 7 | 44.85% | 66.98% | -62.82% | 0.985 | 1.6 | 0.714 | 53 | 224240.0 |
| mercoledi close | Buffer 3pp 5w | buffer | 5 | 44.21% | 67.95% | -56.34% | 1.019 | 1.727 | 0.785 | 75 | 216047.0 |
| mercoledi close | APEX 8w | apex | 8 | 43.91% | 70.31% | -58.74% | 0.981 | 1.621 | 0.747 | 89 | 212321.0 |
| mercoledi close | Pure Relative 8w | pure | 8 | 43.71% | 66.1% | -61.23% | 0.987 | 1.604 | 0.714 | 91 | 209831.0 |
| mercoledi close | Pure Relative 5w | pure | 5 | 43.2% | 65.03% | -56.0% | 1.001 | 1.613 | 0.771 | 130 | 203677.0 |
| mercoledi close | Buffer 1pp 5w | buffer | 5 | 41.7% | 70.95% | -58.38% | 0.977 | 1.747 | 0.714 | 106 | 186479.0 |

Mercoledi open, cioe' la lettura piu vicina all'idea di segnale mattina.

| timing | strategia | famiglia | lookback | CAGR | Out CAGR | Max DD | Sharpe | Out Sharpe | Calmar | Switch | Finale 10k |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mercoledi open | Buffer 2pp 6w | buffer | 6 | 50.22% | 66.76% | -60.81% | 1.115 | 1.58 | 0.826 | 74 | 304400.0 |
| mercoledi open | Buffer 3pp 6w | buffer | 6 | 50.11% | 70.35% | -62.16% | 1.113 | 1.636 | 0.806 | 65 | 302618.0 |
| mercoledi open | Buffer 5pp 6w | buffer | 6 | 49.32% | 62.77% | -62.0% | 1.101 | 1.512 | 0.795 | 61 | 289444.0 |
| mercoledi open | Pure Relative 7w | pure | 7 | 49.14% | 64.0% | -51.11% | 1.116 | 1.535 | 0.961 | 105 | 286542.0 |
| mercoledi open | Confirm2+Buffer2 6w | confirm_buffer | 6 | 47.37% | 46.86% | -53.3% | 1.066 | 1.205 | 0.889 | 51 | 259219.0 |
| mercoledi open | Confirm2 6w | confirm | 6 | 47.33% | 53.86% | -53.0% | 1.058 | 1.306 | 0.893 | 56 | 258662.0 |
| mercoledi open | Pure Relative 8w | pure | 8 | 46.2% | 49.93% | -51.7% | 1.042 | 1.276 | 0.894 | 92 | 242466.0 |
| mercoledi open | Buffer 3pp 5w | buffer | 5 | 44.91% | 72.07% | -62.32% | 1.025 | 1.652 | 0.721 | 73 | 225115.0 |

## Vista Fiscale Sui Migliori

Questa tabella liquida fiscalmente la posizione finale. Serve solo per i candidati migliori emersi dallo sweep.

| timing | strategia | netto 10k | CAGR netto | DD netto | Sharpe netto | switch | tasse |
| --- | --- | --- | --- | --- | --- | --- | --- |
| venerdi open | Buffer 5pp 5w | 169308.0 | 42.47% | -44.69% | 1.034 | 61 | 59714.0 |
| martedi close | Buffer 3pp 6w | 160665.0 | 39.63% | -60.79% | 0.945 | 62 | 56126.0 |
| lunedi open | Buffer 5pp 8w | 152819.0 | 35.37% | -51.47% | 0.899 | 46 | 52566.0 |
| martedi close | Pure Relative 7w | 145502.0 | 37.99% | -49.76% | 0.922 | 107 | 52967.0 |
| lunedi open | Buffer 5pp 11w | 145336.0 | 34.56% | -53.36% | 0.877 | 43 | 50371.0 |
| mercoledi open | Buffer 2pp 6w | 142611.0 | 37.54% | -60.57% | 0.913 | 73 | 49773.0 |
| mercoledi open | Buffer 3pp 6w | 142260.0 | 37.5% | -61.74% | 0.912 | 64 | 49167.0 |
| lunedi open | APEX 8w | 142102.0 | 34.2% | -64.37% | 0.863 | 89 | 50599.0 |
| lunedi open | Buffer 2pp 8w | 140066.0 | 33.97% | -65.39% | 0.866 | 63 | 48248.0 |
| martedi open | Buffer 5pp 5w | 139408.0 | 35.17% | -54.06% | 0.877 | 66 | 48095.0 |
| venerdi open | Pure Relative 5w | 137874.0 | 39.02% | -44.16% | 0.972 | 123 | 52208.0 |
| lunedi open | APEX 11w | 130663.0 | 32.87% | -54.75% | 0.845 | 83 | 46798.0 |
| giovedi open | Pure Relative 5w | 129154.0 | 35.93% | -59.01% | 0.888 | 122 | 52583.0 |
| mercoledi open | Confirm2+Buffer2 6w | 128094.0 | 35.8% | -52.78% | 0.879 | 50 | 43921.0 |
| mercoledi close | Buffer 5pp 4w | 117135.0 | 34.17% | -46.73% | 0.855 | 71 | 47921.0 |
| giovedi open | Buffer 1pp 5w | 114398.0 | 33.98% | -60.09% | 0.854 | 95 | 43623.0 |
| venerdi open | Buffer 1pp 6w | 113955.0 | 35.9% | -58.01% | 0.905 | 92 | 39811.0 |
| giovedi open | APEX 5w | 110938.0 | 33.49% | -59.41% | 0.838 | 127 | 42909.0 |
| mercoledi close | APEX 8w | 103290.0 | 32.18% | -59.46% | 0.8 | 88 | 35657.0 |
| lunedi close | Buffer 5pp 8w | 96985.0 | 30.97% | -68.14% | 0.791 | 52 | 31965.0 |

## Lettura Tecnica

1. La tua intuizione e' corretta: cambiando timing, puo emergere una terza combinazione.
2. Il lunedi close non va escluso: va confrontato con mercoledi close e mercoledi open per robustezza, non solo per capitale finale.
3. Se un timing vince solo con un lookback molto specifico e perde out-of-sample, va considerato overfitting.
4. Per scegliere la versione operativa finale servono due colonne in app: `valore portafoglio` e `netto se liquidato`.

## Conclusione Operativa Provvisoria

APEX 8w non e' il campione assoluto: e' forte quando il perimetro e' stretto, soprattutto vicino al mercoledi close e alla logica originale.

Quando si allarga il test a timing diversi e filtri diversi, emergono candidati migliori. Pero' i migliori assoluti vanno trattati con sospetto, perche' potrebbero essere ottimizzati sul passato.

Shortlist sensata da approfondire:

| Ruolo | Timing | Strategia | Perche' resta candidata |
| --- | --- | --- | --- |
| Base conservativa | mercoledi close | APEX 8w | Strategia originale, semplice, coerente con la tesi BTC-centrica |
| Challenger mattina | mercoledi open | Buffer 2pp 6w / Buffer 3pp 6w | Forte nella logica di segnale mattutino, ma piu' nuova da validare |
| Challenger lunedi | lunedi close | Buffer 5pp 8w | Risponde alla domanda sul lunedi sera, ma non domina lo sweep globale |
| Challenger globale | martedi close | Buffer 3pp 6w | Molto forte su finale e out-of-sample |
| Candidato aggressivo | venerdi open | Buffer 5pp 5w | Vince molte metriche, ma va controllato bene per rischio overfitting e praticabilita' operativa |

La decisione migliore non e' ancora sostituire APEX 8w. La decisione migliore e' creare un confronto finale a 5 candidati, con gli stessi dati, TER aggiornati, tasse, liquidazione finale e regole operative realistiche.

## File Generati

- `output/apex_timing_sweep_grid.csv`
- `output/apex_timing_sweep_tax_top.csv`
- `output/apex_timing_sweep_results.json`
