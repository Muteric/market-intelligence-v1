"""Durable Telegram approval state for simulation-only trade candidates."""
from __future__ import annotations

import json
import os
import time
import uuid
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class SignalApprovalService:
    """Persist approval decisions; approved records only authorize paper entry."""

    def __init__(self, state_file: str = "data/pending_signal_approvals.json", ttl_seconds: int = 300,
                 archive_directory: str = "data/approvals", allowed_chat_id: Optional[str] = None,
                 allowed_user_ids: Optional[list[str]] = None):
        self.path = Path(state_file)
        self.ttl_seconds = int(ttl_seconds)
        self.archive_directory = Path(archive_directory)
        self.allowed_chat_id = str(allowed_chat_id or os.getenv("TELEGRAM_CHAT_ID", "")).strip()
        raw_users = allowed_user_ids if allowed_user_ids is not None else os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").split(",")
        self.allowed_user_ids = {str(value).strip() for value in raw_users if str(value).strip()}
        self.records = self._load()

    @staticmethod
    def _utc(timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.records, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def _archive(self, record: dict[str, Any]) -> None:
        if record.get("status") not in {"APPROVED", "CANCELLED", "EXPIRED", "APPROVED_BUT_INVALIDATED"}:
            return
        self.archive_directory.mkdir(parents=True, exist_ok=True)
        year = datetime.now(timezone.utc).year
        path = self.archive_directory / f"approvals_{year}.jsonl"
        existing = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    existing.add(json.loads(line).get("approval_id"))
                except ValueError:
                    continue
        if record.get("approval_id") not in existing:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")

    def has_equivalent(self, candidate: Any) -> bool:
        now = time.time()
        return any(record.get("status") == "AWAITING_APPROVAL" and float(record.get("expires_at", 0)) > now and record.get("asset") == candidate.asset and record.get("direction") == candidate.direction and record.get("mode") == candidate.mode and record.get("entry") == candidate.entry for record in self.records.values())

    def create(self, candidate: Any, current_price: float, now: Optional[float] = None,
               candidate_id: Optional[str] = None, ttl_seconds: Optional[int] = None) -> dict[str, Any]:
        now = time.time() if now is None else float(now)
        approval_id = uuid.uuid4().hex[:16]
        candidate_id = candidate_id or str(getattr(candidate, "candidate_id", "") or approval_id)
        ttl = self.ttl_seconds if ttl_seconds is None else int(ttl_seconds)
        record = {
            "approval_id": approval_id,
            "signal_id": approval_id,
            "candidate_id": candidate_id,
            "asset": str(candidate.asset),
            "direction": str(candidate.direction),
            "mode": str(candidate.mode),
            "entry": candidate.entry,
            "stop_loss": candidate.stop_loss,
            "take_profit": candidate.take_profit,
            "risk_reward": candidate.risk_reward,
            "confidence": candidate.confidence,
            "score": candidate.signal_score,
            "created_at": now,
            "created_at_utc": self._utc(now),
            "expires_at": now + ttl,
            "valid_until_utc": self._utc(now + ttl),
            "status": "AWAITING_APPROVAL",
            "decision": "NONE",
            "decision_at_utc": None,
            "telegram_message_id": None,
            "telegram_chat_id": self.allowed_chat_id or None,
            "approved_by": None,
            "current_price_at_creation": current_price,
        }
        self.records[approval_id] = record
        self._save()
        return record

    def pending(self) -> list[dict[str, Any]]:
        self.expire()
        return [record for record in self.records.values() if record.get("status") == "AWAITING_APPROVAL"]

    def expire(self, now: Optional[float] = None) -> list[dict[str, Any]]:
        now = time.time() if now is None else float(now)
        expired = []
        for record in self.records.values():
            if record.get("status") == "AWAITING_APPROVAL" and float(record.get("expires_at", 0)) <= now:
                record.update({"status": "EXPIRED", "decision": "EXPIRED", "decision_at_utc": self._utc(now)})
                self._archive(record)
                expired.append(record)
        if expired:
            self._save()
        return expired

    def _authorized(self, chat_id: Any = None, user_id: Any = None) -> bool:
        if self.allowed_chat_id and str(chat_id or "") != self.allowed_chat_id:
            return False
        if self.allowed_user_ids and str(user_id or "") not in self.allowed_user_ids:
            return False
        return True

    def decide(self, approval_id: str, action: str, now: Optional[float] = None,
               chat_id: Any = None, user_id: Any = None) -> dict[str, Any]:
        now = time.time() if now is None else float(now)
        self.expire(now)
        record = self.records.get(approval_id)
        if record is None:
            raise KeyError("approval not found")
        if not self._authorized(chat_id, user_id):
            raise PermissionError("unauthorized Telegram approval source")
        if record.get("status") != "AWAITING_APPROVAL":
            return record
        action = str(action).upper()
        if action not in {"APPROVE", "CANCEL"}:
            raise ValueError("action must be APPROVE or CANCEL")
        status = "APPROVED" if action == "APPROVE" else "CANCELLED"
        record.update({"status": status, "decision": status, "decision_at_utc": self._utc(now), "approved_by": str(user_id) if user_id else None})
        self._archive(record)
        self._save()
        return record

    def approved(self) -> list[dict[str, Any]]:
        return [record for record in self.records.values() if record.get("status") == "APPROVED" and not record.get("paper_opened")]

    def mark_paper_opened(self, approval_id: str, trade_id: str) -> Optional[dict[str, Any]]:
        record = self.records.get(approval_id)
        if record is None:
            return None
        record["paper_opened"] = True
        record["paper_trade_id"] = trade_id
        record["paper_opened_at_utc"] = self._utc(time.time())
        self._save()
        return record

    def mark_invalidated(self, approval_id: str, reason: str = "ENTRY_INVALIDATED") -> Optional[dict[str, Any]]:
        record = self.records.get(approval_id)
        if record is None:
            return None
        record.update({"status": "APPROVED_BUT_INVALIDATED", "decision": "APPROVED_BUT_INVALIDATED", "invalidated_reason": reason, "decision_at_utc": self._utc(time.time())})
        self._archive(record)
        self._save()
        return record

    def send_prompt(self, record: dict[str, Any], token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
        token = token or os.getenv("TELEGRAM_TOKEN", "")
        chat_id = chat_id or self.allowed_chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return False
        text = (f"🚨 TRADE OPPORTUNITY FOUND\n\n{record['asset']} {record['direction']}\n"
                f"Mode: {record['mode']}\nConfidence: {float(record['confidence']):.0%}\nScore: {float(record['score']):.1f}\n"
                f"Entry: {record['entry']}\nSL: {record['stop_loss']}\nTP: {record['take_profit']}\n"
                f"R:R: {record['risk_reward']}\nValid Until: {record['valid_until_utc']}\n\n🧪 PAPER TRADING")
        markup = {"inline_keyboard": [[
            {"text": "✅ APPROVE PAPER", "callback_data": f"approve:{record['approval_id']}"},
            {"text": "❌ CANCEL", "callback_data": f"cancel:{record['approval_id']}"},
        ]]}
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "reply_markup": json.dumps(markup)}).encode()
        request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if 200 <= response.status < 300:
                    payload = json.loads(response.read().decode("utf-8"))
                    message = payload.get("result", {}) if isinstance(payload, dict) else {}
                    record["telegram_message_id"] = message.get("message_id")
                    record["telegram_chat_id"] = chat_id
                    self._save()
                    return True
        except Exception:
            return False
        return False

    def send_text(self, text: str, token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
        token = token or os.getenv("TELEGRAM_TOKEN", "")
        chat_id = chat_id or self.allowed_chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return False
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return 200 <= response.status < 300
        except Exception:
            return False