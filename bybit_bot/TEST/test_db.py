# test_db.py
from core.database import TradeDatabase
from datetime import datetime

db = TradeDatabase("bot_trades.db")

# تست ذخیره یک معامله
trade_data = {
    'symbol': 'BTCUSDT',
    'side': 'Buy',
    'entry_price': 50000.0,
    'exit_price': 51000.0,
    'quantity': 0.001,
    'leverage': 10,
    'margin_used': 5.0,
    'pnl_usdt': 1.0,
    'pnl_percent': 2.0,
    'exit_reason': 'TP Hit',
    'entry_time': datetime.now().isoformat(),
    'exit_time': datetime.now().isoformat(),
    'strategy': 'Test'
}

print("📝 Attempting to save trade...")
try:
    trade_id = db.save_trade(trade_data)
    print(f"✅ Trade saved successfully! ID: {trade_id}")
    
    # حالا چک کن
    import sqlite3
    conn = sqlite3.connect("bot_trades.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades")
    trades = cursor.fetchall()
    print(f"📊 Total trades now: {len(trades)}")
    
    if trades:
        print("\n📋 Last trade:")
        print(trades[-1])
    
    conn.close()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()