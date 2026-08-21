from pathlib import Path

import pytest

from signal_approval import SignalApprovalService


class Candidate:
    asset = "XAUUSD"
    direction = "SELL"
    mode = "MODERATE"
    entry = 4500.0
    stop_loss = 4505.0
    take_profit = 4490.0
    risk_reward = 2.0
    confidence = 0.91
    signal_score = 88.4


def service(tmp_path, ttl=300):
    return SignalApprovalService(str(tmp_path / "pending.json"), ttl_seconds=ttl, archive_directory=str(tmp_path / "approvals"), allowed_chat_id="chat", allowed_user_ids=["user"])


def test_approval_persists_and_approve_is_idempotent(tmp_path):
    s = service(tmp_path)
    record = s.create(Candidate(), 4500.0, now=1000)
    approved = s.decide(record["approval_id"], "APPROVE", now=1001, chat_id="chat", user_id="user")
    assert approved["status"] == "APPROVED"
    assert s.decide(record["approval_id"], "CANCEL", now=1002, chat_id="chat", user_id="user")["status"] == "APPROVED"
    assert SignalApprovalService(str(tmp_path / "pending.json"), archive_directory=str(tmp_path / "approvals")).records[record["approval_id"]]["status"] == "APPROVED"


def test_cancel_and_expiry_are_terminal(tmp_path):
    s = service(tmp_path, ttl=5)
    cancelled = s.create(Candidate(), 4500.0, now=1000)
    assert s.decide(cancelled["approval_id"], "CANCEL", now=1001, chat_id="chat", user_id="user")["status"] == "CANCELLED"
    expired = s.create(Candidate(), 4500.0, now=1000)
    assert s.expire(now=1005)[0]["status"] == "EXPIRED"
    assert s.decide(expired["approval_id"], "APPROVE", now=1006, chat_id="chat", user_id="user")["status"] == "EXPIRED"


def test_unauthorized_callback_is_rejected(tmp_path):
    s = service(tmp_path)
    record = s.create(Candidate(), 4500.0, now=1000)
    with pytest.raises(PermissionError):
        s.decide(record["approval_id"], "APPROVE", now=1001, chat_id="other", user_id="user")


def test_approval_archive_is_idempotent(tmp_path):
    s = service(tmp_path)
    record = s.create(Candidate(), 4500.0, now=1000)
    s.decide(record["approval_id"], "CANCEL", now=1001, chat_id="chat", user_id="user")
    s.decide(record["approval_id"], "CANCEL", now=1002, chat_id="chat", user_id="user")
    lines = (Path(tmp_path) / "approvals" / "approvals_2026.jsonl").read_text().splitlines()
    assert len(lines) == 1


def test_mark_paper_opened_is_idempotent(tmp_path):
    s = service(tmp_path)
    record = s.create(Candidate(), 4500.0, now=1000)
    s.decide(record["approval_id"], "APPROVE", now=1001, chat_id="chat", user_id="user")
    assert s.approved()
    s.mark_paper_opened(record["approval_id"], "trade-1")
    assert s.approved() == []
    assert s.records[record["approval_id"]]["paper_trade_id"] == "trade-1"