# core/utils.py
import pandas as pd
from datetime import datetime
# core/utils.py - اضافه کردن helper function

import pandas as pd
from datetime import datetime, timezone

def safe_float(value, default=0.0):
    """Safe float conversion"""
    if value is None or (isinstance(value, str) and value.strip() == ''):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def get_utc_time():
    """Get current UTC time"""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def format_time_difference(seconds):
    """Format time difference in human readable format"""
    if abs(seconds) < 1:
        return f"{seconds*1000:.0f}ms"
    elif abs(seconds) < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"

def calculate_refresh_delay(timeframe_str):
    """Calculate time until next candle close"""
    timeframe_map = {
        "1": 1, "3": 3, "5": 5, "15": 15, "30": 30,
        "60": 60, "120": 120, "240": 240
    }
    
    now = datetime.utcnow()  # 🔥 Changed to UTC
    
    if timeframe_str in ["D", "W"]:
        next_check_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + pd.Timedelta(days=1)
        return int((next_check_time - now).total_seconds()), next_check_time
    
    minutes = timeframe_map.get(timeframe_str)
    if not minutes:
        return 60, now.replace(second=0, microsecond=0) + pd.Timedelta(minutes=1)
    
    candle_duration_sec = minutes * 60
    now_ts = int(now.timestamp())
    current_open_ts = now_ts - (now_ts % candle_duration_sec)
    next_close_ts = current_open_ts + candle_duration_sec
    next_close_time = datetime.utcfromtimestamp(next_close_ts)
    delay = next_close_ts - now_ts
    
    buffer = 5
    final_delay = max(delay + buffer, 10)
    
    return final_delay, next_close_time

def get_tradingview_html(symbol, timeframe, candle_type="Regular", theme="dark"):
    """Generate TradingView chart HTML"""
    tf_map = {
        "1": "1", "3": "3", "5": "5", "15": "15", "30": "30",
        "60": "1H", "120": "2H", "240": "4H", "D": "1D", "W": "1W"
    }
    tv_tf = tf_map.get(timeframe, "15")
    
    tv_chart_style = "8"  # Heikin-Ashi
    
    tv_html = f"""
    <div class="tradingview-widget-container" style="height:380px;">
      <div id="tradingview_123456" style="height:380px;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "autosize": true,
        "symbol": "BYBIT:{symbol}",
        "interval": "{tv_tf}",
        "timezone": "Etc/UTC",
        "theme": "{theme}",
        "style": "{tv_chart_style}",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": true,
        "hide_top_toolbar": false,
        "hide_legend": false,
        "save_image": true,
        "calendar": true,
        "container_id": "tradingview_123456"
      }});
      </script>
    </div>
    """
    return tv_html


def safe_float(value, default=0.0):
    """Safe float conversion"""
    if value is None or (isinstance(value, str) and value.strip() == ''):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def calculate_refresh_delay(timeframe_str):
    """Calculate time until next candle close"""
    timeframe_map = {
        "1": 1, "3": 3, "5": 5, "15": 15, "30": 30,
        "60": 60, "120": 120, "240": 240
    }
    
    now = datetime.now()
    
    if timeframe_str in ["D", "W"]:
        next_check_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + pd.Timedelta(days=1)
        return int((next_check_time - now).total_seconds()), next_check_time
    
    minutes = timeframe_map.get(timeframe_str)
    if not minutes:
        return 60, now.replace(second=0, microsecond=0) + pd.Timedelta(minutes=1)
    
    candle_duration_sec = minutes * 60
    now_ts = int(now.timestamp())
    current_open_ts = now_ts - (now_ts % candle_duration_sec)
    next_close_ts = current_open_ts + candle_duration_sec
    next_close_time = datetime.fromtimestamp(next_close_ts)
    delay = next_close_ts - now_ts
    
    buffer = 5
    final_delay = max(delay + buffer, 10)
    
    return final_delay, next_close_time

def get_tradingview_html(symbol, timeframe, candle_type="Regular", theme="dark"):
    """Generate TradingView chart HTML"""
    tf_map = {
        "1": "1", "3": "3", "5": "5", "15": "15", "30": "30",
        "60": "1H", "120": "2H", "240": "4H", "D": "1D", "W": "1W"
    }
    tv_tf = tf_map.get(timeframe, "15")
    
    # Always use Heikin-Ashi (candle_type removed from settings)
    tv_chart_style = "8"  # 8 = Heikin-Ashi, 1 = Regular
    
    tv_html = f"""
    <div class="tradingview-widget-container" style="height:380px;">
      <div id="tradingview_123456" style="height:380px;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "autosize": true,
        "symbol": "BYBIT:{symbol}",
        "interval": "{tv_tf}",
        "timezone": "Etc/UTC",
        "theme": "{theme}",
        "style": "{tv_chart_style}",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": true,
        "hide_top_toolbar": false,
        "hide_legend": false,
        "save_image": true,
        "calendar": true,
        "container_id": "tradingview_123456"
      }});
      </script>
    </div>
    """
    return tv_html