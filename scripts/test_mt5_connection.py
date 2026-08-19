"""Windows-local sanitized MT5 connectivity diagnostic."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mt5_bridge import MT5Connection, MT5MarketData, MT5AccountReader, MT5HealthMonitor, MT5SymbolMapper

def main():
    connection = MT5Connection()
    if not connection.connect():
        print(f"MT5: DISCONNECTED ({connection.last_error})")
        return
    market = MT5MarketData(connection, MT5SymbolMapper.from_environment())
    monitor = MT5HealthMonitor(connection, market, MT5AccountReader(connection))
    print(monitor.report())
    for asset in ("BTCUSD", "XAUUSD"):
        print(asset, market.check_symbol(asset))
        print("tick", market.get_tick(asset))
        for timeframe in ("M5", "M15", "H1", "H4", "D1"):
            bars = market.get_ohlcv(asset, timeframe, 100)
            print(asset, timeframe, len(bars), bars[-1] if bars else None)
    connection.shutdown()

if __name__ == "__main__":
    main()