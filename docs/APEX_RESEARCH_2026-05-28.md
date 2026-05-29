# APEX research log - 2026-05-28

Stato: primo giro tecnico, non definitivo. Nessun deploy.

## Decisione timing

La richiesta aggiornata e' corretta: se il segnale deve uscire mercoledi mattina, non deve basarsi solo sul close del martedi.

Scelta proposta:

- run automatica: mercoledi ore 09:45 Europe/Rome;
- motivo: alle 09:10 il mercato europeo puo essere ancora poco formato su alcuni ETC/ETF;
- dati live: ultima barra intraday Yahoo 5 minuti degli strumenti EUR disponibili;
- esecuzione: Fineco dopo lettura segnale;
- manuale: futuro bottone "Ricalcola APEX" che rilancia lo stesso motore.

## Strumenti verificati

| Asset | Prodotto | ISIN | Ticker operativo | Yahoo test |
|---|---|---|---|---|
| BTC | WisdomTree Physical Bitcoin | GB00BJYDH287 | WBTC Borsa Italiana / WBIT Xetra | WBTC.PA funziona; WBTC.MI e WBITG.DE non rispondono su Yahoo chart |
| Oro | iShares Physical Gold ETC | IE00B4ND3602 | SGLN.MI / PPFB.DE | entrambi funzionano |
| S&P 500 | iShares Core S&P 500 UCITS ETF Acc | IE00B5BMR087 | CSSPX.MI / SXR8.DE | entrambi funzionano |
| Cash | Xtrackers II EUR Overnight Rate Swap UCITS ETF 1C | LU0290358497 | XEON.MI / XEON.DE | entrambi funzionano |

Conseguenza: per il live usero' strumenti quotati in EUR. Per BTC, finche Yahoo non serve `WBTC.MI`/`WBITG.DE`, usero' `WBTC.PA` come proxy EUR dello stesso ISIN; fallback secondario `BTC-USD/EURUSD`.

## Fix dati importante

La prima chiamata Yahoo con `range=max&interval=1d` restituiva dati mensili, non daily veri. Ho corretto la query usando `period1/period2`, ottenendo 611 osservazioni settimanali dal 2014-09-17 al 2026-05-27.

Questo era un punto critico: senza correzione il backtest sembrava funzionare, ma era statisticamente sporcato.

## Test logica

Aggiunti test della regola pura:

- BTC vince se BTC > 0 e BTC >= Oro, anche se S&P 500 e' piu forte.
- Oro vince solo se BTC non qualifica e Oro batte S&P 500.
- S&P 500 vince solo se BTC non qualifica e S&P 500 batte Oro.
- Cash se nessuno qualifica.
- errore se ci sono meno di 9 osservazioni settimanali.

Check eseguiti:

- import moduli APEX: OK;
- test logici APEX: OK;
- `npm.cmd run check`: OK.

## Primo backtest proxy lungo

Profilo: proxy EUR, dati daily veri.

- BTC: `BTC-USD / EURUSD`
- Oro: `GC=F / EURUSD`
- S&P 500: `^GSPC / EURUSD`
- Cash: `XEON.MI` quando disponibile
- costo cambio: 30 bps
- periodo utile: 2014-09-17 -> 2026-05-27

### Prezzi close

| Lookback | CAGR | Max DD | Vol | Sharpe | Cambi |
|---:|---:|---:|---:|---:|---:|
| 4w | 44.27% | -71.75% | 53.47% | 0.940 | 203 |
| 6w | 54.39% | -67.49% | 53.57% | 1.066 | 166 |
| 8w | 71.93% | -62.86% | 54.93% | 1.249 | 123 |
| 10w | 57.59% | -64.56% | 56.25% | 1.081 | 92 |
| 12w | 60.08% | -59.11% | 53.67% | 1.134 | 111 |
| 16w | 65.23% | -62.29% | 57.18% | 1.154 | 94 |

Benchmark stesso periodo:

- BTC buy&hold: CAGR 56.00%, max DD -78.69%.
- Equal BTC/Oro/SP500: CAGR 42.55%, max DD -73.49%.
- Oro: CAGR 12.62%.
- S&P 500: CAGR 13.02%.

Lettura iniziale: 8w e' il migliore del set per CAGR, Sharpe e rapporto rendimento/drawdown rispetto a BTC buy&hold.

### Prezzi open

Questo e' piu coerente con APEX Morning.

| Lookback | CAGR | Max DD | Vol | Sharpe | Cambi |
|---:|---:|---:|---:|---:|---:|
| 4w | 48.57% | -70.29% | 52.14% | 1.001 | 198 |
| 6w | 64.30% | -67.06% | 52.25% | 1.194 | 153 |
| 8w | 65.79% | -72.10% | 53.97% | 1.190 | 122 |
| 10w | 58.88% | -65.74% | 56.12% | 1.092 | 107 |
| 12w | 58.91% | -58.25% | 54.83% | 1.106 | 101 |
| 16w | 60.97% | -59.96% | 54.12% | 1.134 | 93 |

Lettura iniziale: su open, 8w resta leggermente migliore per CAGR, ma 6w e 16w sono competitivi. Qui serve sensitivity piu profonda, soprattutto su drawdown e costi.

## Sensitivity costi su 8w/open

- 10 bps: CAGR 69.35%, max DD -71.19%, Sharpe 1.230.
- 30 bps: CAGR 65.79%, max DD -72.10%, Sharpe 1.190.
- 60 bps: CAGR 60.58%, max DD -73.59%, Sharpe 1.130.

Anche con costo pesante 60 bps, 8w/open resta sopra BTC buy&hold nel periodo testato, ma il margine si assottiglia.

## Backtest strumenti listati

Profilo `listed/open` con `WBTC.PA`, `SGLN.MI`, `CSSPX.MI`, `XEON.MI` ha solo 17 osservazioni settimanali perche il proxy Yahoo EUR del WisdomTree BTC parte nel 2026.

Conclusione: utile per test live/ticker, non per giudicare la strategia. Il backtest serio resta proxy lungo, poi si valida la differenza tracking con strumenti reali.

## Segnale corrente calcolato dal motore

Ultima settimana disponibile: 2026-05-27.

- proxy close: BTC, ret BTC +8.62%, ret Oro -7.52%, ret S&P 500 +13.76%, confermato BTC.
- proxy open: BTC, ret BTC +10.48%, ret Oro -5.45%, ret S&P 500 +14.12%, confermato BTC.
- listed open: BTC, ret BTC +8.99%, ret Oro -5.45%, ret S&P 500 +14.01%, confermato BTC.

Nota: qui si vede bene la regola BTC-centrica. S&P 500 ha momentum superiore a BTC, ma BTC e' positivo e batte Oro, quindi la strategia resta BTC.

## Prossimi test necessari

Prima di collegarla all'app:

1. validare variante 8w con buffer anti-whipsaw;
2. validare conferma 2 settimane;
3. split per sottoperiodi: 2014-2017, 2018-2020, 2021-2023, 2024-2026;
4. worst months / worst years;
5. turnover annuale e costo effettivo;
6. simulazione "manuale mercoledi 09:45" con open storico;
7. export `dashboard/data-apex.json`;
8. workflow GitHub mercoledi 09:45;
9. bottone app manuale.

## Verdetto provvisorio

Per ora non ho trovato "di meglio" in modo convincente: 8w rimane la candidata principale. La sto trattando come ipotesi forte da stressare, non come dogma. La prossima cosa sensata e' provare buffer/conferma e vedere se riducono drawdown/cambi senza mangiare troppo CAGR.

