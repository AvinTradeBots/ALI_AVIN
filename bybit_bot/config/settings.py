# config/settings.py
import json
import os
from datetime import datetime
import streamlit as st

class ConfigManager:
    """Configuration and storage management"""
    
    CONFIG_FILE = "config_hh.json"
    
    CONFIG_KEYS = [
        "live", "env", "api_key", "api_secret", "confirm_real", 
        "timeframe", "exit_tf", "trade_type", 
        "use_sl", "sl_perc",  # Unified SL
        "use_tp", "tp_perc",  # Unified TP
        "qty_mode", "amount_value", "leverage", "order_type", "limit_price",
        "max_slippage_perc", "use_slippage_filter", "refresh_seconds",
        "use_trailing_sl", "trailing_distance_perc", "trailing_activation_perc","initial_balance_manual",
        "risk_perc", "initial_capital", "current_capital", "total_realized_pnl", 
        "last_pnl_check", "max_reached_price", "min_reached_price",
        "connection_max_retries", "connection_retry_delay", "connection_timeout", 
        "use_telegram", "telegram_bot_token", "telegram_chat_id",
        "multi_symbol_mode", "multi_symbol_list", "max_positions"و
        # 🔥 WebSocket configs
        "use_websocket", "ws_reconnect_delay", "ws_heartbeat_interval"
    ]
    
    @classmethod
    def load_config(cls):
        """Load settings from JSON file"""
        if os.path.exists(cls.CONFIG_FILE):
            try:
                with open(cls.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return {}
        return {}
    
    @classmethod
    def save_config(cls):
        """Save settings to JSON file"""
        data_to_save = {}
        
        for key in cls.CONFIG_KEYS:
            if key in st.session_state:
                value = st.session_state[key]
                
                # Convert datetime to string
                if isinstance(value, datetime):
                    value = value.strftime("%Y-%m-%d %H:%M:%S.%f")
                
                data_to_save[key] = value
        
        try:
            with open(cls.CONFIG_FILE, "w") as f:
                json.dump(data_to_save, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    @classmethod
    def get_defaults(cls):
        """Default settings values"""
        return {
            "logs": [],
            "position": None,
            "live": False,
            "last_run": None,
            "env": "Demo",
            "api_key": "",
            "api_secret": "",
            "confirm_real": False,
            "timeframe": "15",
            "exit_tf": "30",
            "trade_type": "Both",
            "use_sl": True,
            "sl_perc": 0.5,  # Unified SL
            "use_tp": True,
            "tp_perc": 3.2,  # Unified TP
            "qty_mode": "Fixed USDT Amount",
            "amount_value": 100.0,
            "risk_perc": 1.0,
            "initial_capital": 1000.0,
            "current_capital": 1000.0,
            "initial_balance_manual": 1000.0,
            "total_realized_pnl": 0.0,
            "leverage": 1,
            "order_type": "Market",
            "limit_price": 0.0,
            "max_slippage_perc": 0.0,
            "use_slippage_filter": False,
            "refresh_seconds": 30,
            "last_chart_data": None,
            "positions_data": None,
            "pnl_history_data": None,
            "last_position_side": "None",
            "last_action_time": datetime.min,
            "use_trailing_sl": False,
            "trailing_distance_perc": 0.5,
            "trailing_activation_perc": 2.0,
            "max_reached_price": 0.0,
            "min_reached_price": 0.0,
            "last_pnl_check": 0.0,
            "last_exit_reason": "TP/SL/TSL Hit",
            "connection_max_retries": 3,
            "connection_retry_delay": 5,
            "connection_timeout": 10,
            "use_telegram": False,
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "multi_symbol_mode": False,
            "multi_symbol_list": ["BTCUSDT"],
            "max_positions": 5 ,
            # 🔥 WebSocket defaults
            "use_websocket": True,  # WebSocket به صورت پیش‌فرض فعال
            "ws_reconnect_delay": 5,  # ثانیه
            "ws_heartbeat_interval": 20,  # ثانیه
        }
    
    @classmethod
    def initialize_session_state(cls):
        """Initialize session state"""
        file_config = cls.load_config()
        defaults = cls.get_defaults()
        
        for key, default_value in defaults.items():
            if key not in st.session_state:
                value = file_config.get(key, default_value)
                
                # Type conversion
                if key in ["initial_capital", "current_capital", "last_pnl_check", 
                          "amount_value", "risk_perc", "sl_perc", "tp_perc",
                          "trailing_distance_perc", "trailing_activation_perc", 
                          "limit_price", "max_slippage_perc",
                          "total_realized_pnl", "max_reached_price", "min_reached_price"]:
                    value = cls._safe_float(value, default_value)
                
                elif key in ["leverage", "refresh_seconds"]:
                    value = int(cls._safe_float(value, default_value))
                
                elif key == "last_action_time" and isinstance(value, str):
                    try:
                        value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
                    except:
                        value = default_value
                
                st.session_state[key] = value
    
    @staticmethod
    def _safe_float(value, default=0.0):
        """Safe float conversion"""
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default