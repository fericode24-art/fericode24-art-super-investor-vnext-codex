# APEX - Strategie usate nel backtest

Stato: documento descrittivo. Nessun risultato numerico.

## Universo Comune

Tutte le strategie ruotano il capitale tra quattro asset:

| Codice | Asset operativo | Strumento di riferimento |
| --- | --- | --- |
| BTC | Bitcoin | WisdomTree Physical Bitcoin |
| GOLD | Oro | iShares Physical Gold ETC |
| SP500 | Azionario USA | iShares Core S&P 500 UCITS ETF |
| CASH | Liquidita' remunerata | XEON / overnight EUR |

Le strategie sono a posizione singola: in ogni momento il capitale e' al 100% su un solo asset. Non ci sono pesi parziali.

## Dati e Timing

Il backtest usa osservazioni settimanali.

La data di riferimento e' il mercoledi. Per la versione simulata sull'apertura viene usato il prezzo di apertura disponibile della settimana. Se il mercoledi non e' disponibile, il motore usa il giorno lavorativo precedente nella stessa settimana.

Il momentum e' calcolato cosi':

```text
momentum_asset = prezzo_asset_oggi / prezzo_asset_N_settimane_fa - 1
```

Dove `N` cambia in base alla variante: 6, 8, 10, 16 o 17 settimane.

## APEX Rev2

Questa e' la strategia originale BTC-centrica.

Per ogni mercoledi calcola:

```text
ret_BTC
ret_GOLD
ret_SP500
```

Poi applica le regole in questo ordine:

```text
1. Se BTC e' positivo e BTC >= Oro:
   segnale = BTC

2. Altrimenti, se Oro e' positivo e Oro > SP500:
   segnale = GOLD

3. Altrimenti, se SP500 e' positivo e SP500 > Oro:
   segnale = SP500

4. Altrimenti:
   segnale = CASH
```

La regola centrale e' questa: SP500 non batte mai direttamente BTC. Se BTC e' positivo e batte o pareggia l'oro, BTC vince anche se SP500 ha fatto meglio.

Nel backtest questa logica e' stata provata con piu lookback:

| Nome | Lookback | Funzionamento |
| --- | --- | --- |
| APEX Rev2 6w | 6 settimane | Versione piu reattiva della regola originale |
| APEX Rev2 8w originale | 8 settimane | Versione base della strategia |
| APEX Rev2 17w | 17 settimane | Versione piu lenta, usata per testare lookback lunghi |

## Buffer 2pp 6w

Questa variante parte dalla regola APEX Rev2, ma aggiunge un filtro contro i cambi inutili.

Funzionamento:

```text
1. Calcola il segnale APEX Rev2 con lookback 6 settimane.
2. Se il segnale e' uguale alla posizione attuale, resta fermo.
3. Se il segnale e' diverso, cambia solo se il nuovo asset supera l'asset attuale di almeno 2 punti percentuali di momentum.
4. Se il vantaggio e' inferiore a 2 punti percentuali, resta sull'asset attuale.
```

Esempio concettuale:

```text
Posizione attuale: BTC
Nuovo segnale grezzo: GOLD
Momentum GOLD - momentum BTC >= 2 punti percentuali -> cambio
Altrimenti -> nessun cambio
```

Scopo: ridurre i falsi cambi quando due asset sono vicini.

## Buffer 5pp

Stessa logica del buffer 2pp, ma con filtro piu severo.

Funzionamento:

```text
1. Calcola il segnale APEX Rev2.
2. Cambia asset solo se il nuovo asset supera l'asset attuale di almeno 5 punti percentuali di momentum.
3. Se il vantaggio e' minore, mantiene la posizione corrente.
```

Nel backtest sono state usate queste versioni:

| Nome | Lookback | Funzionamento |
| --- | --- | --- |
| Buffer 5pp 8w | 8 settimane | APEX 8w con soglia di cambio a 5 punti percentuali |
| Buffer 5pp 16w | 16 settimane | APEX lento con soglia di cambio a 5 punti percentuali |

Scopo: ridurre ancora di piu gli swap, accettando il rischio di entrare piu tardi.

## Confirm2

Questa variante richiede conferma del segnale per due settimane consecutive.

Funzionamento:

```text
1. Calcola il segnale APEX Rev2.
2. Se il segnale e' uguale alla posizione attuale, resta fermo.
3. Se appare un nuovo segnale diverso, non cambia subito.
4. Cambia solo se lo stesso nuovo segnale si ripresenta anche alla settimana successiva.
```

Esempio concettuale:

```text
Settimana 1: posizione BTC, nuovo segnale GOLD -> osserva, non cambia
Settimana 2: nuovo segnale ancora GOLD -> cambia a GOLD
Settimana 2: nuovo segnale torna BTC o cambia ancora -> resta fermo
```

Nel backtest sono state usate queste versioni:

| Nome | Lookback | Funzionamento |
| --- | --- | --- |
| Confirm2 6w | 6 settimane | Reattiva, ma richiede conferma |
| Confirm2 10w | 10 settimane | Piu lenta, richiede conferma |

Scopo: evitare cambi causati da un solo segnale settimanale isolato.

## Confirm2 + Buffer 6w

Questa variante combina conferma e filtro.

Funzionamento:

```text
1. Calcola il segnale APEX Rev2 con lookback 6 settimane.
2. Richiede che il nuovo segnale diverso sia confermato per due settimane consecutive.
3. Dopo la conferma, cambia solo se il nuovo asset supera l'asset attuale di almeno 2 punti percentuali di momentum.
4. Se una delle due condizioni manca, resta sull'asset attuale.
```

Scopo: cambiare solo quando il segnale e' sia persistente sia abbastanza piu forte.

## Pure Relative 8w

Questa variante cambia la filosofia della strategia.

Non usa la priorita' BTC-centrica di APEX Rev2. Sceglie semplicemente l'asset con momentum positivo piu alto.

Funzionamento:

```text
1. Calcola il momentum 8 settimane di BTC, Oro e SP500.
2. Trova l'asset con momentum piu alto.
3. Se il momentum migliore e' positivo, segnale = asset migliore.
4. Se nessun momentum e' positivo, segnale = CASH.
```

Differenza critica rispetto ad APEX Rev2:

```text
In APEX Rev2, SP500 non puo battere direttamente BTC.
In Pure Relative, SP500 puo battere BTC se ha momentum piu alto.
```

Scopo: testare una rotazione momentum pura, meno legata alla tesi BTC-centrica.

## BTC Buy & Hold

Benchmark semplice.

Funzionamento:

```text
1. Compra BTC all'inizio del periodo.
2. Non fa nessun cambio.
3. Mantiene BTC fino alla fine.
```

Scopo: verificare se APEX crea valore rispetto al semplice tenere Bitcoin.

## Equal BTC / Oro / SP500

Benchmark diversificato statico.

Funzionamento:

```text
1. Divide il capitale iniziale in tre parti uguali.
2. Compra BTC, Oro e SP500.
3. Non fa rotazioni settimanali.
4. Mantiene le tre posizioni fino alla fine.
```

Nel backtest non e' stato applicato ribilanciamento periodico; e' un paniere statico iniziale.

Scopo: confrontare APEX con una diversificazione passiva semplice.

## Costi e Fiscalita' Nel Backtest Netto

Nel backtest fiscale le strategie operative applicano:

```text
costo cambio = 0,30% del controvalore quando avviene un cambio posizione
```

Fiscalita' modellata:

```text
BTC ETP  -> redditi diversi
Oro ETC  -> redditi diversi
SP500 ETF UCITS -> redditi di capitale sulle plus, minus nello zainetto
CASH/XEON ETF UCITS -> redditi di capitale sulle plus, minus nello zainetto
```

Lo zainetto fiscale e' modellato come credito da minusvalenze utilizzabile entro il quarto anno successivo. Le plus su BTC ETP e Oro ETC possono usare lo zainetto disponibile. Le plus su ETF UCITS non lo usano.

Questa sezione descrive solo il funzionamento del modello fiscale usato nel backtest, non sostituisce una verifica fiscale professionale sul caso reale.
