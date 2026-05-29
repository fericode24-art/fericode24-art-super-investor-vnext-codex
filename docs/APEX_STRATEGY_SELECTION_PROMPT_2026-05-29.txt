# Prompt per scegliere la strategia APEX finale

Obiettivo: decidere quale strategia APEX seguire in produzione, quale timing di segnale usare, e quale candidata e' piu robusta, cioe' piu lineare e con meno drawdown.

Contesto: la strategia nasce dal concetto Dual Momentum BTC/Gold e dalla versione APEX Rev2 BTC-centrica. L'utente accetta fino a 15 swap/anno. Operativita' Fineco, strumenti in EUR quando disponibili, segnale informativo senza ordini automatici.

Universo:
- BTC: WisdomTree Physical Bitcoin o ETP BTC equivalente acquistabile su Fineco.
- GOLD: iShares Physical Gold / ETC oro fisico a basso TER.
- SP500: ETF UCITS S&P 500 basso TER e liquido.
- CASH: XEON / overnight EUR.

Regole comuni:
- 100% del capitale su un solo asset alla volta.
- Momentum = prezzo oggi / prezzo lookback - 1, calcolato in EUR.
- Costo swap nel test base: 0,30% per cambio.
- Vincolo operativo: scartare strategie sopra 15 swap/anno.

Strategie candidate da confrontare:

```python
STRATEGIES = [
    {
        "name": "APEX Rev2 originale 8w",
        "type": "weekly",
        "timing_to_test": ["mercoledi close", "mercoledi open"],
        "lookback": "8 settimane",
        "rule": "BTC vince se ret_BTC > 0 e ret_BTC >= ret_GOLD; altrimenti GOLD se positivo e > SP500; altrimenti SP500 se positivo e > GOLD; altrimenti CASH.",
        "note": "SP500 non compete mai direttamente con BTC. Questa e' la regola originale da usare come benchmark obbligatorio."
    },
    {
        "name": "Buffer 5pp 5w",
        "type": "weekly",
        "timing_to_test": ["venerdi open"],
        "lookback": "5 settimane",
        "rule": "Calcola APEX Rev2; cambia asset solo se il nuovo asset batte quello corrente di almeno 5 punti percentuali di momentum."
    },
    {
        "name": "Buffer 3pp 6w",
        "type": "weekly",
        "timing_to_test": ["martedi close"],
        "lookback": "6 settimane",
        "rule": "Calcola APEX Rev2; cambia asset solo se il nuovo asset batte quello corrente di almeno 3 punti percentuali di momentum."
    },
    {
        "name": "Pure Relative 7w",
        "type": "weekly",
        "timing_to_test": ["martedi close"],
        "lookback": "7 settimane",
        "rule": "Sceglie l'asset con momentum positivo piu alto tra BTC, GOLD e SP500; se nessuno e' positivo va in CASH. Nessuna priorita' BTC."
    },
    {
        "name": "Confirm2+Buffer2 90d",
        "type": "daily",
        "timing_to_test": ["daily open"],
        "lookback": "90 giorni di trading",
        "rule": "Calcola APEX Rev2 ogni giorno; richiede due segnali consecutivi uguali e poi cambia solo se il nuovo asset supera quello corrente di almeno 2 punti percentuali."
    },
    {
        "name": "Buffer 5pp 8w",
        "type": "weekly",
        "timing_to_test": ["lunedi open"],
        "lookback": "8 settimane",
        "rule": "Calcola APEX Rev2; cambia asset solo se il nuovo asset batte quello corrente di almeno 5 punti percentuali."
    },
]
```

Richiesta di valutazione:
1. Filtra tutto con massimo 15 swap/anno.
2. Classifica i migliori per CAGR lordo e poi per CAGR netto fiscale.
3. Tra i migliori, scegli il candidato piu robusto usando: MaxDD, ulcer index, linearita' R2 della curva log, tempo sotto -20% e -40%, peggior anno, Sharpe out-of-sample 2023-2026.
4. Controlla se il timing vincente e' stabile o se sembra overfitting di calendario.
5. Confronta sempre contro APEX Rev2 originale 8w.
6. Restituisci una decisione finale: strategia consigliata, timing segnale consigliato, motivi, rischi residui e cosa monitorare live.
