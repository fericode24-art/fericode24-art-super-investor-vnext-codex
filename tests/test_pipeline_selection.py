"""Test selezione rotazionale v2.5 — bacino qualità, health-sell,
sostituzione del più debole, cash fallback, equal-weight."""
import pipeline


def _stock(ticker, sector, opp, radar=None, entry="NEUTRAL", momentum=50, conf=70):
    return {
        "ticker": ticker, "sector": sector,
        "opportunity_score": opp,
        "radar_score": radar if radar is not None else opp,
        "entry_status": entry,
        "confidence_score": conf,
        "components": {"momentum": momentum},
    }


# ─────────────────────── Bootstrap (nessun incumbent) ───────────────────────
def test_bootstrap_only_buy_signals_enter():
    """Bootstrap: entrano solo FRESH/PULLBACK, neutro ed esteso restano fuori."""
    scored = [
        _stock("AAA", "Tech", 90, entry="FRESH_BREAKOUT"),
        _stock("BBB", "Energy", 85, entry="NEUTRAL"),
        _stock("CCC", "Health", 80, entry="PULLBACK_IN_TREND"),
        _stock("DDD", "Fin", 75, entry="EXTENDED"),
    ]
    portfolio, n_valid = pipeline.select_portfolio_rotational(scored, 12, [])
    tickers = {s["ticker"] for s in portfolio if not s.get("is_cash")}
    assert tickers == {"AAA", "CCC"}
    assert n_valid == 2
    assert sum(1 for s in portfolio if s.get("is_cash")) == 10
    assert len(portfolio) == 12


def test_loose_gate_admits_neutral_and_extended():
    """Gate v2.6 (produzione): con buy_states ampio entrano anche NEUTRAL ed
    EXTENDED; solo BROKEN/AVOID restano fuori."""
    scored = [
        _stock("AAA", "Tech", 90, entry="NEUTRAL"),
        _stock("BBB", "Energy", 85, entry="EXTENDED"),
        _stock("CCC", "Health", 80, entry="BROKEN"),
    ]
    gate = ["FRESH_BREAKOUT", "PULLBACK_IN_TREND", "NEUTRAL", "CONSOLIDATION", "EXTENDED"]
    portfolio, n_valid = pipeline.select_portfolio_rotational(
        scored, 12, [], buy_states=gate)
    tickers = {s["ticker"] for s in portfolio if not s.get("is_cash")}
    assert "AAA" in tickers       # NEUTRAL ammesso
    assert "BBB" in tickers       # EXTENDED ammesso
    assert "CCC" not in tickers   # BROKEN resta escluso
    assert n_valid == 2


def test_sector_cap_in_rotational():
    """Il cap settoriale (letto da config) è rispettato nella selezione."""
    cap = pipeline.load_config()["filters"]["sector_cap"]
    scored = [_stock(f"T{i}", "Technology", 95 - i, entry="FRESH_BREAKOUT")
              for i in range(12)]
    portfolio, _ = pipeline.select_portfolio_rotational(scored, 12, [])
    tech = [s for s in portfolio if s.get("sector") == "Technology"]
    assert len(tech) <= cap


# ─────────────────────────── Health-sell ───────────────────────────────────
def test_incumbent_neutral_survives():
    """Un incumbent con segnale neutro resta: non è challenger ma sopravvive."""
    scored = [_stock("INC", "Tech", 70, entry="NEUTRAL")]
    portfolio, _ = pipeline.select_portfolio_rotational(scored, 12, ["INC"])
    assert "INC" in {s["ticker"] for s in portfolio if not s.get("is_cash")}


def test_incumbent_broken_is_health_sold():
    """Un incumbent con trend rotto viene venduto (vendita di salute)."""
    scored = [_stock("INC", "Tech", 70, entry="BROKEN"),
              _stock("NEW", "Energy", 65, entry="FRESH_BREAKOUT")]
    portfolio, _ = pipeline.select_portfolio_rotational(scored, 12, ["INC"])
    tickers = {s["ticker"] for s in portfolio if not s.get("is_cash")}
    assert "INC" not in tickers
    assert "NEW" in tickers


def test_incumbent_out_of_bacino_is_sold():
    """Incumbent caduto fuori dal bacino qualità → venduto."""
    scored = [_stock("A", "S1", 90, entry="NEUTRAL"),
              _stock("B", "S2", 88, entry="NEUTRAL"),
              _stock("C", "S3", 86, entry="NEUTRAL"),
              _stock("INC", "S4", 50, entry="NEUTRAL")]
    portfolio, _ = pipeline.select_portfolio_rotational(
        scored, 12, ["INC"], bacino_size=3)
    assert "INC" not in {s["ticker"] for s in portfolio if not s.get("is_cash")}


# ─────────────────────────── Sostituzione ──────────────────────────────────
def test_substitution_swaps_weakest_when_clearly_stronger():
    """Portafoglio pieno: un challenger nettamente più forte scalza il più debole."""
    scored = [_stock(f"I{i}", f"S{i}", 60, radar=50, entry="NEUTRAL")
              for i in range(12)]
    scored.append(_stock("CH", "SX", 95, radar=90, entry="FRESH_BREAKOUT"))
    prev = [f"I{i}" for i in range(12)]
    portfolio, _ = pipeline.select_portfolio_rotational(scored, 12, prev, margin=7)
    tickers = {s["ticker"] for s in portfolio if not s.get("is_cash")}
    assert "CH" in tickers
    assert len(tickers) == 12


def test_no_substitution_when_margin_not_met():
    """Challenger solo di poco più forte → niente swap (anti-churn)."""
    scored = [_stock(f"I{i}", f"S{i}", 60, radar=70, entry="NEUTRAL")
              for i in range(12)]
    scored.append(_stock("CH", "SX", 75, radar=73, entry="FRESH_BREAKOUT"))
    prev = [f"I{i}" for i in range(12)]
    portfolio, _ = pipeline.select_portfolio_rotational(scored, 12, prev, margin=7)
    assert "CH" not in {s["ticker"] for s in portfolio if not s.get("is_cash")}


def test_extended_winner_not_swapped_out():
    """Un vincente esteso (momentum alto) NON è il più debole → resta protetto."""
    winner = _stock("WIN", "S0", 70, radar=65, entry="EXTENDED", momentum=95)
    weak = _stock("WEAK", "S1", 68, radar=55, entry="NEUTRAL", momentum=40)
    others = [_stock(f"I{i}", f"S{i+2}", 66, radar=60, entry="NEUTRAL", momentum=60)
              for i in range(10)]
    challenger = _stock("CH", "SX", 90, radar=80, entry="FRESH_BREAKOUT", momentum=80)
    scored = [winner, weak] + others + [challenger]
    prev = ["WIN", "WEAK"] + [f"I{i}" for i in range(10)]
    portfolio, _ = pipeline.select_portfolio_rotational(scored, 12, prev, margin=7)
    tickers = {s["ticker"] for s in portfolio if not s.get("is_cash")}
    assert "CH" in tickers       # il challenger forte entra
    assert "WEAK" not in tickers  # ha scalzato il più debole
    assert "WIN" in tickers      # il vincente esteso è protetto


def test_hold_score_rewards_conviction_and_trend():
    """hold_score: 85% convinzione + 15% trend; il trend non penalizza i vincenti."""
    extended = _stock("E", "S", 70, radar=65, entry="EXTENDED", momentum=95)
    fading = _stock("F", "S", 70, radar=65, entry="NEUTRAL", momentum=30)
    assert pipeline._hold_score(extended) > pipeline._hold_score(fading)


# ─────────────────────────── Cash fallback ─────────────────────────────────
def test_cash_fallback_when_few_buy_signals():
    """Pochi segnali buy → slot CASH a riempire fino a 12."""
    scored = [_stock("AAA", "Tech", 80, entry="FRESH_BREAKOUT"),
              _stock("BBB", "Energy", 70, entry="PULLBACK_IN_TREND")]
    portfolio, n_valid = pipeline.select_portfolio_rotational(scored, 12, [])
    cash = [s for s in portfolio if s.get("is_cash")]
    assert n_valid == 2
    assert len(cash) == 10
    assert len(portfolio) == 12


# ─────────────────────────── Equal-weight v2.4 ─────────────────────────────
def test_equal_weight_v24():
    """v2.4 — sizing equal-weight: niente tier, weight_pct e size_band assegnati."""
    portfolio = [_stock(f"T{i}", "Sec", 90 - i) for i in range(12)]
    weighted = pipeline.assign_weights_v24(portfolio, target_size=12)
    assert all("weight_pct" in s for s in weighted)
    assert all("size_band" in s for s in weighted)
    assert all("tier" not in s for s in weighted)
    assert weighted[0]["rank"] == 1 and weighted[11]["rank"] == 12


def test_equal_weight_confidence_band():
    """Confidence alta → size_band 'full'; bassa → 'reduced'."""
    hi = pipeline.assign_weights_v24([_stock("A", "S", 80, conf=90)], 12)[0]
    lo = pipeline.assign_weights_v24([_stock("B", "S", 80, conf=40)], 12)[0]
    assert hi["size_band"] == "full"
    assert lo["size_band"] == "reduced"
    assert hi["weight_pct"] >= lo["weight_pct"]
