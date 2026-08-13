from __future__ import annotations

import os
import sys
from typing import Any


NUMERIC_ENV = {
    "GOLDAPI_MIN_INTERVAL_SECONDS": int,
    "XAU_MAX_STALE_SECONDS": int,
    "MAX_PRICE_DEVIATION_PERCENT": float,
    "MIN_VALID_PROVIDERS": int,
    "NOTIFICATION_DEDUPE_SECONDS": int,
}


def _parse_status(name: str, caster: Any) -> str:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return f"{name} expected={caster.__name__} parsed=UNSET status=NOT SET"
    try:
        parsed = caster(raw)
    except (TypeError, ValueError):
        return f"{name} expected={caster.__name__} parsed=str status=INVALID"
    return f"{name} expected={caster.__name__} parsed={type(parsed).__name__} status=VALID"


def main() -> int:
    print("RUNTIME CONFIGURATION TYPE DIAGNOSTICS")
    for name, caster in NUMERIC_ENV.items():
        print(_parse_status(name, caster))

    try:
        from configuration_manager import ConfigurationManager
        manager = ConfigurationManager()
        system = manager.get_system_config()
        for name, caster in (
            ("goldapi_min_interval_seconds", int),
            ("xau_max_stale_seconds", int),
            ("max_price_deviation_percent", float),
            ("min_valid_providers", int),
            ("notification_dedupe_seconds", int),
        ):
            value = getattr(system, name)
            status = "VALID" if isinstance(value, caster) and not isinstance(value, bool) else "INVALID"
            print(f"{name} expected={caster.__name__} parsed={type(value).__name__} status={status}")
    except Exception as error:
        print(f"Configuration load status=INVALID error_type={type(error).__name__}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
