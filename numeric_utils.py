"""Shared numeric normalization for trading metrics."""

import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


def round_finite(value: Optional[float], decimals: int = 2,
                 non_finite: float = 0.0) -> Optional[float]:
    """Round finite numeric values and normalize NaN/infinity safely.

    Metrics such as profit factor can be mathematically unbounded when there
    are no losses.  Persisted and displayed metrics must remain finite, so
    callers receive the explicit ``non_finite`` sentinel instead.
    """
    if value is None:
        return None
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        return non_finite
    quantum = Decimal("1").scaleb(-decimals)
    return float(Decimal(str(numeric_value)).quantize(quantum, rounding=ROUND_HALF_UP))
