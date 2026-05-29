# APEX R / ALFA DEX - revisione e confronto 2026-05-29

Stato: confronto quantitativo locale, nessun deploy.

## Metodo

- Periodo: 2018-01-01 -> 2026-05-29.
- Dati: stessi proxy EUR Yahoo usati nei test APEX precedenti.
- Costo swap: 0,30%.
- APEX R e APEX ALFA DEX sono implementate seguendo il codice incollato.
- APEX R viene mostrata in due modi:
  - `as-written`: perdite UCITS SP500 considerate perse, come nel codice incollato.
  - `fisco corretto`: perdite UCITS considerate minus nello zainetto, ma plus ETF tassate come redditi di capitale. La differenza qui e' piccola.
- La vincitrice attuale e' presa dal report precedente: `Buffer 5pp 5w venerdi open`.

## Risultati

| Strategia | Timing | Tipo | CAGR | Finale 10k | MaxDD | Calmar | Sharpe | R2 | Ulcer | Sw/anno |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| APEX R Fineco proposta (as-written) | mercoledi close | netto | 31.07% | 96.430 | -42.28% | 0.735 | 0.825 | 0.909 | 26.06% | 9.7 |
| APEX R Fineco proposta (fisco corretto) | mercoledi close | netto | 32.31% | 104.289 | -42.28% | 0.764 | 0.847 | 0.916 | 25.77% | 9.7 |
| APEX ALFA DEX proposta | martedi close | lordo | 54.10% | 373.959 | -28.96% | 1.868 | 1.234 | 0.957 | 14.35% | 6.8 |
| Vincitrice attuale - Buffer 5pp 5w | venerdi open | netto | 42.47% | 169.308 | -44.69% | 0.95 | 1.034 |  |  | 7.4 |

## Lettura

1. `APEX R Fineco proposta` migliora molto la vecchia APEX Rev2 sul drawdown, grazie al filtro SMA30, ma resta sotto la nostra vincitrice su CAGR, capitale finale e Calmar.
2. `APEX ALFA DEX proposta` e' molto forte come lordo e ha drawdown molto piu basso, ma non e' una risposta Fineco: niente SP500, niente tassazione cripto, uso PAXG/proxy oro, operativita' DEX.
3. La vincitrice attuale `Buffer 5pp 5w venerdi open` resta davanti nel confronto netto Fineco: CAGR netto 42,47% e finale netto 169.308 su 10k.
4. Se guardiamo solo robustezza/drawdown, ALFA DEX e' la piu pulita, ma e' un'altra categoria di rischio e fiscalita'.

## Audit tecnico della strategia incollata

- APEX R dichiara prezzi intraday mercoledi 15:00, ma il codice usa solo barre daily Yahoo e nel main usa close.
- APEX R aggiunge filtro SMA30 che cambia la filosofia Rev2: se BTC e' sotto SMA, SP500 viene ignorato come fallback anche quando positivo.
- APEX R usa buffer 0pp: e' piu esposta a micro-cambi rispetto alle varianti buffer.
- APEX ALFA DEX e' lordo imposte: non e' confrontabile col netto Fineco senza modello fiscale cripto.
- APEX ALFA DEX usa GC=F come proxy Oro/PAXG: utile per serie lunga, ma non replica spread, liquidita' e tracking PAXG on-chain.
- Il cash e' modellato a rendimento zero: per Fineco sottostima XEON, per DEX sottostima eventuale stable yield ma evita ipotesi rischiose.
- Il codice as-written tratta le perdite UCITS SP500 come perse; Fineco indica che il capital gain/loss da compravendita quote ha componente redditi diversi, mentre i proventi periodici ETF restano redditi di capitale.

## Decisione provvisoria

- Per Fineco/regime amministrato: APEX R e' sensata come versione difensiva, ma non batte ancora `Buffer 5pp 5w venerdi open`.
- Per DEX: APEX ALFA DEX merita un filone separato, perche' il profilo e' interessante ma non confrontabile al netto fiscale italiano.
- Prossimo test necessario: walk-forward/rolling validation tra `Buffer 5pp 5w`, `APEX R + SMA30`, e una variante ibrida `Buffer 5pp 5w + SMA30` per capire se il filtro anti-crash migliora la nostra vincitrice senza uccidere il CAGR.
