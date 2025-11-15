# core/notifier.py
import requests

class TelegramNotifier:
    """ارسال پیام به تلگرام"""
    
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, text):
        """ارسال پیام ساده"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data, timeout=10)
            return response.json()
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
            return None
    
    def notify_entry(self, symbol, side, price, qty, margin):
        """اعلان ورود"""
        emoji = "🟢" if side == "Buy" else "🔴"
        text = f"""
{emoji} <b>NEW POSITION OPENED</b>

Symbol: {symbol}
Side: {side}
Entry Price: {price:.4f}
Quantity: {qty:.6f}
Margin Used: {margin:.2f} USDT

Good luck! 🚀
        """
        self.send_message(text)
    
    def notify_exit(self, symbol, side, pnl_usdt, pnl_perc, reason):
        """اعلان خروج"""
        emoji = "✅" if pnl_usdt >= 0 else "❌"
        text = f"""
{emoji} <b>POSITION CLOSED</b>

Symbol: {symbol}
Side: {side}
PnL: {pnl_usdt:+.2f} USDT ({pnl_perc:+.2f}%)
Reason: {reason}

{"Profit!" if pnl_usdt >= 0 else "Loss!"}
        """
        self.send_message(text)
    
    def notify_error(self, error_msg):
        """اعلان خطا"""
        text = f"⚠️ <b>BOT ERROR</b>\n\n{error_msg}"
        self.send_message(text)