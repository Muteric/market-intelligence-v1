"""CLI for persisted trading reports."""
from __future__ import annotations
import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from reporting import TradeHistoryStore, TradingReportService

def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--daily", metavar="YYYY-MM-DD")
    group.add_argument("--weekly", metavar="YYYY-Www")
    group.add_argument("--monthly", metavar="YYYY-MM")
    group.add_argument("--yearly", metavar="YYYY")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--send-telegram", action="store_true")
    args = parser.parse_args()
    service = TradingReportService(TradeHistoryStore())
    if args.daily:
        date = datetime.strptime(args.daily, "%Y-%m-%d"); report = service.generate("daily", date.year, date.month, date.day, args.force)
    elif args.weekly:
        year, raw = args.weekly.split("-W"); report = service.generate("weekly", int(year), week=int(raw), force=args.force)
    elif args.monthly:
        year, month = args.monthly.split("-"); report = service.generate("monthly", int(year), month=int(month), force=args.force)
    else:
        report = service.generate("yearly", int(args.yearly), force=args.force)
    if args.send_telegram:
        token = os.getenv("TELEGRAM_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if token and chat_id and not report.get("telegram_sent"):
            metrics = report["metrics"]
            win_rate = "N/A" if metrics.get("win_rate") is None else f"{metrics['win_rate']:.1%}"
            text = (f"{report['period'].upper()} TRADING REPORT\n🧪 PAPER TRADING\n\n"
                    f"If you invested $100, simulated net PnL would be ${metrics['realized_pnl']:.2f}.\n\n"
                    f"Trades: {metrics['trades']}\nWins: {metrics['wins']}\nLosses: {metrics['losses']}\n"
                    f"Win rate: {win_rate}\nProfit factor: {metrics.get('profit_factor') or 'N/A'}")
            body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
            request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    report["telegram_sent"] = 200 <= response.status < 300
            except Exception:
                report["telegram_sent"] = False
            report["telegram_attempts"] = int(report.get("telegram_attempts", 0)) + 1
            report["last_telegram_status"] = "SENT" if report["telegram_sent"] else "FAILED"
            start = datetime.fromisoformat(report["start_utc"])
            if report["period"] == "daily":
                path = service._period("daily", start.year, start.month, start.day)[2]
            elif report["period"] == "weekly":
                path = service._period("weekly", start.isocalendar().year, week=start.isocalendar().week)[2]
            elif report["period"] == "monthly":
                path = service._period("monthly", start.year, start.month)[2]
            else:
                path = service._period("yearly", start.year)[2]
            path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
