"""
QFAS v2.5 — Configurazione centralizzata.

Tutti i parametri sono qui per audit e tuning facile.
Ogni costante ha un commento col rationale e (se applicabile) il riferimento
alla literature/patch.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
QFAS_DIR = ROOT / "qfas"
CACHE_DIR = QFAS_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class QFASConfig:
    # ═══════════════════════════════════════════════════════════════════════
    # CAPITALE E POSIZIONI (cambiato vs Super Investor 12×€2k)
    # ═══════════════════════════════════════════════════════════════════════
    INITIAL_CAPITAL_EUR: float = 48000.0
    NUM_POSITIONS: int = 8
    POSITION_SIZE_EUR: float = 6000.0       # = INITIAL_CAPITAL / NUM_POSITIONS

    # ═══════════════════════════════════════════════════════════════════════
    # COMPOSIZIONE OPPORTUNITY SCORE
    # ═══════════════════════════════════════════════════════════════════════
    OPPORTUNITY_WEIGHT_RADAR: float = 0.50  # peso del Radar (13F-based)
    OPPORTUNITY_WEIGHT_ENTRY: float = 0.50  # peso dell'Entry (real-time signals)

    # Composizione Radar
    RADAR_WEIGHT_CONVICTION: float = 0.55     # share of fund weight in name
    RADAR_WEIGHT_ACCUMULATION: float = 0.45   # % fondi che accumulano

    # Composizione Entry
    ENTRY_WEIGHT_MOMENTUM: float = 0.35
    ENTRY_WEIGHT_ANALYST: float = 0.30
    ENTRY_WEIGHT_INSIDER: float = 0.25
    ENTRY_WEIGHT_CONGRESSIONAL: float = 0.10

    # ═══════════════════════════════════════════════════════════════════════
    # ANTI-CHURN (testato in sensitivity walk-forward)
    # ═══════════════════════════════════════════════════════════════════════
    SUB_MARGIN_BASE: int = 12              # margine base per sostituzione
    SUB_MARGIN_LOW_VIX_OFFSET: int = -2    # VIX<15 → margine più basso
    SUB_MARGIN_HIGH_VIX_OFFSET: int = +8   # VIX>25 → margine più alto
    MIN_HOLD_DAYS: int = 21                # eccezione status BROKEN/AVOID
    BACINO_SIZE: int = 40                  # bacino qualità per scoring

    # ═══════════════════════════════════════════════════════════════════════
    # CROWDING (point-in-time, denominator = active funds)
    # ═══════════════════════════════════════════════════════════════════════
    CROWDING_THRESHOLD: float = 0.35       # se fund_coverage > 35% applica penalty
    CROWDING_MIN_FACTOR: float = 0.60      # penalty massima (40% reduction)
    CROWDING_ENABLED: bool = True          # toggle per A/B test

    # ═══════════════════════════════════════════════════════════════════════
    # DECAY ESPONENZIALE CONVICTION
    # ═══════════════════════════════════════════════════════════════════════
    DEFAULT_HALFLIFE_DAYS: int = 90        # se fondo non ha pattern stabile
    CONVICTION_PCT_CAP: float = 15.0       # cap su pct_of_portfolio per fondo
    HALFLIFE_MIN_DAYS: int = 90            # PATCH MATEMATICA: 13F sono trimestrali,
                                            # mediana tra variazioni NON può scendere <90gg.
                                            # Formula: halflife = max(HALFLIFE_MIN_DAYS, mediana_calcolata)

    # ═══════════════════════════════════════════════════════════════════════
    # PEAD (Post-Earnings Announcement Drift)
    # ═══════════════════════════════════════════════════════════════════════
    PEAD_MAX_BOOST: float = 15.0           # punti massimi aggiunti a entry_score
    PEAD_SURPRISE_THRESHOLD_POS: float = 3.0   # %
    PEAD_SURPRISE_THRESHOLD_NEG: float = -5.0  # %
    PEAD_WINDOW_DAYS: int = 5              # giorni dopo earnings dove attivo

    # ═══════════════════════════════════════════════════════════════════════
    # SHORT SQUEEZE conditional
    # ═══════════════════════════════════════════════════════════════════════
    SQUEEZE_SI_THRESHOLD: float = 25.0     # short interest % per attivare
    SQUEEZE_INSIDER_THRESHOLD: float = 70.0  # insider score per confermare
    SQUEEZE_MOMENTUM_THRESHOLD: float = 55.0
    SQUEEZE_MULTIPLIER_BULLISH: float = 1.4   # boost score se condizioni OK
    SQUEEZE_MULTIPLIER_BEARISH: float = 0.5   # penalty se segnali negativi

    # ═══════════════════════════════════════════════════════════════════════
    # FILTRO LIQUIDITÀ (pre-processing universo)
    # ═══════════════════════════════════════════════════════════════════════
    MIN_MARKET_CAP_USD: float = 2_000_000_000     # $2B
    MIN_ADV_20D_USD: float = 10_000_000           # $10M average daily volume

    # ═══════════════════════════════════════════════════════════════════════
    # SECTOR CAP CONDIZIONATO (top settori per momentum 3m)
    # ═══════════════════════════════════════════════════════════════════════
    SECTOR_TOP_N: int = 3                  # numero settori "hot"
    SECTOR_CAP_HOT: int = 5                # max posizioni sui top N settori
    SECTOR_CAP_OTHER: int = 3              # max posizioni su altri settori

    # ═══════════════════════════════════════════════════════════════════════
    # SPREAD CALIBRATO MID-CAP (Fineco real)
    # ═══════════════════════════════════════════════════════════════════════
    SPREAD_BASE_AT_10M_ADV: float = 0.0015    # 0.15% a soglia liquidità
    SPREAD_CAP: float = 0.003                  # 0.30% cap estremo

    # ═══════════════════════════════════════════════════════════════════════
    # COSTI BASE
    # ═══════════════════════════════════════════════════════════════════════
    COMMISSION_PER_ORDER_EUR: float = 5.0      # Fineco standard
    CAPITAL_GAIN_TAX_RATE: float = 0.26        # IT capital gain
    LOSS_CARRYFORWARD_YEARS: int = 4           # zainetto fiscale italiano

    # ═══════════════════════════════════════════════════════════════════════
    # FISCALITÀ DIVIDENDI USA per residente italiano
    # ═══════════════════════════════════════════════════════════════════════
    ASSUME_FOREIGN_TAX_CREDIT_RECOVERY: bool = True
    # True  → Scenario A: 26% effettivo (recupera credito via Quadro CE/RM)
    # False → Scenario B: 37.1% effettivo (no recupero)
    DIV_WITHHOLDING_USA: float = 0.15
    DIV_SOSTITUTIVA_NETTO: float = 0.221       # 0.26 × (1 - 0.15)

    # ═══════════════════════════════════════════════════════════════════════
    # TAX-LOSS HARVESTING PROATTIVO (regime amministrato italiano)
    # PATCH WASH SALE: in Italia NON esiste wash sale rule. Vendi in perdita
    # e ricompri lo stesso CUSIP il giorno dopo → minusvalenza RESTA VALIDA.
    # Quindi: NO blocco riacquisto 31gg (era errore del prompt v2.5).
    # ═══════════════════════════════════════════════════════════════════════
    TLH_WINDOW_START_MMDD: str = "11-01"        # 1° novembre
    TLH_WINDOW_END_MMDD: str = "12-20"          # 20 dicembre
    TLH_TRIGGER_LOSS_PCT: float = -8.0          # se posizione < -8% → candidata TLH
    TLH_CHALLENGER_MAX_DELTA: float = 3.0       # challenger score >= incumbent - 3
    TLH_BLOCK_REBUY_SAME_CUSIP: bool = False    # ❌ wash sale US, NON applicabile in IT

    # ═══════════════════════════════════════════════════════════════════════
    # RATE LIMITERS API (gratis-friendly)
    # ═══════════════════════════════════════════════════════════════════════
    YFINANCE_MAX_CALLS_PER_SESSION: int = 500
    SEC_RATE_LIMIT_PER_SEC: int = 10           # SEC EDGAR limit
    OPENFIGI_RATE_LIMIT_PER_MIN: int = 25
    FMP_FREE_CALLS_PER_DAY: int = 250
    FINNHUB_FREE_RATE_PER_MIN: int = 60
    YFINANCE_USER_AGENTS: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/121",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15",
    ])
    # FIX BUG #α (round 3): SEC vuole UA reale (nome + email valida).
    # Se vuoto in env → fallback su valore generico ma con email funzionante
    # (super-investor-dashboard@protonmail.com creato per questo scopo).
    # SEC ban-lista UA con email manifestly fake → tutto il pipeline 13F/Form4/8-K
    # crasha. Override da env var SEC_USER_AGENT consigliato in produzione.
    SEC_USER_AGENT_ENV: str = "SEC_USER_AGENT"
    SEC_USER_AGENT_DEFAULT: str = "Super Investor Dashboard super-investor-dashboard@proton.me"

    # ═══════════════════════════════════════════════════════════════════════
    # API KEYS (caricabili da env vars)
    # ═══════════════════════════════════════════════════════════════════════
    # NOTA: FMP ha messo a paywall analyst grades dopo 31 ago 2025.
    # Usiamo Finnhub free (60 calls/min) per analyst recommendation + earnings.
    FINNHUB_API_KEY_ENV: str = "FINNHUB_API_KEY"   # https://finnhub.io (free 60/min)
    FMP_API_KEY_ENV: str = "FMP_API_KEY"           # legacy, non più usato attivamente


config = QFASConfig()


def get_sec_user_agent() -> str:
    """Risolve l'UA per SEC EDGAR a runtime (env var > default)."""
    import os
    return os.environ.get(config.SEC_USER_AGENT_ENV) or config.SEC_USER_AGENT_DEFAULT


# ═════════════════════════════════════════════════════════════════════════
# SIGNAL AVAILABILITY MAP (patch architetturale anti-look-ahead)
#
# Ogni segnale ha una data dalla quale i dati storici sono disponibili
# gratuitamente in modo affidabile. Il signal_decay_scorer e il
# realtime_trigger_engine consultano questa mappa e applicano peso=0 quando
# signal_date < available_from. Così il backtest pre-data NON inquina con
# segnali "che dovrebbero esserci ma non ci sono".
#
# Nel periodo backtest che precede la data disponibile, lo score viene
# RIDISTRIBUITO sui segnali disponibili (rinormalizzazione pesi).
#
# In LIVE TRADING tutti i segnali sono a peso pieno.
# ═════════════════════════════════════════════════════════════════════════
SIGNAL_AVAILABLE_FROM: Dict[str, Optional[date]] = {
    # ── Sempre disponibili (no restriction) ──
    "radar_score":          date(2010, 1, 1),   # 13F via SEC archive paginato
    "accumulation":         date(2010, 1, 1),   # 13F → variazioni shares
    "crowding":             date(2010, 1, 1),   # derivato da 13F
    "momentum":             date(2010, 1, 1),   # prezzi yfinance
    "vix_regime":           date(2010, 1, 1),   # ^VIX yfinance
    "dividend_drag":        date(2010, 1, 1),   # yield static, conto
    "tlh_proactive":        date(2010, 1, 1),   # solo logica fiscale

    # ── Backtestabili dal 2014 (limit fetcher 13F attuale) ──
    "insider_flow":         date(2014, 1, 1),   # Form 4 SEC archive (parzial)
    "congressional":        date(2014, 1, 1),   # Capitol Trades archive

    # ── Disponibili dal 2021 in poi (FMP Free Tier 5 anni storico) ──
    "analyst_composite":    date(2021, 1, 1),   # FMP Historical Grades API
    "pead_surprise":        date(2021, 1, 1),   # earnings surprise via FMP/scrape

    # ── Disponibili dal 2024 (FINRA scraping + yfinance current) ──
    "short_squeeze":        date(2024, 1, 1),   # short interest storico FINRA

    # ── Forward-only (live trading) ──
    # nessun segnale forward-only puro per ora
}


def signal_is_available(signal_name: str, signal_date: date) -> bool:
    """True se il segnale è utilizzabile alla data corrente del backtest.
    Per LIVE TRADING (signal_date >= today), tutti i segnali sono available."""
    from_date = SIGNAL_AVAILABLE_FROM.get(signal_name)
    if from_date is None:
        return False
    return signal_date >= from_date


def renormalize_weights(weights_dict: Dict[str, float],
                        signal_date: date) -> Dict[str, float]:
    """
    Rinormalizza i pesi dei segnali in base alla data corrente.
    Segnali non ancora disponibili → peso 0.
    I pesi rimanenti vengono scalati proporzionalmente per sommare a 1.

    Esempio: in backtest 2018, analyst_composite (avail 2021) ha peso 0;
    i pesi di momentum/insider/congressional vengono rescalati per coprirlo.
    """
    available = {n: w for n, w in weights_dict.items()
                 if signal_is_available(n, signal_date)}
    total = sum(available.values())
    if total <= 0:
        return {n: 0.0 for n in weights_dict}
    return {n: (w / total if n in available else 0.0)
            for n, w in weights_dict.items()}

# ═════════════════════════════════════════════════════════════════════════
# DISCLAIMERS che vanno SEMPRE loggati nel report finale
# ═════════════════════════════════════════════════════════════════════════
DISCLAIMERS = {
    "survivorship_residual": (
        "Anche con filtro point-in-time, la lista 36 fondi è pre-selezionata "
        "sui 'vincitori storici'. Bias residuo stimato: +1-2pp CAGR."
    ),
    "analyst_data_coverage": (
        "Analyst data disponibile gratuitamente solo per gli ultimi ~5 anni "
        "(FMP Free Tier). Per backtest pre-2021 il segnale analyst è disabilitato."
    ),
    "short_interest_lag": (
        "Short interest da FINRA reports bi-mensili: lag tipico 5-9 giorni "
        "tra data riferimento e pubblicazione."
    ),
    "dividend_tax_scenario": (
        "Scenario fiscalità dividendi configurato via "
        "ASSUME_FOREIGN_TAX_CREDIT_RECOVERY. True = 26%, False = 37.1%."
    ),
}
