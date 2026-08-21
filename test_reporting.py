from datetime import datetime, timezone
import json
from reporting import TradeHistoryStore, TradeOutcomeRecord, TradingReportService

def record(trade_id, when, pnl, asset="BTCUSD", mode="MODERATE"):
    return TradeOutcomeRecord(trade_id=trade_id, source="PAPER", asset=asset, direction="BUY", mode=mode,
        entry_price=100, exit_price=100+pnl, entry_time_utc=when, exit_time_utc=when,
        realized_pnl=pnl, net_pnl=pnl, realized_pips=pnl, winning_trade=pnl > 0,
        losing_trade=pnl < 0, breakeven_trade=pnl == 0)

def test_jsonl_append_is_idempotent(tmp_path):
    store = TradeHistoryStore(tmp_path)
    item = record("t1", "2026-08-20T12:00:00+00:00", 5)
    assert store.append(item) is True
    assert store.append(item) is False
    assert len(store.records()) == 1
    assert json.loads((tmp_path / "trade_history" / "trades_2026.jsonl").read_text())['trade_id'] == "t1"

def test_period_reports_and_reconciliation(tmp_path):
    store = TradeHistoryStore(tmp_path)
    store.append(record("d1", "2026-08-20T12:00:00+00:00", 5))
    store.append(record("d2", "2026-08-21T12:00:00+00:00", -2, "XAUUSD", "AGGRESSIVE"))
    service = TradingReportService(store, tmp_path / "reports")
    daily = service.generate("daily", 2026, 8, 20)
    weekly = service.generate("weekly", 2026, week=34)
    monthly = service.generate("monthly", 2026, month=8)
    yearly = service.generate("yearly", 2026)
    assert daily["metrics"]["realized_pnl"] == 5
    assert weekly["metrics"]["realized_pnl"] == 3
    assert monthly["metrics"]["realized_pnl"] == 3
    assert yearly["metrics"]["realized_pnl"] == 3
    assert service.reconcile(weekly)["ok"]

def test_invalid_source_and_nonfinite_values_are_rejected(tmp_path):
    try:
        TradeOutcomeRecord("t", "UNKNOWN", "BTCUSD", "BUY")
        assert False
    except ValueError:
        pass
    store = TradeHistoryStore(tmp_path)
    item = record("t2", "2026-01-01T00:00:00+00:00", float("nan"))
    store.append(item)
    assert "NaN" not in (tmp_path / "trade_history" / "trades_2026.jsonl").read_text()
