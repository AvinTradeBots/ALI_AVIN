# strategies/nikki_full.py - Event-Driven WebSocket Version

from strategies.base_strategy import BaseStrategy
from datetime import datetime, timedelta
import streamlit as st

class NIKKIFullWebSocket(BaseStrategy):
    """
    NIKKI Strategy - Pure WebSocket Version
    
    Event-driven with real-time candle updates
    """
    
    STRATEGY_METADATA = {
        'name': 'NIKKI Full (WebSocket)',
        'version': '5.0.0',
        'author': 'NIKKI Team',
        'description': 'Real-time NIKKI with WebSocket - Event Driven',
        'enabled': True,
        'timeframes': ['1', '3', '5', '15'],
        'symbols': ['BTCUSDT', 'ETHUSDT'],
        'requires_websocket': True
    }
    
    def __init__(self, config):
        super().__init__(config)
        
        # State per symbol
        if 'nikki_state' not in st.session_state:
            st.session_state.nikki_state = {}
    
    def get_strategy_name(self):
        return "NIKKI Full - WebSocket (Event-Driven)"
    
    def get_required_candles(self):
        return 50
    
    def on_kline_update(self, symbol, interval, candle_data):
        """
        WebSocket callback - اجرا می‌شه هر بار که candle update می‌شه
        
        Args:
            symbol: نماد
            interval: تایم‌فریم
            candle_data: {
                'timestamp': datetime,
                'open': float,
                'high': float,
                'low': float,
                'close': float,
                'volume': float,
                'is_closed': bool
            }
        """
        
        # Initialize state for symbol
        if symbol not in st.session_state.nikki_state:
            st.session_state.nikki_state[symbol] = {
                'candles': [],
                'last_signal': None,
                'last_signal_time': None,
                'current_position': None,
                'intrabar_check_time': None
            }
        
        state = st.session_state.nikki_state[symbol]
        
        # Update candles buffer
        if candle_data['is_closed']:
            # Candle جدید کامل شد
            state['candles'].append(candle_data)
            
            # فقط 100 شمع آخر را نگه دار
            if len(state['candles']) > 100:
                state['candles'] = state['candles'][-100:]
            
            # Reset intrabar check
            state['intrabar_check_time'] = None
        
        else:
            # Candle در حال شکل‌گیری
            if state['candles']:
                # Update آخرین candle
                state['candles'][-1] = candle_data
        
        # Check signals
        if len(state['candles']) >= 2:
            self._check_signals(symbol, state)
    
    def _check_signals(self, symbol, state):
        """بررسی سیگنال‌ها"""
        
        if len(state['candles']) < 2:
            return
        
        current = state['candles'][-1]
        previous = state['candles'][-2]
        
        # محاسبه رنگ candles (ساده شده)
        current_color = 'green' if current['close'] > current['open'] else 'red'
        previous_color = 'green' if previous['close'] > previous['open'] else 'red'
        
        # دریافت position از state manager
        from main import state_manager
        
        has_position = state_manager.has_position(symbol) if state_manager else False
        position = state_manager.get_position(symbol) if state_manager else None
        
        # ═══════════════════════════════════════
        # EXIT LOGIC (فوری)
        # ═══════════════════════════════════════
        
        if has_position and position:
            side = position.get('side')
            
            # Long exit
            if side == "Buy" and current_color == 'red':
                self._trigger_signal(symbol, 'long_exit', current, "Color Reversal")
                return
            
            # Short exit
            elif side == "Sell" and current_color == 'green':
                self._trigger_signal(symbol, 'short_exit', current, "Color Reversal")
                return
        
        # ═══════════════════════════════════════
        # ENTRY LOGIC (با 10-second check)
        # ═══════════════════════════════════════
        
        if not has_position:
            
            # شمع جدید با رنگ یکسان
            if current_color == previous_color:
                
                # اگه intrabar check نداریم، تنظیم کن
                if not state['intrabar_check_time']:
                    state['intrabar_check_time'] = datetime.now() + timedelta(seconds=10)
                    state['pending_signal'] = current_color
                
                # بررسی 10 ثانیه
                elif datetime.now() >= state['intrabar_check_time']:
                    
                    # اگه رنگ هنوز یکسان هست
                    if current_color == state['pending_signal']:
                        
                        if current_color == 'green':
                            self._trigger_signal(symbol, 'long_entry', current, "10s Confirmed")
                        else:
                            self._trigger_signal(symbol, 'short_entry', current, "10s Confirmed")
                    
                    # Reset
                    state['intrabar_check_time'] = None
                    state['pending_signal'] = None
    
    def _trigger_signal(self, symbol, signal_type, candle, reason):
        """ارسال سیگنال به main loop"""
        
        # ذخیره signal برای main loop
        if 'strategy_signals' not in st.session_state:
            st.session_state.strategy_signals = {}
        
        st.session_state.strategy_signals[symbol] = {
            'type': signal_type,
            'price': candle['close'],
            'reason': reason,
            'timestamp': datetime.now()
        }
        
        # Log
        from main import logger
        if logger:
            logger.add_log(
                f"🎯 [NIKKI] {signal_type.upper()} signal: {symbol} @ {candle['close']:.4f} - {reason}",
                "INFO"
            )
    
    def calculate_signals(self, df_regular, df_ha=None):
        """
        Compatibility method (فقط برای fallback)
        در حالت WebSocket این استفاده نمی‌شه
        """
        return False, False, False, False