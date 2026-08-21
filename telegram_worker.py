"""Long-polling Telegram callback worker for paper approvals.

Run this on the desktop/VPS runtime, not in a short-lived GitHub Actions job.
It never calls MT5 execution APIs.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any

from signal_approval import SignalApprovalService


class TelegramApprovalWorker:
    def __init__(self, service: SignalApprovalService | None = None, token: str | None = None,
                 poll_timeout: int = 25, poll_interval: float = 1.0, offset_file: str = "data/telegram_update_offset.json"):
        self.service = service or SignalApprovalService()
        self.token = token or os.getenv("TELEGRAM_TOKEN", "")
        self.poll_timeout = int(poll_timeout)
        self.poll_interval = float(poll_interval)
        self.offset_path = offset_file
        self.offset = self._load_offset()

    def _load_offset(self) -> int | None:
        try:
            with open(self.offset_path, encoding="utf-8") as handle:
                return int(json.load(handle).get("last_update_id", 0)) or None
        except (OSError, ValueError, TypeError):
            return None

    def _save_offset(self) -> None:
        directory = os.path.dirname(self.offset_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temporary = self.offset_path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump({"last_update_id": self.offset}, handle)
        os.replace(temporary, self.offset_path)

    def _call(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.token:
            raise RuntimeError("TELEGRAM_TOKEN is not configured")
        encoded = urllib.parse.urlencode(payload or {}).encode()
        request = urllib.request.Request(f"https://api.telegram.org/bot{self.token}/{method}", data=encoded, method="POST")
        with urllib.request.urlopen(request, timeout=self.poll_timeout + 10) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok"):
            raise RuntimeError("Telegram API request failed")
        return result

    def check(self) -> bool:
        result = self._call("getMe", {})
        return bool(result.get("ok"))

    def process_update(self, update: dict[str, Any]) -> bool:
        callback = update.get("callback_query") or {}
        data = str(callback.get("data", ""))
        if ":" not in data:
            return False
        action, approval_id = data.split(":", 1)
        action = action.upper()
        if action not in {"APPROVE", "CANCEL"}:
            return False
        message = callback.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        user_id = (callback.get("from") or {}).get("id")
        try:
            record = self.service.decide(approval_id, action, chat_id=chat_id, user_id=user_id)
            status = record.get("status")
            text = "✅ SIGNAL APPROVED\nPaper position may be opened on the next validated cycle." if status == "APPROVED" else "❌ SIGNAL CANCELLED\nNo trade opened."
            if status == "EXPIRED":
                text = "⌛ SIGNAL EXPIRED\nNo trade opened."
            if callback.get("id"):
                self._call("answerCallbackQuery", {"callback_query_id": callback["id"], "text": status})
            self.service.send_text(text)
            return True
        except PermissionError:
            if callback.get("id"):
                self._call("answerCallbackQuery", {"callback_query_id": callback["id"], "text": "Unauthorized"})
            return False
        except (KeyError, ValueError):
            if callback.get("id"):
                self._call("answerCallbackQuery", {"callback_query_id": callback["id"], "text": "Signal unavailable"})
            return False

    def poll_once(self) -> int:
        payload = {"timeout": self.poll_timeout, "allowed_updates": json.dumps(["callback_query"])}
        if self.offset is not None:
            payload["offset"] = self.offset
        result = self._call("getUpdates", payload)
        updates = result.get("result", [])
        for update in updates:
            self.offset = int(update.get("update_id", 0)) + 1
            self.process_update(update)
            self._save_offset()
        expired = self.service.expire()
        for record in expired:
            self.service.send_text(f"⌛ SIGNAL EXPIRED\n{record.get('asset')} {record.get('direction')}\nNo trade opened.")
        return len(updates)

    def run_forever(self) -> None:
        while True:
            try:
                self.poll_once()
            except KeyboardInterrupt:
                raise
            except Exception:
                time.sleep(self.poll_interval)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    worker = TelegramApprovalWorker()
    if args.check:
        print("Telegram approval worker: CONFIGURED" if worker.token else "Telegram approval worker: NOT CONFIGURED")
        return 0 if worker.token else 1
    worker.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())