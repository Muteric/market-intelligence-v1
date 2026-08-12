"""Objective OHLC chart-pattern and market-structure evidence.

The detector is deliberately conservative: a pattern is evidence only.  It
does not place trades or override the existing decision engine.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class PatternEvidence:
    pattern_name: str
    timeframe: str
    direction: str
    confidence: float
    start_time: Any
    end_time: Any
    price_level: Optional[float]
    confirmation_status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ChartPatternDetector:
    """Detect conservative candlestick and basic market-structure evidence."""

    def detect(self, candles: List[Dict[str, Any]], timeframe: str) -> List[PatternEvidence]:
        rows = self._valid_candles(candles)
        if not rows:
            return []
        patterns: List[PatternEvidence] = []
        if len(rows) >= 2:
            patterns.extend(self._last_two_patterns(rows, timeframe))
        if len(rows) >= 3:
            patterns.extend(self._three_candle_patterns(rows, timeframe))
        patterns.extend(self._structure_patterns(rows, timeframe))
        return patterns

    detect_patterns = detect

    def analyze(self, candles: List[Dict[str, Any]], timeframe: str) -> Dict[str, Any]:
        rows = self._valid_candles(candles)
        patterns = self.detect(rows, timeframe)
        structure = self.market_structure(rows, timeframe)
        return {
            "timeframe": timeframe,
            "patterns": [pattern.to_dict() for pattern in patterns],
            "market_structure": structure,
            "support": structure.get("support", []),
            "resistance": structure.get("resistance", []),
        }

    def market_structure(self, candles: List[Dict[str, Any]], timeframe: str = "") -> Dict[str, Any]:
        rows = self._valid_candles(candles)
        if len(rows) < 4:
            return {"labels": [], "overall": "neutral", "support": [], "resistance": [], "breakout": False, "retest": False}
        closes = [row["close"] for row in rows]
        highs = [row["high"] for row in rows]
        lows = [row["low"] for row in rows]
        labels: List[str] = []
        if closes[-1] > closes[-2] and lows[-1] >= lows[-2]:
            labels.extend(["HH", "HL"])
            overall = "bullish"
        elif closes[-1] < closes[-2] and highs[-1] <= highs[-2]:
            labels.extend(["LH", "LL"])
            overall = "bearish"
        else:
            overall = "neutral"
        resistance = [max(highs[-min(20, len(highs)):])]
        support = [min(lows[-min(20, len(lows)):])]
        prior_range_high = max(highs[-4:-1])
        prior_range_low = min(lows[-4:-1])
        breakout = closes[-1] > prior_range_high or closes[-1] < prior_range_low
        if breakout:
            labels.append("BOS")
        if len(closes) >= 4:
            prior_direction = closes[-3] - closes[-4]
            current_direction = closes[-1] - closes[-2]
            if prior_direction * current_direction < 0:
                labels.append("CHoCH")
        return {
            "labels": labels,
            "overall": overall,
            "support": support,
            "resistance": resistance,
            "breakout": breakout,
            "retest": False,
        }

    def _last_two_patterns(self, rows: List[Dict[str, Any]], timeframe: str) -> List[PatternEvidence]:
        previous, current = rows[-2], rows[-1]
        result: List[PatternEvidence] = []
        po, pc = previous["open"], previous["close"]
        co, cc = current["open"], current["close"]
        if pc < po and cc > co and co <= pc and cc >= po:
            result.append(self._evidence("Bullish Engulfing", timeframe, "bullish", rows[-2:], 0.82, current["close"]))
        elif pc > po and cc < co and co >= pc and cc <= po:
            result.append(self._evidence("Bearish Engulfing", timeframe, "bearish", rows[-2:], 0.82, current["close"]))
        body = abs(cc - co)
        candle_range = max(current["high"] - current["low"], 1e-12)
        upper = current["high"] - max(co, cc)
        lower = min(co, cc) - current["low"]
        if body / candle_range <= 0.1:
            result.append(self._evidence("Doji", timeframe, "neutral", [current], 0.70, current["close"]))
        if lower >= body * 2 and upper <= max(body, candle_range * 0.15):
            result.append(self._evidence("Hammer", timeframe, "bullish", [current], 0.74, current["close"]))
            result.append(self._evidence("Pin Bar", timeframe, "bullish", [current], 0.72, current["close"]))
        elif upper >= body * 2 and lower <= max(body, candle_range * 0.15):
            result.append(self._evidence("Shooting Star", timeframe, "bearish", [current], 0.74, current["close"]))
            result.append(self._evidence("Pin Bar", timeframe, "bearish", [current], 0.72, current["close"]))
        return result

    def _three_candle_patterns(self, rows: List[Dict[str, Any]], timeframe: str) -> List[PatternEvidence]:
        first, middle, last = rows[-3:]
        result: List[PatternEvidence] = []
        if first["close"] < first["open"] and abs(middle["close"] - middle["open"]) < abs(first["close"] - first["open"]) * 0.5 and last["close"] > last["open"] and last["close"] > (first["open"] + first["close"]) / 2:
            result.append(self._evidence("Morning Star", timeframe, "bullish", rows[-3:], 0.78, last["close"]))
        if first["close"] > first["open"] and abs(middle["close"] - middle["open"]) < abs(first["close"] - first["open"]) * 0.5 and last["close"] < last["open"] and last["close"] < (first["open"] + first["close"]) / 2:
            result.append(self._evidence("Evening Star", timeframe, "bearish", rows[-3:], 0.78, last["close"]))
        return result

    def _structure_patterns(self, rows: List[Dict[str, Any]], timeframe: str) -> List[PatternEvidence]:
        structure = self.market_structure(rows, timeframe)
        direction = structure["overall"]
        result = []
        if "BOS" in structure["labels"]:
            result.append(self._evidence("Break of Structure", timeframe, direction, rows[-4:], 0.80, rows[-1]["close"]))
        return result

    @staticmethod
    def _valid_candles(candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        required = ("open", "high", "low", "close")
        result = []
        for candle in candles or []:
            try:
                if all(candle.get(field) is not None for field in required):
                    row = dict(candle)
                    for field in required:
                        row[field] = float(row[field])
                    row.setdefault("timestamp", datetime.now(timezone.utc))
                    result.append(row)
            except (TypeError, ValueError):
                continue
        return result

    @staticmethod
    def _evidence(name, timeframe, direction, rows, confidence, level):
        return PatternEvidence(name, timeframe, direction, confidence, rows[0].get("timestamp"), rows[-1].get("timestamp"), level, "confirmed")
