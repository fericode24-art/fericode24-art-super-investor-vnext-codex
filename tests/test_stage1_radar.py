"""Test Stage 1 — conviction, accumulation, freshness decay, skill multiplier."""
from scoring import stage1_radar


def test_fund_effective_weight_type_multiplier():
    """value_legend deve pesare più di tiger_cub a parità di base_weight."""
    legend = {"base_weight": 1.0, "type": "value_legend"}
    cub = {"base_weight": 1.0, "type": "tiger_cub"}
    assert stage1_radar.fund_effective_weight(legend) > stage1_radar.fund_effective_weight(cub)


def test_fund_effective_weight_skill_multiplier():
    """Il recent_skill_mult deve scalare il peso."""
    base = {"base_weight": 1.0, "type": "value_legend"}
    hot = {"base_weight": 1.0, "type": "value_legend", "recent_skill_mult": 1.8}
    assert stage1_radar.fund_effective_weight(hot) > stage1_radar.fund_effective_weight(base)


def test_freshness_decay_monotonic():
    """Decay: un filing più vecchio deve pesare meno."""
    recent = stage1_radar.decay_factor("2026-05-01", 60)
    old = stage1_radar.decay_factor("2025-05-01", 60)
    assert 0 < old < recent <= 1.0


def test_conviction_requires_two_high_conviction_holders(holdings_by_fund, funds):
    """CCC è high-conviction per 1 solo fondo → escluso. AAA da 2 → incluso."""
    conv = stage1_radar.compute_conviction(holdings_by_fund, funds)
    assert "AAA" in conv
    assert "CCC" not in conv


def test_accumulation_detects_increase(holdings_by_fund, funds):
    """AAA cresce QoQ in entrambi i fondi → accumulation alta; BBB stabile → bassa."""
    accum = stage1_radar.compute_accumulation(holdings_by_fund, funds)
    assert accum.get("AAA", 0) > accum.get("BBB", 0)


def test_skill_multiplier_fallback_for_new_fund(holdings_by_fund, funds, momentum):
    """Il fondo nuovo (1 quarter) deve ricevere skill mult neutro 1.0."""
    mults = stage1_radar.compute_skill_multipliers(funds, holdings_by_fund, momentum)
    assert mults["0000000003"] == 1.0       # New Fund, quarters_available=1


def test_radar_score_combines_components(holdings_by_fund, funds):
    """Il radar score deve essere calcolato e nel range [0,130]."""
    insider = {"AAA": 50.0, "BBB": 20.0}
    radar = stage1_radar.calculate_radar_scores(holdings_by_fund, funds, insider)
    assert "AAA" in radar
    assert 0 <= radar["AAA"]["radar"] <= 130
