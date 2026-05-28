"""
v2.4.1 — Beta Score (modalità ROTATION_BETA).

NON è "più volatile = meglio". Il punteggio premia una REATTIVITA' SANA:
  - beta vs SPY / QQQ → curva a campana, picco ~1,15 (partecipa al mercato
    senza esagerare); penalizza sia i titoli troppo piatti (<0,8) sia quelli
    pericolosamente nervosi (>1,7), con discesa più ripida sul lato del rischio
  - upside capture ratio → piccolo bonus se cattura bene i rialzi
  - volatilità realizzata → penalità se molto sopra la mediana dell'universo

Score 0-100: 100 ≈ beta sana ~1,1 che cattura bene i rialzi; valori bassi sia
per titoli addormentati sia per titoli iper-volatili.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from .cfg import clip


def _daily_returns(close: pd.Series) -> np.ndarray:
    """Rendimenti giornalieri da una serie di prezzi."""
    r = close.pct_change().dropna()
    return r.to_numpy()


def linreg_beta(stock_close: pd.Series, market_close: pd.Series) -> float:
    """Beta = covarianza(stock, market) / varianza(market) sui rendimenti giornalieri."""
    # allinea le due serie sulle date comuni
    df = pd.DataFrame({"s": stock_close, "m": market_close}).dropna()
    if len(df) < 30:
        return 1.0
    rs = df["s"].pct_change().dropna().to_numpy()
    rm = df["m"].pct_change().dropna().to_numpy()
    n = min(len(rs), len(rm))
    rs, rm = rs[-n:], rm[-n:]
    var_m = np.var(rm)
    if var_m == 0:
        return 1.0
    return float(np.cov(rs, rm)[0][1] / var_m)


def upside_capture(stock_close: pd.Series, market_close: pd.Series, days: int = 90) -> float:
    """
    Upside capture: nei giorni in cui il mercato sale, quanto sale in media il
    titolo rispetto al mercato. 100 = cattura uguale, >100 = amplifica.
    """
    df = pd.DataFrame({"s": stock_close, "m": market_close}).dropna().tail(days + 1)
    if len(df) < 20:
        return 100.0
    rs = df["s"].pct_change().dropna()
    rm = df["m"].pct_change().dropna()
    up_days = rm > 0
    if up_days.sum() < 5:
        return 100.0
    mkt_up = rm[up_days].mean()
    stk_up = rs[up_days].mean()
    if mkt_up == 0:
        return 100.0
    return float(clip((stk_up / mkt_up) * 100, 0, 150))


def annualized_vol(stock_close: pd.Series, days: int = 60) -> float:
    """Volatilità annualizzata dei rendimenti giornalieri."""
    r = stock_close.pct_change().dropna().tail(days)
    if len(r) < 10:
        return 0.0
    return float(r.std() * np.sqrt(252))


def _beta_fit(beta: float) -> float:
    """Punteggio 0-100 a CAMPANA: premia una beta sana, non una beta alta.
    Picco ~1,15 (il titolo partecipa ai movimenti del mercato senza esagerare).
    Penalizza i titoli troppo addormentati e quelli iper-volatili; la discesa è
    più ripida sul lato alto perché lì c'è il rischio vero.
    Esempi: 0,7→~76  1,0→~97  1,15→100  1,5→~82  1,8→~46  2,2→~14  2,6→~2."""
    center = 1.15
    spread = 0.85 if beta <= center else 0.70   # lato alto = più severo (rischio)
    return float(clip(100.0 * np.exp(-((beta - center) / spread) ** 2), 0, 100))


def compute_beta_score(
    stock_close: pd.Series,
    spy_close: pd.Series,
    qqq_close: pd.Series,
    universe_vol_median: float,
    cfg: dict,
) -> dict:
    """
    Beta Score 0-100 — reattività SANA, non aggressività.
    Ritorna {score, beta_spy, beta_qqq, upside_capture, annualized_vol}.
    """
    bs_cfg = cfg["rotation_beta"]["beta_score"]
    beta_spy = linreg_beta(stock_close, spy_close)
    beta_qqq = linreg_beta(stock_close, qqq_close)
    up_cap = upside_capture(stock_close, spy_close, bs_cfg["upside_capture_days"])
    vol = annualized_vol(stock_close, bs_cfg["vol_days"])

    # nucleo: beta a campana (salute della reattività, non sua intensità)
    fit = 0.65 * _beta_fit(beta_spy) + 0.35 * _beta_fit(beta_qqq)

    # bonus: cattura bene i rialzi del mercato (0 → +10)
    upside_bonus = clip((up_cap - 100.0) * 0.25, 0, 10)

    # penalità: volatilità molto sopra la mediana dell'universo (0 → -20)
    vol_penalty = 0.0
    if universe_vol_median:
        ratio = vol / universe_vol_median
        vol_penalty = clip((ratio - 1.4) * 25.0, 0, 20)

    score = clip(fit + upside_bonus - vol_penalty, 0, 100)
    return {
        "score": round(score, 2),
        "beta_spy": round(beta_spy, 2),
        "beta_qqq": round(beta_qqq, 2),
        "upside_capture": round(up_cap, 1),
        "annualized_vol": round(vol, 3),
    }
