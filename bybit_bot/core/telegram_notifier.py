# core/telegram_notifier.py
import requests
import threading
import time
from datetime import datetime, timedelta
import streamlit as st

class TelegramNotifier:
    """سیستم اعلان رسانی تلگرام"""
    
    def __init__(self, bot_token=None, chat_id=None, enabled=False):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.base_url = f"https://api.telegram.org/bot{bot_token}" if bot_token else None
        self.last_daily_report = None
        self.message_queue = []
    
    def is_configured(self):
        """بررسی اینکه تنظیمات کامل است"""
        return bool(self.bot_token and self.chat_id and self.enabled)
    
    def send_message(self, text, parse_mode="HTML", disable_notification=False):
        """ارسال پیام به تلگرام"""
        if not self.is_configured():
            return None
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_notification": disable_notification
            }
            
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            
            if result.get("ok"):
                return result
            else:
                print(f"Telegram Error: {result.get('description', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
            return None
    
    def notify_entry(self, symbol, side, entry_price, quantity, leverage, margin_used, strategy=""):
        """اعلان باز شدن پوزیشن"""
        if not self.is_configured():
            return
        
        emoji = "🟢" if side == "Buy" else "🔴"
        direction = "LONG" if side == "Buy" else "SHORT"
        
        tp_text = ""
        sl_text = ""
        
        if st.session_state.get('use_tp', False):
            tp_perc = st.session_state.get('tp_perc_long' if side == "Buy" else 'tp_perc_short', 0)
            tp_price = entry_price * (1 + tp_perc/100) if side == "Buy" else entry_price * (1 - tp_perc/100)
            tp_text = f"\n📈 <b>Take Profit:</b> {tp_price:.4f} (+{tp_perc}%)"
        
        if st.session_state.get('use_sl', False):
            sl_perc = st.session_state.get('sl_perc_long' if side == "Buy" else 'sl_perc_short', 0)
            sl_price = entry_price * (1 - sl_perc/100) if side == "Buy" else entry_price * (1 + sl_perc/100)
            sl_text = f"\n📉 <b>Stop Loss:</b> {sl_price:.4f} (-{sl_perc}%)"
        
        text = f"""
{emoji} <b>🎯 NEW POSITION OPENED</b> {emoji}

<b>Symbol:</b> {symbol}
<b>Direction:</b> {direction}
<b>Entry Price:</b> {entry_price:.4f}
<b>Quantity:</b> {quantity:.6f}
<b>Leverage:</b> {leverage}x
<b>Margin Used:</b> {margin_used:.2f} USDT
{tp_text}{sl_text}

<b>Strategy:</b> {strategy if strategy else 'N/A'}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💰 Good luck! Let's make some profit! 🚀
        """
        
        self.send_message(text.strip())
    
    def notify_exit(self, symbol, side, entry_price, exit_price, quantity, pnl_usdt, pnl_percent, reason):
        """اعلان بسته شدن پوزیشن"""
        if not self.is_configured():
            return
        
        if pnl_usdt > 0:
            emoji = "✅"
            status = "PROFIT"
            pnl_emoji = "💰"
        elif pnl_usdt < 0:
            emoji = "❌"
            status = "LOSS"
            pnl_emoji = "📉"
        else:
            emoji = "⚪"
            status = "BREAKEVEN"
            pnl_emoji = "➖"
        
        direction = "LONG" if side == "Buy" else "SHORT"
        
        text = f"""
{emoji} <b>{pnl_emoji} POSITION CLOSED - {status}</b> {emoji}

<b>Symbol:</b> {symbol}
<b>Direction:</b> {direction}
<b>Entry Price:</b> {entry_price:.4f}
<b>Exit Price:</b> {exit_price:.4f}
<b>Quantity:</b> {quantity:.6f}

{pnl_emoji} <b>PnL:</b> {pnl_usdt:+.2f} USDT ({pnl_percent:+.2f}%)

<b>Exit Reason:</b> {reason}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{"🎉 Congratulations!" if pnl_usdt > 0 else "📚 Learn and improve!"}
        """
        
        self.send_message(text.strip())
    
    def notify_bot_started(self, balance):
        """اعلان شروع بات"""
        if not self.is_configured():
            return
        
        text = f"""
🟢 <b>🤖 BOT STARTED</b> 🟢

<b>Status:</b> Live Trading Active
<b>Initial Balance:</b> {balance:.2f} USDT
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ Bot is now monitoring the market and ready to trade!
Stay tuned for updates. 📊
        """
        
        self.send_message(text.strip())
    
    def notify_bot_stopped(self, final_balance, total_pnl, pnl_percent):
        """اعلان توقف بات"""
        if not self.is_configured():
            return
        
        emoji = "🎉" if total_pnl > 0 else "📉" if total_pnl < 0 else "➖"
        
        text = f"""
🔴 <b>🤖 BOT STOPPED</b> 🔴

<b>Status:</b> Trading Paused
<b>Final Balance:</b> {final_balance:.2f} USDT
<b>Total PnL:</b> {total_pnl:+.2f} USDT ({pnl_percent:+.2f}%)
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{emoji} {"Great job!" if total_pnl > 0 else "Keep learning!"}
        """
        
        self.send_message(text.strip())
    
    def notify_error(self, error_type, error_message):
        """اعلان خطا"""
        if not self.is_configured():
            return
        
        text = f"""
⚠️ <b>🚨 ERROR ALERT</b> ⚠️

<b>Type:</b> {error_type}
<b>Message:</b> {error_message}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔧 Please check the bot and fix the issue.
        """
        
        self.send_message(text.strip())
    
    def notify_connection_lost(self):
        """Alert when connection to exchange is lost"""
        if not self.is_configured():
            return
        
        text = f"""
🔴 <b>⚠️ CONNECTION LOST</b> 🔴

<b>Status:</b> Unable to reach Bybit API
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔄 Bot is still RUNNING and will retry automatically.
Positions remain open, but new trades are paused until reconnection.

💡 No action needed - waiting for network recovery.
        """
        
        self.send_message(text.strip())
    
    def notify_connection_restored(self):
        """Alert when connection is restored"""
        if not self.is_configured():
            return
        
        text = f"""
🟢 <b>✅ CONNECTION RESTORED</b> 🟢

<b>Status:</b> Connection to Bybit API re-established
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ Bot resumed normal operation.
Strategy execution will continue on next signal.
        """
        
        self.send_message(text.strip())
    
    def send_daily_report(self, db, current_capital, initial_capital):
        """ارسال گزارش روزانه"""
        if not self.is_configured():
            return
        
        today = datetime.now().date()
        
        if self.last_daily_report == today:
            return
        
        stats = db.get_statistics(days=1)
        
        total_pnl = current_capital - initial_capital
        pnl_percent = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
        
        emoji = "📈" if total_pnl > 0 else "📉" if total_pnl < 0 else "➖"
        
        text = f"""
{emoji} <b>📊 DAILY REPORT</b> {emoji}

<b>Date:</b> {today.strftime('%Y-%m-%d')}

<b>💰 Capital Status:</b>
• Current: {current_capital:.2f} USDT
• Initial: {initial_capital:.2f} USDT
• PnL: {total_pnl:+.2f} USDT ({pnl_percent:+.2f}%)

<b>📈 Today's Performance:</b>
• Total Trades: {stats['total_trades']}
• Winning Trades: {stats['winning_trades']}
• Losing Trades: {stats['losing_trades']}
• Win Rate: {stats['win_rate']:.1f}%
• Total PnL: {stats['total_pnl']:+.2f} USDT

<b>🏆 Best/Worst:</b>
• Best Trade: +{stats['best_trade']:.2f} USDT
• Worst Trade: {stats['worst_trade']:.2f} USDT

<b>⏱️ Report Time:</b> {datetime.now().strftime('%H:%M:%S')}

{"🎉 Great day!" if total_pnl > 0 else "💪 Tomorrow is another chance!"}
        """
        
        self.send_message(text.strip())
        self.last_daily_report = today