# APEX Degen - decisione di ricerca 2026-05-30

Questa nota non modifica APEX Legit, non cambia l'app e non attiva workflow.
Serve solo a fissare la candidata di ricerca per una terza strategia separata
chiamata APEX Degen.

## Stato decisione

APEX Degen resta una strategia separata. Non sostituisce APEX Legit.

Decisione aggiornata: la candidata definitiva di ricerca e' `APEX Degen
Pure Relative + BTC SMA30 + CL2 SMA10`, con radar giornaliero solo
informativo da progettare prima dell'implementazione in app.

## Candidata definitiva salvata

APEX Degen Pure:

- Universo: BTC + Gold 2x + CL2 + XEON
- BTC: proxy BTC EUR / ETP BTC in esecuzione reale
- Gold 2x: WisdomTree Gold 2x Daily Leveraged, LBUL.MI, ISIN JE00B2NFTL95
- Equity 2x: Amundi MSCI USA Daily 2x Leveraged, CL2.MI, ISIN FR0010755611
- Fallback difensivo: XEON / cash remunerato
- Timing ufficiale: martedi
- Lookback: 6 settimane
- Buffer: 5 punti percentuali
- Filtro BTC: SMA 30 settimane
- Filtro CL2: SMA 10 settimane
- Filtro Gold 2x: nessun filtro operativo nella candidata principale
- Regola: Pure Relative. Vince l'asset con momentum piu alto, se positivo,
  tra BTC, Gold 2x e CL2. Se l'asset vincente non passa il proprio filtro
  trend, viene bocciato e il motore passa al miglior asset alternativo valido.
  Se nessun asset rischioso e' valido, va su XEON.

## Numeri ricerca 2018-01-01 -> 2026-05-29

Capitale iniziale: 10.000 EUR.
Modello: EUR, regime dichiarativo simulato con imposta annuale, aliquota 26%,
costi 0,30% per switch, minusvalenze riportabili dove applicabile.

- Finale: circa 682.700 EUR
- CAGR: circa 65,3%
- Max drawdown daily: circa -43,1%
- Calmar: circa 1,52
- Ulcer: circa 19,8%
- R2 linearita: circa 0,948
- Swap totali: 54
- Swap/anno: circa 6,4
- Anni positivi: 6/9
- Peggior anno: circa -33,1%
- Evento max drawdown: 2021-09-06 -> 2022-12-15

## Settimane per asset

Conteggio precedente su curva settimanale salvato come riferimento storico:

- BTC: area 135-150 settimane a seconda del modello daily/weekly
- Gold 2x: area 120-130 settimane
- CL2: area 120-140 settimane
- XEON: area 30-55 settimane

Il conteggio definitivo va rigenerato dal motore app quando Degen verra
implementata, per mantenere coerenza con la curva daily mostrata in UI.

## Test commodities

Il primo test con proxy USA DBC sembrava migliorare la strategia, ma con
strumenti europei piu realistici su Borsa/Fineco, come AIGC.MI e CMOD.MI, il
vantaggio non e abbastanza robusto:

- AIGC/CMOD possono alzare leggermente il finale in alcune versioni.
- Peggiorano pero drawdown, Ulcer o Calmar rispetto a XEON.
- La correlazione con gli asset rischiosi e piu alta del cash.

Decisione: commodities restano in watchlist, ma non sostituiscono XEON nella
candidata principale.

## Test elasticita e daily flash

Abbiamo testato se Degen potesse diventare piu libera nel giorno di esecuzione
o addirittura cambiare asset ogni giorno.

Conclusione:

- Il segnale ufficiale deve restare settimanale.
- La versione daily operativa non migliora la robustezza.
- Le uscite giornaliere su SMA/trailing tendono a uscire dopo il danno e a
  rientrare peggio.
- La rotazione daily/twice abbassa il CAGR o peggiora il drawdown nelle finestre
  forward/stress.
- Il radar giornaliero resta utile solo come allerta informativa, non come ordine
  operativo.

Numeri indicativi:

- Degen definitiva `Pure + BTC SMA30 + CL2 SMA10`: circa 683k da 10k,
  CAGR 65,3%, MaxDD daily -43,1%, 6,4 swap/anno.
- Variante difensiva con `Gold2 SMA52`: circa 625k da 10k, CAGR 63,6%,
  MaxDD daily -42,1%, 6,5 swap/anno.
- Daily/twice rotation migliori: non promosse; nel test forward/stress hanno
  peggiorato drawdown o CAGR rispetto al segnale settimanale.

## Regola futura da implementare, se richiesta

Implementazione app vNext avviata:

1. Il segnale operativo ufficiale resta martedi.
2. Il motore ha un radar daily non operativo, costruito bene e coerente
   con gli altri APEX.
3. Il radar mostra:
   - asset che vincerebbe oggi se il motore fosse letto adesso;
   - differenza di momentum contro l'asset ufficiale;
   - stato filtri SMA di BTC, CL2 e, se presente nella variante, Gold2;
   - alert "attenzione inversione" se l'asset ufficiale perde il proprio filtro
     o viene battuto con margine importante da un altro asset valido;
   - storico alert, senza trasformarli in ordini.
4. Il radar non deve generare automaticamente uno swap.
5. Lo swap resta deciso dal segnale settimanale ufficiale.
6. Lo stesso concetto di radar daily e' portato anche su APEX Legit e APEX Dex,
   come livello informativo comune.

Decisione finale salvata: APEX Degen = Pure Relative settimanale aggressiva,
BTC SMA30, CL2 SMA10, Gold2 libero, XEON come fallback. Il daily radar e' solo
una funzione di avviso.
