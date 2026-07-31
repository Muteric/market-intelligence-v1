"""
Trade Storage for AI Trading Intelligence Bot
Persistent storage for trades, portfolio statistics, and performance data.
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from asset_manager import Trade, TradeStatus
from configuration_manager import SystemConfig

class StorageType(Enum):
    """Storage types"""
    SQLITE = "sqlite"
    JSON = "json"
    MIXED = "mixed"

@dataclass
class TradeRecord:
    """Trade record for storage"""
    id: str = None
    asset: str = None
    direction: str = None
    entry_price: float = None
    entry_time: datetime = None
    exit_price: float = None
    exit_time: datetime = None
    position_size: float = None
    leverage: float = None
    floating_pnl: float = 0.0
    realized_pnl: float = 0.0
    trade_duration: int = 0
    roi: float = 0.0
    status: str = TradeStatus.OPEN.value
    stop_loss_price: float = None
    take_profit_price: float = None
    close_reason: str = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.entry_time is None:
            self.entry_time = datetime.now(timezone.utc)

@dataclass
class PortfolioStatsRecord:
    """Portfolio statistics record for storage"""
    id: str = None
    timestamp: datetime = None
    total_balance: float = 0.0
    total_equity: float = 0.0
    total_floating_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    net_pnl: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    max_drawdown: float = 0.0
    recovery_factor: float = 0.0
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

class TradeStorage:
    """Manages persistent storage of trading data"""
    
    def __init__(self, system_config: SystemConfig, storage_type: str = StorageType.SQLITE.value):
        self.system_config = system_config
        self.storage_type = storage_type
        self._initialize_storage()
    
    def _initialize_storage(self) -> None:
        """Initialize storage based on type"""
        if self.storage_type == StorageType.SQLITE.value:
            self._initialize_sqlite()
        elif self.storage_type == StorageType.JSON.value:
            self._initialize_json()
        else:  # MIXED
            self._initialize_sqlite()
            self._initialize_json()
    
    def _initialize_sqlite(self) -> None:
        """Initialize SQLite database"""
        # Ensure data directory exists
        data_dir = Path(self.system_config.data_directory)
        data_dir.mkdir(exist_ok=True)
        
        self.db_path = data_dir / "trading_data.db"
        
        # Create connection
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        # Create tables
        self._create_tables()
    
    def _initialize_json(self) -> None:
        """Initialize JSON storage"""
        data_dir = Path(self.system_config.data_directory)
        data_dir.mkdir(exist_ok=True)
        
        self.json_dir = data_dir / "json_data"
        self.json_dir.mkdir(exist_ok=True)
    
    def _create_tables(self) -> None:
        """Create SQLite tables"""
        cursor = self.conn.cursor()
        
        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                asset TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                entry_time TEXT NOT NULL,
                exit_price REAL,
                exit_time TEXT,
                position_size REAL NOT NULL,
                leverage REAL NOT NULL,
                floating_pnl REAL DEFAULT 0.0,
                realized_pnl REAL DEFAULT 0.0,
                trade_duration INTEGER DEFAULT 0,
                roi REAL DEFAULT 0.0,
                status TEXT NOT NULL,
                stop_loss_price REAL,
                take_profit_price REAL,
                close_reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Portfolio stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_stats (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                total_balance REAL NOT NULL,
                total_equity REAL NOT NULL,
                total_floating_pnl REAL NOT NULL,
                total_realized_pnl REAL NOT NULL,
                net_pnl REAL NOT NULL,
                win_rate REAL NOT NULL,
                profit_factor REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                winning_trades INTEGER NOT NULL,
                losing_trades INTEGER NOT NULL,
                max_drawdown REAL NOT NULL,
                recovery_factor REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                decision TEXT NOT NULL,
                confidence REAL NOT NULL,
                action_taken TEXT NOT NULL,
                positions_opened INTEGER NOT NULL,
                positions_closed INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                symbol TEXT,
                data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def save_trade(self, trade: Trade) -> bool:
        """Save a trade to storage"""
        try:
            if self.storage_type in [StorageType.SQLITE.value, StorageType.MIXED.value]:
                self._save_trade_sqlite(trade)
            
            if self.storage_type in [StorageType.JSON.value, StorageType.MIXED.value]:
                self._save_trade_json(trade)
            
            return True
        except Exception as e:
            print(f"Error saving trade: {e}")
            return False
    
    def save_portfolio_stats(self, stats: Dict[str, Any]) -> bool:
        """Save portfolio statistics to storage"""
        try:
            if self.storage_type in [StorageType.SQLITE.value, StorageType.MIXED.value]:
                self._save_portfolio_stats_sqlite(stats)
            
            if self.storage_type in [StorageType.JSON.value, StorageType.MIXED.value]:
                self._save_portfolio_stats_json(stats)
            
            return True
        except Exception as e:
            print(f"Error saving portfolio stats: {e}")
            return False
    
    def save_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Save a signal to storage"""
        try:
            if self.storage_type in [StorageType.SQLITE.value, StorageType.MIXED.value]:
                self._save_signal_sqlite(signal_data)
            
            if self.storage_type in [StorageType.JSON.value, StorageType.MIXED.value]:
                self._save_signal_json(signal_data)
            
            return True
        except Exception as e:
            print(f"Error saving signal: {e}")
            return False
    
    def get_trades(self, symbol: str = None, status: str = None, 
                   limit: int = 100) -> List[Trade]:
        """Get trades from storage"""
        trades = []
        
        if self.storage_type in [StorageType.SQLITE.value, StorageType.MIXED.value]:
            trades.extend(self._get_trades_sqlite(symbol, status, limit))
        
        if self.storage_type in [StorageType.JSON.value, StorageType.MIXED.value]:
            trades.extend(self._get_trades_json(symbol, status, limit))
        
        # Remove duplicates (if both storage types are used)
        unique_trades = []
        seen_ids = set()
        
        for trade in trades:
            if trade.id not in seen_ids:
                seen_ids.add(trade.id)
                unique_trades.append(trade)
        
        return unique_trades[:limit]
    
    def get_portfolio_stats(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get portfolio statistics from storage"""
        stats = []
        
        if self.storage_type in [StorageType.SQLITE.value, StorageType.MIXED.value]:
            stats.extend(self._get_portfolio_stats_sqlite(limit))
        
        if self.storage_type in [StorageType.JSON.value, StorageType.MIXED.value]:
            stats.extend(self._get_portfolio_stats_json(limit))
        
        return stats[:limit]
    
    def get_signals(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get signals from storage"""
        signals = []
        
        if self.storage_type in [StorageType.SQLITE.value, StorageType.MIXED.value]:
            signals.extend(self._get_signals_sqlite(symbol, limit))
        
        if self.storage_type in [StorageType.JSON.value, StorageType.MIXED.value]:
            signals.extend(self._get_signals_json(symbol, limit))
        
        return signals[:limit]
    
    def backup_data(self) -> bool:
        """Create backup of all data"""
        try:
            if self.system_config.backup_enabled:
                backup_dir = Path(self.system_config.data_directory) / "backups"
                backup_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                backup_file = backup_dir / f"backup_{timestamp}.json"
                
                # Create backup data
                backup_data = {
                    'trades': self.get_trades(),
                    'portfolio_stats': self.get_portfolio_stats(),
                    'signals': self.get_signals(),
                    'backup_timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, default=str)
                
                # Keep only last N backup files
                backup_files = list(backup_dir.glob('backup_*.json'))
                backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                
                if len(backup_files) > self.system_config.max_backup_files:
                    for old_backup in backup_files[self.system_config.max_backup_files:]:
                        old_backup.unlink()
            
            return True
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False
    
    def restore_from_backup(self, backup_file: str) -> bool:
        """Restore data from backup file"""
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Clear existing data
            self._clear_data()
            
            # Restore data
            for trade_data in backup_data.get('trades', []):
                trade = self._trade_from_dict(trade_data)
                self.save_trade(trade)
            
            for stats_data in backup_data.get('portfolio_stats', []):
                self.save_portfolio_stats(stats_data)
            
            for signal_data in backup_data.get('signals', []):
                self.save_signal(signal_data)
            
            return True
        except Exception as e:
            print(f"Error restoring from backup: {e}")
            return False
    
    def _save_trade_sqlite(self, trade: Trade) -> None:
        """Save trade to SQLite database"""
        cursor = self.conn.cursor()
        
        trade_dict = asdict(trade)
        
        # Convert datetime objects to strings
        if trade_dict['entry_time']:
            trade_dict['entry_time'] = trade_dict['entry_time'].isoformat()
        if trade_dict['exit_time']:
            trade_dict['exit_time'] = trade_dict['exit_time'].isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO trades 
            (id, asset, direction, entry_price, entry_time, exit_price, exit_time,
             position_size, leverage, floating_pnl, realized_pnl, trade_duration,
             roi, status, stop_loss_price, take_profit_price, close_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_dict['id'], trade_dict['asset'], trade_dict['direction'],
            trade_dict['entry_price'], trade_dict['entry_time'], trade_dict['exit_price'],
            trade_dict['exit_time'], trade_dict['position_size'], trade_dict['leverage'],
            trade_dict['floating_pnl'], trade_dict['realized_pnl'], trade_dict['trade_duration'],
            trade_dict['roi'], trade_dict['status'], trade_dict['stop_loss_price'],
            trade_dict['take_profit_price'], trade_dict['close_reason']
        ))
        
        self.conn.commit()
    
    def _save_trade_json(self, trade: Trade) -> None:
        """Save trade to JSON file"""
        trade_dict = asdict(trade)
        
        # Convert datetime objects to strings
        if trade_dict['entry_time']:
            trade_dict['entry_time'] = trade_dict['entry_time'].isoformat()
        if trade_dict['exit_time']:
            trade_dict['exit_time'] = trade_dict['exit_time'].isoformat()
        
        # Save to file
        filename = f"trades_{trade.asset.lower()}.json"
        filepath = self.json_dir / filename
        
        # Load existing trades
        trades = []
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                trades = json.load(f)
        
        # Add new trade
        trades.append(trade_dict)
        
        # Save back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(trades, f, indent=2, default=str)
    
    def _save_portfolio_stats_sqlite(self, stats: Dict[str, Any]) -> None:
        """Save portfolio stats to SQLite database"""
        cursor = self.conn.cursor()
        
        stats_dict = stats.copy()
        
        # Convert timestamp to string
        if 'timestamp' in stats_dict and isinstance(stats_dict['timestamp'], datetime):
            stats_dict['timestamp'] = stats_dict['timestamp'].isoformat()
        
        cursor.execute('''
            INSERT INTO portfolio_stats 
            (id, timestamp, total_balance, total_equity, total_floating_pnl,
             total_realized_pnl, net_pnl, win_rate, profit_factor, total_trades,
             winning_trades, losing_trades, max_drawdown, recovery_factor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()), stats_dict.get('timestamp', datetime.now(timezone.utc).isoformat()),
            stats_dict.get('total_balance', 0.0), stats_dict.get('total_equity', 0.0),
            stats_dict.get('total_floating_pnl', 0.0), stats_dict.get('total_realized_pnl', 0.0),
            stats_dict.get('net_pnl', 0.0), stats_dict.get('win_rate', 0.0),
            stats_dict.get('profit_factor', 0.0), stats_dict.get('total_trades', 0),
            stats_dict.get('winning_trades', 0), stats_dict.get('losing_trades', 0),
            stats_dict.get('max_drawdown', 0.0), stats_dict.get('recovery_factor', 0.0)
        ))
        
        self.conn.commit()
    
    def _save_portfolio_stats_json(self, stats: Dict[str, Any]) -> None:
        """Save portfolio stats to JSON file"""
        stats_dict = stats.copy()
        
        # Convert timestamp to string
        if 'timestamp' in stats_dict and isinstance(stats_dict['timestamp'], datetime):
            stats_dict['timestamp'] = stats_dict['timestamp'].isoformat()
        
        # Save to file
        filename = f"portfolio_stats_{datetime.now(timezone.utc).strftime('%Y%m')}.json"
        filepath = self.json_dir / filename
        
        # Load existing stats
        stats_list = []
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                stats_list = json.load(f)
        
        # Add new stats
        stats_list.append(stats_dict)
        
        # Save back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(stats_list, f, indent=2, default=str)
    
    def _save_signal_sqlite(self, signal_data: Dict[str, Any]) -> None:
        """Save signal to SQLite database"""
        cursor = self.conn.cursor()
        
        signal_dict = signal_data.copy()
        
        # Convert timestamp to string
        if 'timestamp' in signal_dict and isinstance(signal_dict['timestamp'], datetime):
            signal_dict['timestamp'] = signal_dict['timestamp'].isoformat()
        
        cursor.execute('''
            INSERT INTO signals 
            (id, symbol, timestamp, decision, confidence, action_taken,
             positions_opened, positions_closed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()), signal_dict.get('symbol'),
            signal_dict.get('timestamp', datetime.now(timezone.utc).isoformat()),
            signal_dict.get('decision'), signal_dict.get('confidence', 0.0),
            signal_dict.get('action_taken', ''), signal_dict.get('positions_opened', 0),
            signal_dict.get('positions_closed', 0)
        ))
        
        self.conn.commit()
    
    def _save_signal_json(self, signal_data: Dict[str, Any]) -> None:
        """Save signal to JSON file"""
        signal_dict = signal_data.copy()
        
        # Convert timestamp to string
        if 'timestamp' in signal_dict and isinstance(signal_dict['timestamp'], datetime):
            signal_dict['timestamp'] = signal_dict['timestamp'].isoformat()
        
        # Save to file
        filename = f"signals_{signal_dict.get('symbol', 'unknown')}.json"
        filepath = self.json_dir / filename
        
        # Load existing signals
        signals = []
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                signals = json.load(f)
        
        # Add new signal
        signals.append(signal_dict)
        
        # Save back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(signals, f, indent=2, default=str)
    
    def _get_trades_sqlite(self, symbol: str = None, status: str = None, 
                          limit: int = 100) -> List[Trade]:
        """Get trades from SQLite database"""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND asset = ?"
            params.append(symbol)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY entry_time DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        trades = []
        for row in cursor.fetchall():
            trade = self._trade_from_row(row)
            trades.append(trade)
        
        return trades
    
    def _get_trades_json(self, symbol: str = None, status: str = None, 
                        limit: int = 100) -> List[Trade]:
        """Get trades from JSON files"""
        trades = []
        
        for filepath in self.json_dir.glob("*.json"):
            if symbol and symbol.lower() not in filepath.name:
                continue
            
            with open(filepath, 'r', encoding='utf-8') as f:
                file_trades = json.load(f)
            
            for trade_dict in file_trades:
                if status and trade_dict.get('status') != status:
                    continue
                
                trade = self._trade_from_dict(trade_dict)
                trades.append(trade)
        
        # Sort by entry time
        trades.sort(key=lambda t: t.entry_time, reverse=True)
        
        return trades[:limit]
    
    def _get_portfolio_stats_sqlite(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get portfolio stats from SQLite database"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM portfolio_stats 
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        
        stats = []
        for row in cursor.fetchall():
            stats.append(self._stats_from_row(row))
        
        return stats
    
    def _get_portfolio_stats_json(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get portfolio stats from JSON files"""
        stats = []
        
        for filepath in self.json_dir.glob("portfolio_stats_*.json"):
            with open(filepath, 'r', encoding='utf-8') as f:
                file_stats = json.load(f)
            
            stats.extend(file_stats)
        
        # Sort by timestamp
        stats.sort(key=lambda s: s.get('timestamp', ''), reverse=True)
        
        return stats[:limit]
    
    def _get_signals_sqlite(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get signals from SQLite database"""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM signals WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        signals = []
        for row in cursor.fetchall():
            signals.append(self._signal_from_row(row))
        
        return signals
    
    def _get_signals_json(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get signals from JSON files"""
        signals = []
        
        for filepath in self.json_dir.glob("*.json"):
            if symbol and symbol.lower() not in filepath.name:
                continue
            
            with open(filepath, 'r', encoding='utf-8') as f:
                file_signals = json.load(f)
            
            for signal_dict in file_signals:
                if signal_dict.get('symbol') == symbol:
                    signals.append(signal_dict)
        
        # Sort by timestamp
        signals.sort(key=lambda s: s.get('timestamp', ''), reverse=True)
        
        return signals[:limit]
    
    def _trade_from_row(self, row: sqlite3.Row) -> Trade:
        """Convert SQLite row to Trade object"""
        trade_dict = dict(row)
        
        # Convert strings to appropriate types
        trade_dict['entry_price'] = float(trade_dict['entry_price'])
        trade_dict['exit_price'] = float(trade_dict['exit_price']) if trade_dict['exit_price'] else None
        trade_dict['position_size'] = float(trade_dict['position_size'])
        trade_dict['leverage'] = float(trade_dict['leverage'])
        trade_dict['floating_pnl'] = float(trade_dict['floating_pnl'])
        trade_dict['realized_pnl'] = float(trade_dict['realized_pnl'])
        trade_dict['trade_duration'] = int(trade_dict['trade_duration'])
        trade_dict['roi'] = float(trade_dict['roi'])
        trade_dict['stop_loss_price'] = float(trade_dict['stop_loss_price']) if trade_dict['stop_loss_price'] else None
        trade_dict['take_profit_price'] = float(trade_dict['take_profit_price']) if trade_dict['take_profit_price'] else None
        
        # Convert timestamp strings to datetime
        trade_dict['entry_time'] = datetime.fromisoformat(trade_dict['entry_time'])
        if trade_dict['exit_time']:
            trade_dict['exit_time'] = datetime.fromisoformat(trade_dict['exit_time'])
        
        return Trade(**trade_dict)
    
    def _trade_from_dict(self, trade_dict: Dict[str, Any]) -> Trade:
        """Convert dictionary to Trade object"""
        # Convert strings to appropriate types
        trade_dict['entry_price'] = float(trade_dict['entry_price'])
        trade_dict['exit_price'] = float(trade_dict['exit_price']) if trade_dict.get('exit_price') else None
        trade_dict['position_size'] = float(trade_dict['position_size'])
        trade_dict['leverage'] = float(trade_dict['leverage'])
        trade_dict['floating_pnl'] = float(trade_dict.get('floating_pnl', 0.0))
        trade_dict['realized_pnl'] = float(trade_dict.get('realized_pnl', 0.0))
        trade_dict['trade_duration'] = int(trade_dict.get('trade_duration', 0))
        trade_dict['roi'] = float(trade_dict.get('roi', 0.0))
        trade_dict['stop_loss_price'] = float(trade_dict['stop_loss_price']) if trade_dict.get('stop_loss_price') else None
        trade_dict['take_profit_price'] = float(trade_dict['take_profit_price']) if trade_dict.get('take_profit_price') else None
        
        # Convert timestamp strings to datetime
        trade_dict['entry_time'] = datetime.fromisoformat(trade_dict['entry_time'])
        if trade_dict.get('exit_time'):
            trade_dict['exit_time'] = datetime.fromisoformat(trade_dict['exit_time'])
        
        return Trade(**trade_dict)
    
    def _stats_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to stats dictionary"""
        return dict(row)
    
    def _signal_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to signal dictionary"""
        return dict(row)
    
    def _clear_data(self) -> None:
        """Clear all data from storage"""
        if self.storage_type in [StorageType.SQLITE.value, StorageType.MIXED.value]:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM trades")
            cursor.execute("DELETE FROM portfolio_stats")
            cursor.execute("DELETE FROM signals")
            cursor.execute("DELETE FROM events")
            self.conn.commit()
        
        if self.storage_type in [StorageType.JSON.value, StorageType.MIXED.value]:
            for filepath in self.json_dir.glob("*.json"):
                filepath.unlink()
    
    def _round_decimal(self, value: float, decimals: int = 2) -> float:
        """Round decimal value to specified precision"""
        return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))