# core/database.py - COMPLETE FIXED VERSION
import sqlite3
import pandas as pd
from datetime import datetime
import os
import time

class TradeDatabase:
    """Trade and statistics database management - FIXED"""
    
    def __init__(self, db_path="bot_trades.db"):
        self.db_path = db_path
        self.create_tables()
        self.migrate_if_needed()
    
    def create_tables(self):
        """Create database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                strategy TEXT,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                quantity REAL NOT NULL,
                leverage INTEGER DEFAULT 1,
                margin_used REAL,
                pnl_usdt REAL NOT NULL,
                pnl_percent REAL NOT NULL,
                exit_reason TEXT,
                entry_time TEXT,
                exit_time TEXT,
                duration_minutes INTEGER,
                fees REAL DEFAULT 0,
                notes TEXT
            )
        """)
        
        # Daily Capital table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_capital (
                date TEXT PRIMARY KEY,
                opening_capital REAL NOT NULL,
                closing_capital REAL NOT NULL,
                daily_pnl REAL NOT NULL,
                daily_pnl_percent REAL NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                largest_win REAL DEFAULT 0,
                largest_loss REAL DEFAULT 0
            )
        """)
        
        # Signals log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                price REAL NOT NULL,
                action_taken TEXT,
                reason TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def migrate_if_needed(self):
        """Apply necessary migrations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(trades)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'fees' not in columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN fees REAL DEFAULT 0")
        
        if 'notes' not in columns:
            cursor.execute("ALTER TABLE trades ADD COLUMN notes TEXT")
        
        conn.commit()
        conn.close()
    
    def save_trade(self, trade_data):
        """Save a trade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        duration_minutes = None
        if 'entry_time' in trade_data and 'exit_time' in trade_data:
            try:
                entry = datetime.fromisoformat(trade_data['entry_time'])
                exit = datetime.fromisoformat(trade_data['exit_time'])
                duration_minutes = int((exit - entry).total_seconds() / 60)
            except:
                pass
        
        cursor.execute("""
            INSERT INTO trades 
            (timestamp, symbol, side, strategy, entry_price, exit_price, quantity, 
             leverage, margin_used, pnl_usdt, pnl_percent, exit_reason, 
             entry_time, exit_time, duration_minutes, fees, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            trade_data.get('symbol'),
            trade_data.get('side'),
            trade_data.get('strategy', 'Heikin-Ashi'),
            trade_data.get('entry_price'),
            trade_data.get('exit_price'),
            trade_data.get('quantity'),
            trade_data.get('leverage', 1),
            trade_data.get('margin_used'),
            trade_data.get('pnl_usdt'),
            trade_data.get('pnl_percent'),
            trade_data.get('exit_reason'),
            trade_data.get('entry_time'),
            trade_data.get('exit_time', datetime.now().isoformat()),
            duration_minutes,
            trade_data.get('fees', 0),
            trade_data.get('notes')
        ))
        
        conn.commit()
        trade_id = cursor.lastrowid
        conn.close()
        
        return trade_id
    
    def save_signal(self, symbol, signal_type, price, action_taken="", reason=""):
        """Save signal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO signals (timestamp, symbol, signal_type, price, action_taken, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            symbol,
            signal_type,
            price,
            action_taken,
            reason
        ))
        
        conn.commit()
        conn.close()
    
    def update_daily_capital(self, date, capital, pnl):
        """Update daily capital"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_str = date.strftime("%Y-%m-%d") if isinstance(date, datetime) else date
        
        cursor.execute("SELECT * FROM daily_capital WHERE date = ?", (date_str,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("""
                UPDATE daily_capital 
                SET closing_capital = ?, daily_pnl = ?, daily_pnl_percent = ?
                WHERE date = ?
            """, (
                capital,
                pnl,
                (pnl / capital * 100) if capital > 0 else 0,
                date_str
            ))
        else:
            cursor.execute("""
                INSERT INTO daily_capital 
                (date, opening_capital, closing_capital, daily_pnl, daily_pnl_percent)
                VALUES (?, ?, ?, ?, ?)
            """, (
                date_str,
                capital - pnl,
                capital,
                pnl,
                (pnl / capital * 100) if capital > 0 else 0
            ))
        
        conn.commit()
        conn.close()
    
    def get_trade_history(self, days=30, symbol=None):
        """Get trade history"""
        conn = sqlite3.connect(self.db_path)
        
        if days is None:
            query = "SELECT * FROM trades WHERE 1=1"
        else:
            query = f"SELECT * FROM trades WHERE timestamp >= datetime('now', '-{days} days')"
        
        if symbol:
            query += f" AND symbol = '{symbol}'"
        
        query += " ORDER BY timestamp DESC"
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def get_daily_capital_history(self, days=30):
        """Get daily capital history"""
        conn = sqlite3.connect(self.db_path)
        
        df = pd.read_sql_query(f"""
            SELECT * FROM daily_capital 
            WHERE date >= date('now', '-{days} days')
            ORDER BY date ASC
        """, conn)
        
        conn.close()
        return df
    
    def get_signals_history(self, days=7):
        """Get signals history"""
        conn = sqlite3.connect(self.db_path)
        
        df = pd.read_sql_query(f"""
            SELECT * FROM signals 
            WHERE timestamp >= datetime('now', '-{days} days')
            ORDER BY timestamp DESC
        """, conn)
        
        conn.close()
        return df
    
    def get_statistics(self, days=30):
        """Calculate statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        if days:
            time_filter = f"AND timestamp >= datetime('now', '-{days} days')"
        else:
            time_filter = ""
        
        cursor.execute(f"SELECT COUNT(*) FROM trades WHERE 1=1 {time_filter}")
        stats['total_trades'] = cursor.fetchone()[0]
        
        if stats['total_trades'] == 0:
            conn.close()
            return self._empty_stats()
        
        cursor.execute(f"SELECT COUNT(*) FROM trades WHERE 1=1 {time_filter} AND pnl_usdt > 0")
        stats['winning_trades'] = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM trades WHERE 1=1 {time_filter} AND pnl_usdt < 0")
        stats['losing_trades'] = cursor.fetchone()[0]
        
        stats['win_rate'] = (stats['winning_trades'] / stats['total_trades'] * 100)
        
        cursor.execute(f"SELECT SUM(pnl_usdt) FROM trades WHERE 1=1 {time_filter}")
        stats['total_pnl'] = cursor.fetchone()[0] or 0
        
        cursor.execute(f"SELECT AVG(pnl_usdt) FROM trades WHERE 1=1 {time_filter}")
        stats['avg_pnl'] = cursor.fetchone()[0] or 0
        
        cursor.execute(f"SELECT MAX(pnl_usdt) FROM trades WHERE 1=1 {time_filter}")
        stats['best_trade'] = cursor.fetchone()[0] or 0
        
        cursor.execute(f"SELECT MIN(pnl_usdt) FROM trades WHERE 1=1 {time_filter}")
        stats['worst_trade'] = cursor.fetchone()[0] or 0
        
        cursor.execute(f"""
            SELECT AVG(duration_minutes) 
            FROM trades 
            WHERE 1=1 {time_filter} AND duration_minutes IS NOT NULL
        """)
        avg_duration = cursor.fetchone()[0]
        stats['avg_duration_minutes'] = avg_duration if avg_duration else 0
        
        cursor.execute(f"SELECT SUM(pnl_usdt) FROM trades WHERE 1=1 {time_filter} AND pnl_usdt > 0")
        total_profit = cursor.fetchone()[0] or 0
        
        cursor.execute(f"SELECT ABS(SUM(pnl_usdt)) FROM trades WHERE 1=1 {time_filter} AND pnl_usdt < 0")
        total_loss = cursor.fetchone()[0] or 1
        
        stats['profit_factor'] = total_profit / total_loss if total_loss > 0 else 0
        
        stats['max_consecutive_wins'] = self._get_max_consecutive(cursor, "pnl_usdt > 0", time_filter)
        stats['max_consecutive_losses'] = self._get_max_consecutive(cursor, "pnl_usdt < 0", time_filter)
        
        conn.close()
        return stats
    
    def _get_max_consecutive(self, cursor, condition, time_filter):
        """Calculate max consecutive (wins or losses)"""
        cursor.execute(f"""
            SELECT pnl_usdt FROM trades 
            WHERE 1=1 {time_filter}
            ORDER BY timestamp ASC
        """)
        
        results = cursor.fetchall()
        
        max_consecutive = 0
        current_consecutive = 0
        
        for row in results:
            pnl = row[0]
            
            if (condition == "pnl_usdt > 0" and pnl > 0) or \
               (condition == "pnl_usdt < 0" and pnl < 0):
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _empty_stats(self):
        """Empty stats (when no trades)"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'avg_pnl': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'avg_duration_minutes': 0,
            'profit_factor': 0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0
        }
    
    # 🔥 FIXED: Export to CSV with timestamp and lock handling
    def export_to_csv(self, output_path=None, days=None):
        """
        Export trades to CSV with timestamp and lock handling
        
        Args:
            output_path: Custom filename (optional)
            days: Time range filter (None = all)
        
        Returns:
            str: Path to exported file
        """
        
        df = self.get_trade_history(days=days)
        
        if df.empty:
            print("⚠️ No trades to export")
            return None
        
        # 🔥 Generate unique filename
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"trades_export_{timestamp}.csv"
        
        # 🔥 Try export with retry
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                print(f"✅ Exported {len(df)} trades to {output_path}")
                return output_path
            
            except PermissionError:
                if attempt < max_retries - 1:
                    # Try with different name
                    base_name = output_path.replace('.csv', '')
                    output_path = f"{base_name}_{int(time.time())}.csv"
                    print(f"⚠️ File locked, trying: {output_path}")
                else:
                    # Final attempt failed
                    raise PermissionError(
                        f"Cannot write to {output_path}. "
                        "Please close the file in Excel/Notepad and try again."
                    )
            
            except Exception as e:
                print(f"❌ Export error: {e}")
                raise
        
        return None
    
    @staticmethod
    def is_file_locked(filepath):
        """Check if file is locked by another process"""
        if not os.path.exists(filepath):
            return False
        
        try:
            os.rename(filepath, filepath)
            return False
        except OSError:
            return True
    
    def delete_old_data(self, days=90):
        """Delete data older than X days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(f"""
            DELETE FROM trades 
            WHERE timestamp < datetime('now', '-{days} days')
        """)
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"✅ Deleted {deleted} old records")
        return deleted
    
    def get_database_size(self):
        """Get database size (MB)"""
        if os.path.exists(self.db_path):
            size_bytes = os.path.getsize(self.db_path)
            size_mb = size_bytes / (1024 * 1024)
            return size_mb
        return 0