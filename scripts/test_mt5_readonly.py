"""Prove MT5 order operations are refused in READ_ONLY mode."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mt5_bridge import MT5Connection, MT5ExecutionAdapter

def main():
    adapter = MT5ExecutionAdapter(MT5Connection(enabled=False, mode="READ_ONLY"))
    try:
        adapter.open_position("BTCUSD", "BUY")
    except RuntimeError as exc:
        print(f"READ_ONLY protection: PASS ({exc})")
    else:
        raise SystemExit("READ_ONLY protection failed")

if __name__ == "__main__":
    main()