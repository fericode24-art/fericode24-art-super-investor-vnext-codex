"""Test Insider Quality Score — role, type, size, cluster."""
from scoring import insider_quality


def _txn(name, title, ttype, value, date):
    return {"insider_name": name, "title": title, "transaction_type": ttype,
            "value_usd": value, "trade_date": date, "filing_date": date}


def test_requires_two_distinct_insiders():
    """Un solo insider → score 0."""
    txns = [_txn("Alice", "CEO", "P-Purchase", 2_000_000, "2026-05-10")]
    res = insider_quality.compute_insider_quality_score("X", txns)
    assert res["score"] == 0


def test_excludes_non_purchase_transactions():
    """Award/sale non contano: solo P-Purchase."""
    txns = [_txn("Alice", "CEO", "A-Award", 5_000_000, "2026-05-10"),
            _txn("Bob", "CFO", "S-Sale", 5_000_000, "2026-05-11")]
    res = insider_quality.compute_insider_quality_score("X", txns)
    assert res["score"] == 0


def test_ceo_cfo_score_higher_than_directors():
    """Acquisti di CEO+CFO pesano più di 2 director generici."""
    big = [_txn("Alice", "CEO", "P-Purchase", 2_000_000, "2026-05-10"),
           _txn("Bob", "CFO", "P-Purchase", 1_500_000, "2026-05-11")]
    small = [_txn("Carl", "Dir", "P-Purchase", 30_000, "2026-05-10"),
             _txn("Dave", "Dir", "P-Purchase", 25_000, "2026-05-11")]
    s_big = insider_quality.compute_insider_quality_score("X", big)["score"]
    s_small = insider_quality.compute_insider_quality_score("Y", small)["score"]
    assert s_big > s_small


def test_cluster_freshness_boost():
    """Acquisti concentrati in pochi giorni → score più alto di acquisti sparsi."""
    tight = [_txn("Alice", "CEO", "P-Purchase", 2_000_000, "2026-05-10"),
             _txn("Bob", "CFO", "P-Purchase", 2_000_000, "2026-05-12")]
    spread = [_txn("Alice", "CEO", "P-Purchase", 2_000_000, "2026-03-01"),
              _txn("Bob", "CFO", "P-Purchase", 2_000_000, "2026-05-12")]
    s_tight = insider_quality.compute_insider_quality_score("X", tight)["score"]
    s_spread = insider_quality.compute_insider_quality_score("Y", spread)["score"]
    assert s_tight >= s_spread
