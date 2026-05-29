# APEX tax backtest 1 BTC - 2026-05-28

Stato: simulazione fiscale, nessun deploy.

## Ipotesi

- Periodo: 2018-01-03 -> 2026-05-27.
- Capitale iniziale: valore EUR di 1 BTC al primo mercoledi utile = 12.418 EUR.
- Valore finale lordo di 1 BTC al 2026-05-27: 65.150 EUR.
- Regime simulato: amministrato Italia.
- Aliquota: 26%.
- BTC ETP e Oro ETC: redditi diversi, quindi plus compensabili con zainetto disponibile.
- SP500 ETF UCITS e XEON ETF UCITS: plus come redditi di capitale, tassate senza usare zainetto; minus aggiunte allo zainetto.
- Zainetto: scadenza modellata al 31 dicembre del quarto anno successivo alla minus.
- Costi: 30 bps su ingresso iniziale e ogni cambio posizione, come nel backtest precedente.
- Valore finale: posizione finale liquidata fiscalmente. Non e' consulenza fiscale.

## Classifica Netta

| rank | strategia | netto EUR | BTC eq netto | CAGR netto | Max DD | swap | vendite fiscali | tasse pagate | zainetto creato | zainetto usato | zainetto finale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Buffer 2pp 6w | 177.090 | 2.718 | 37.54% | -60.57% | 73 | 74 | 61.806 | 61.233 | 61.233 | 0 |
| 2 | Confirm2 6w | 157.598 | 2.419 | 35.65% | -52.47% | 55 | 56 | 53.918 | 83.180 | 83.180 | 0 |
| 3 | Confirm2+buffer 6w | 157.598 | 2.419 | 35.65% | -52.47% | 55 | 56 | 53.918 | 83.180 | 83.180 | 0 |
| 4 | Pure-relative 8w | 142.278 | 2.184 | 34.0% | -51.88% | 91 | 92 | 50.335 | 70.680 | 70.680 | 0 |
| 5 | APEX Rev2 6w | 134.543 | 2.065 | 33.11% | -60.07% | 112 | 113 | 47.888 | 71.377 | 71.377 | 0 |
| 6 | Buffer 5pp 8w | 119.275 | 1.831 | 31.22% | -66.47% | 54 | 55 | 39.678 | 44.520 | 44.520 | 0 |
| 7 | Confirm2 10w | 114.884 | 1.763 | 30.63% | -56.19% | 46 | 47 | 37.868 | 28.645 | 28.645 | 0 |
| 8 | Buffer 5pp 16w | 102.627 | 1.575 | 28.89% | -57.45% | 33 | 34 | 32.898 | 14.018 | 14.018 | 0 |
| 9 | APEX Rev2 8w originale | 100.469 | 1.542 | 28.56% | -66.13% | 90 | 91 | 34.149 | 55.973 | 55.973 | 0 |
| 10 | APEX Rev2 17w | 63.627 | 0.977 | 21.75% | -68.73% | 64 | 65 | 19.302 | 23.930 | 23.930 | 0 |
| 11 | BTC buy&hold | 51.439 | 0.79 | 18.45% | -75.75% | 0 | 1 | 13.710 | 0 | 0 | 0 |
| 12 | Equal BTC/Oro/SP500 | 38.831 | 0.596 | 14.55% | -43.93% | 0 | 1 | 9.281 | 0 | 0 | 0 |

## Lettura Rapida

1. `Buffer 2pp 6w` resta primo anche dopo tasse e zainetto.
2. `Confirm2 6w` e `Confirm2+buffer 6w` sono identici in questa simulazione.
3. `APEX 8w originale` batte nettamente BTC buy&hold netto tasse, ma scende dietro le varianti 6w filtrate.
4. `Pure-relative 8w` va forte, ma cambia filosofia perche lascia SP500 battere direttamente BTC.
5. La colonna `BTC eq netto` dice quanti BTC finali equivalenti avresti dopo tasse se riconvertissi il valore netto finale al prezzo BTC finale.

## File Generati

- `output/apex_tax_results_2018_1btc.csv`
- `output/apex_tax_results_2018_1btc.json`
