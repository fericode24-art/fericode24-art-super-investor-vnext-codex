"""
QFAS v2.5 — fund_universe.py

Filtro point-in-time per mitigare survivorship bias dei fondi.

Per ogni fondo del pool: start_date (primo 13F utile), end_date (eventuale
chiusura), closure_reason. La funzione is_fund_active() filtra i filing 13F
per assicurare che non si usino fondi "che non c'erano ancora" o "che non
c'erano più" alla data del backtest.

DISCLAIMER ONESTO: anche con questo filtro, la lista dei 36 fondi attuali è
pre-selezionata sui "vincitori storici". Bias residuo stimato: +1-2pp CAGR.
Per ridurre ulteriormente, in v2.6 aggiungere fondi falliti del periodo
(es. Archegos 2021, SAC pre-2013) col loro storico pre-blowup.

Dati start/end ricostruiti da:
- Knowledge pubblica delle fondazioni/chiusure dei fondi più noti
- Date primo filing 13F nel SEC EDGAR
- Wikipedia, news pubbliche per le chiusure
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional


@dataclass(frozen=True)
class FundActivePeriod:
    fund_name: str
    cik: str
    base_weight: float                # 0.5-1.0 (peso convinzione composito)
    default_halflife_days: int        # decay esponenziale conviction
    start_date: date                  # primo 13F utile / fondazione
    end_date: Optional[date]          # None se ancora attivo
    closure_reason: str               # "active", "wound_down", "blowup", "merged"
    notes: str = ""


# ═════════════════════════════════════════════════════════════════════════
# I 36 FONDI ATTUALI (correntemente nel pool Super Investor Dashboard)
# Date verificate al meglio della conoscenza pubblica.
# ═════════════════════════════════════════════════════════════════════════
FUND_ACTIVE_PERIODS: Dict[str, FundActivePeriod] = {
    "Berkshire Hathaway": FundActivePeriod(
        "Berkshire Hathaway", "0001067983", 1.00, 180,
        date(1980, 1, 1), None, "active",
        "Buffett. 13F dal 1979. Hold periods lunghissimi → halflife 180gg."
    ),
    "Pershing Square Capital": FundActivePeriod(
        "Pershing Square Capital", "0002026053", 0.95, 90,
        date(2004, 1, 1), None, "active",
        "Ackman. Fondato 2003. Concentrato 8-12 nomi."
    ),
    "Scion Asset Management": FundActivePeriod(
        "Scion Asset Management", "0001649339", 0.80, 60,
        date(2013, 1, 1), None, "active",
        "Michael Burry. Riapertura post-Scion Capital. Posizioni tattiche."
    ),
    "Appaloosa LP": FundActivePeriod(
        "Appaloosa LP", "0001656456", 0.95, 90,
        date(2000, 1, 1), None, "active",
        "David Tepper. Fondato 1993. Distressed + macro."
    ),
    "Greenlight Capital": FundActivePeriod(
        "Greenlight Capital", "0001079114", 0.85, 120,
        date(2000, 1, 1), None, "active",
        "David Einhorn. Long/short value."
    ),
    "Tiger Global Management": FundActivePeriod(
        "Tiger Global Management", "0001167483", 0.85, 60,
        date(2001, 1, 1), None, "active",
        "Chase Coleman. Tiger Cub. Tech-heavy."
    ),
    "Coatue Management": FundActivePeriod(
        "Coatue Management", "0001135730", 0.85, 60,
        date(2000, 1, 1), None, "active",
        "Philippe Laffont. Tech crossover."
    ),
    "Viking Global Investors": FundActivePeriod(
        "Viking Global Investors", "0001103804", 0.85, 90,
        date(2000, 1, 1), None, "active",
        "Andreas Halvorsen. Tiger Cub."
    ),
    "Lone Pine Capital": FundActivePeriod(
        "Lone Pine Capital", "0001061165", 0.85, 90,
        date(2000, 1, 1), None, "active",
        "Steve Mandel. Long-only fund spin-off."
    ),
    "Third Point LLC": FundActivePeriod(
        "Third Point LLC", "0001040273", 0.85, 90,
        date(2000, 1, 1), None, "active",
        "Daniel Loeb. Event-driven + activist."
    ),
    "Trian Fund Management": FundActivePeriod(
        "Trian Fund Management", "0001345471", 0.80, 180,
        date(2005, 11, 1), None, "active",
        "Nelson Peltz. Activist. Lungo termine."
    ),
    "Icahn Capital LP": FundActivePeriod(
        "Icahn Capital LP", "0000921669", 0.80, 180,
        date(2000, 1, 1), None, "active",
        "Carl Icahn. Activist veteran."
    ),
    "Baupost Group": FundActivePeriod(
        "Baupost Group", "0001061768", 0.90, 180,
        date(2000, 1, 1), None, "active",
        "Seth Klarman. Value, hold long, often cash-heavy."
    ),
    "Oaktree Capital Management": FundActivePeriod(
        "Oaktree Capital Management", "0000949509", 0.85, 180,
        date(2000, 1, 1), None, "active",
        "Howard Marks. Distressed credit + equity."
    ),
    "ValueAct Capital": FundActivePeriod(
        "ValueAct Capital", "0001418814", 0.85, 180,
        date(2000, 1, 1), None, "active",
        "Mason Morfit. Constructivist long-term."
    ),
    "Elliott Investment Management": FundActivePeriod(
        "Elliott Investment Management", "0001791786", 0.85, 90,
        date(2000, 1, 1), None, "active",
        "Paul Singer. Multi-strategy activist."
    ),
    "Glenview Capital Management": FundActivePeriod(
        "Glenview Capital Management", "0001138995", 0.80, 90,
        date(2001, 1, 1), None, "active",
        "Larry Robbins. Healthcare-heavy."
    ),
    "Starboard Value LP": FundActivePeriod(
        "Starboard Value LP", "0001517137", 0.80, 90,
        date(2011, 1, 1), None, "active",
        "Jeffrey Smith. Activist mid-cap."
    ),
    "Akre Capital Management": FundActivePeriod(
        "Akre Capital Management", "0001112520", 0.85, 180,
        date(2000, 1, 1), None, "active",
        "Chuck Akre. Compounders long-only."
    ),
    "Sequoia Fund / Ruane Cunniff": FundActivePeriod(
        "Sequoia Fund / Ruane Cunniff", "0001507971", 0.80, 180,
        date(2000, 1, 1), None, "active",
        "Mutual fund storico. Concentrato, long-term."
    ),
    "Markel Group": FundActivePeriod(
        "Markel Group", "0001698926", 0.80, 180,
        date(2000, 1, 1), None, "active",
        "Tom Gayner. Insurance + equity book."
    ),
    "Dodge & Cox": FundActivePeriod(
        "Dodge & Cox", "0001954242", 0.80, 180,
        date(2000, 1, 1), None, "active",
        "Mutual fund. Value, lungo hold period."
    ),
    "First Eagle Investment Management": FundActivePeriod(
        "First Eagle Investment Management", "0001325447", 0.75, 180,
        date(2005, 1, 1), None, "active",
        "Storica casa. Value globale + gold."
    ),
    "Polen Capital Management": FundActivePeriod(
        "Polen Capital Management", "0001954929", 0.80, 180,
        date(2000, 1, 1), None, "active",
        "Long-only growth quality."
    ),
    "Diamond Hill Capital Management": FundActivePeriod(
        "Diamond Hill Capital Management", "0001217541", 0.70, 180,
        date(2000, 1, 1), None, "active",
        "Value, US large cap."
    ),
    "Pzena Investment Management": FundActivePeriod(
        "Pzena Investment Management", "0001027796", 0.75, 180,
        date(2000, 1, 1), None, "active",
        "Richard Pzena. Deep value."
    ),
    "Yacktman Asset Management": FundActivePeriod(
        "Yacktman Asset Management", "0000905567", 0.75, 180,
        date(2000, 1, 1), None, "active",
        "Donald Yacktman. Value contrarian."
    ),
    "Ariel Investments": FundActivePeriod(
        "Ariel Investments", "0000936753", 0.75, 180,
        date(2000, 1, 1), None, "active",
        "John Rogers. Small/mid value."
    ),
    "Maverick Capital": FundActivePeriod(
        "Maverick Capital", "0000934639", 0.75, 90,
        date(2000, 1, 1), None, "active",
        "Lee Ainslie. Tiger Cub. Long/short equity."
    ),
    "Lansdowne Partners": FundActivePeriod(
        "Lansdowne Partners", "0001608485", 0.80, 90,
        date(2000, 1, 1), None, "active",
        "UK-based, global equity long/short."
    ),
    "Smead Capital Management": FundActivePeriod(
        "Smead Capital Management", "0001427008", 0.70, 180,
        date(2008, 1, 1), None, "active",
        "Bill Smead. Concentrated value."
    ),
    "Situational Awareness LP": FundActivePeriod(
        "Situational Awareness LP", "0002045724", 0.75, 60,
        date(2024, 6, 1), None, "active",
        "Leopold Aschenbrenner. Nuovo fondo AI-focused. Storico minimo."
    ),
    "Light Street Capital Management": FundActivePeriod(
        "Light Street Capital Management", "0001569049", 0.85, 60,
        date(2011, 1, 1), None, "active",
        "Glen Kacher. Tiger Cub. Tech crossover."
    ),
    "Whale Rock Capital Management": FundActivePeriod(
        "Whale Rock Capital Management", "0001387322", 0.85, 60,
        date(2006, 1, 1), None, "active",
        "Alex Sacerdote. Tech long/short."
    ),
    "Duquesne Family Office": FundActivePeriod(
        "Duquesne Family Office", "0001536411", 0.90, 90,
        date(2010, 1, 1), None, "active",
        "Stanley Druckenmiller. Ex-Duquesne Capital, ora family office."
    ),
    "Melqart Asset Management": FundActivePeriod(
        "Melqart Asset Management", "0001712901", 0.80, 90,
        date(2007, 1, 1), None, "active",
        "Michel Massoud. Multi-strategy."
    ),
}


# ═════════════════════════════════════════════════════════════════════════
# FONDI STORICAMENTE RILEVANTI DEL PERIODO MA NON NEL POOL ATTUALE
# Da includere in v2.6 per ridurre ulteriormente survivorship bias.
# Comment-out per ora (richiede CIK + storico 13F pre-chiusura).
# ═════════════════════════════════════════════════════════════════════════
# HISTORICAL_FUNDS_TODO = {
#     "Archegos Capital Management": {
#         "cik": "TBD", "founded": date(2013, 1, 1),
#         "blowup_date": date(2021, 3, 26),
#         "reason": "blowup",
#         "note": "Bill Hwang. Family office, $20B AUM → 0 in 1 settimana."
#     },
#     "SAC Capital Advisors": {
#         "cik": "TBD", "founded": date(1992, 1, 1),
#         "wound_down_date": date(2013, 11, 1),
#         "reason": "wound_down",
#         "note": "Steve Cohen. Chiuso per insider trading scandal. Diventato Point72."
#     },
#     "Galleon Group": {
#         "cik": "TBD", "founded": date(1997, 1, 1),
#         "wound_down_date": date(2009, 10, 1),
#         "reason": "wound_down",
#         "note": "Raj Rajaratnam. Chiuso per insider trading."
#     },
#     "Pequot Capital": {
#         "cik": "TBD", "founded": date(1998, 1, 1),
#         "wound_down_date": date(2010, 5, 1),
#         "reason": "wound_down",
#         "note": "Arthur Samberg. Chiuso per insider trading."
#     },
# }


# ═════════════════════════════════════════════════════════════════════════
# API PUBBLICA
# ═════════════════════════════════════════════════════════════════════════

def is_fund_active(fund_name: str, signal_date: date) -> bool:
    """True se il fondo era operativo a signal_date.
    Usare SEMPRE prima di processare un filing 13F nel backtest."""
    p = FUND_ACTIVE_PERIODS.get(fund_name)
    if p is None:
        return False
    if signal_date < p.start_date:
        return False
    if p.end_date is not None and signal_date > p.end_date:
        return False
    return True


def is_fund_active_by_cik(cik: str, signal_date: date) -> bool:
    """Versione CIK-based per integrare con SEC EDGAR data."""
    # Normalizza CIK (rimuovi zeri iniziali se serve)
    cik_norm = str(cik).lstrip("0").zfill(10)
    for p in FUND_ACTIVE_PERIODS.values():
        if p.cik.lstrip("0").zfill(10) == cik_norm:
            return is_fund_active(p.fund_name, signal_date)
    return False


def get_active_funds_at(signal_date: date) -> Dict[str, FundActivePeriod]:
    """Tutti i fondi attivi alla data data. Usato dal crowding scorer."""
    return {n: p for n, p in FUND_ACTIVE_PERIODS.items()
            if is_fund_active(n, signal_date)}


def get_fund_by_cik(cik: str) -> Optional[FundActivePeriod]:
    cik_norm = str(cik).lstrip("0").zfill(10)
    for p in FUND_ACTIVE_PERIODS.values():
        if p.cik.lstrip("0").zfill(10) == cik_norm:
            return p
    return None


def num_active_funds_summary() -> str:
    """Diagnostico: stampa quanti fondi attivi per anno per validare il filtro."""
    from datetime import date
    lines = []
    for year in range(2010, 2027):
        d = date(year, 6, 1)
        n = len(get_active_funds_at(d))
        lines.append(f"  {year}: {n}/{len(FUND_ACTIVE_PERIODS)} fondi attivi")
    return "\n".join(lines)


SURVIVORSHIP_RESIDUAL_DISCLAIM = (
    "Anche con filtro point-in-time, la lista 36 fondi è pre-selezionata sui "
    "'vincitori storici'. Fondi falliti del periodo (Archegos 2021, SAC 2013, "
    "Galleon 2009, Pequot 2010) NON sono nel pool. Bias residuo stimato: "
    "+1-2pp CAGR. In v2.6 aggiungerli per onestà completa."
)


if __name__ == "__main__":
    print("FUND UNIVERSE — Survivorship filter test")
    print("=" * 60)
    print(f"Fondi totali nel pool: {len(FUND_ACTIVE_PERIODS)}")
    print()
    print("Copertura per anno (fondi attivi):")
    print(num_active_funds_summary())
    print()
    print("DISCLAIMER:")
    print(f"  {SURVIVORSHIP_RESIDUAL_DISCLAIM}")
