# core/state_manager.py - COMPLETE VERSION

import threading
import time
from datetime import datetime, timedelta
from core.risk_manager import safe_float
import streamlit as st

class TradingStateManager:
    """
    Unified state manager برای جلوگیری از conflict بین WebSocket و REST
    
    Features:
    - Thread-safe operations با Lock
    - Order deduplication (جلوگیری از duplicate orders)
    - Priority system (WebSocket > REST)
    - Signal cooldown (منع signal مکرر)
    """
    
    def __init__(self, logger=None):
        self.logger = logger
        
        # Lock برای thread safety
        self._lock = threading.Lock()
        
        # State
        self._positions = {}  # {symbol: position_data}
        self._pending_orders = {}  # {symbol: order_data}
        self._last_signal = {}  # {symbol: (signal_type, timestamp)}
        
        # Config
        self.signal_cooldown_seconds = 5  # حداقل 5 ثانیه بین signals
        self.order_timeout_seconds = 10  # order بعد از 10 ثانیه expire می‌شه
    
    def can_place_order(self, symbol, side, source="REST"):
        """
        بررسی که آیا می‌تونیم order بزنیم یا نه
        
        Returns:
            (can_place, reason)
        """
        with self._lock:
            
            # 1. چک کردن pending order
            if symbol in self._pending_orders:
                pending = self._pending_orders[symbol]
                
                # آیا expire شده؟
                if self._is_order_expired(pending):
                    # پاک کن و ادامه بده
                    del self._pending_orders[symbol]
                    self._log(f"🗑️ [STATE] Expired pending order removed: {symbol}", "DEBUG")
                else:
                    # هنوز pending هست
                    return False, f"Pending order exists (placed {pending.get('seconds_ago')}s ago)"
            
            # 2. چک کردن position موجود
            if symbol in self._positions:
                pos = self._positions[symbol]
                current_side = pos.get('side')
                
                # اگه همون side رو داریم، duplicate order هست
                if current_side == side:
                    return False, f"Position already open: {current_side}"
                
                # اگه side مخالف هست، reversal هست (مجاز)
                else:
                    self._log(f"🔄 [STATE] Reversal detected: {current_side} → {side}", "INFO")
                    return True, "Reversal allowed"
            
            # 3. چک کردن signal cooldown
            if symbol in self._last_signal:
                last_type, last_time = self._last_signal[symbol]
                
                seconds_since = (datetime.now() - last_time).total_seconds()
                
                if seconds_since < self.signal_cooldown_seconds:
                    return False, f"Signal cooldown: wait {self.signal_cooldown_seconds - seconds_since:.1f}s"
            
            # 4. همه چیز OK
            return True, "OK"
    
    def register_pending_order(self, symbol, side, quantity, source="REST"):
        """ثبت order pending (قبل از ارسال به API)"""
        with self._lock:
            self._pending_orders[symbol] = {
                'side': side,
                'quantity': quantity,
                'timestamp': datetime.now(),
                'source': source
            }
            
            self._log(f"📝 [STATE] Pending order registered: {symbol} {side} from {source}", "DEBUG")
    
    def confirm_order_filled(self, symbol, side, entry_price, quantity):
        """تایید که order fill شده"""
        with self._lock:
            
            # حذف از pending
            if symbol in self._pending_orders:
                del self._pending_orders[symbol]
            
            # اضافه به positions
            self._positions[symbol] = {
                'side': side,
                'entry_price': entry_price,
                'quantity': quantity,
                'timestamp': datetime.now()
            }
            
            # ثبت signal
            self._last_signal[symbol] = (side, datetime.now())
            
            self._log(f"✅ [STATE] Order confirmed: {symbol} {side} @ {entry_price}", "INFO")
    
    def remove_position(self, symbol):
        """حذف position (بعد از close)"""
        with self._lock:
            if symbol in self._positions:
                del self._positions[symbol]
                self._log(f"🗑️ [STATE] Position removed: {symbol}", "DEBUG")
    
    def update_positions_from_api(self, api_positions):
        """
        بروزرسانی از API (REST)
        این متد state را با API sync می‌کنه
        """
        with self._lock:
            
            # پاک کردن positions قدیمی
            old_symbols = set(self._positions.keys())
            
            # اضافه/update از API
            new_symbols = set()
            
            for pos in api_positions:
                symbol = pos.get('symbol')
                size = safe_float(pos.get('size'))
                
                if size > 0:
                    self._positions[symbol] = {
                        'side': pos.get('side'),
                        'entry_price': safe_float(pos.get('avgPrice')),
                        'quantity': size,
                        'timestamp': datetime.now()
                    }
                    new_symbols.add(symbol)
            
            # پیدا کردن positions بسته شده
            closed = old_symbols - new_symbols
            
            for symbol in closed:
                del self._positions[symbol]
                self._log(f"🔴 [STATE] Position closed (from API): {symbol}", "INFO")
            
            self._log(f"🔄 [STATE] Synced with API: {len(self._positions)} positions", "DEBUG")
    
    def get_position(self, symbol):
        """دریافت position (thread-safe)"""
        with self._lock:
            return self._positions.get(symbol)
    
    def has_position(self, symbol):
        """آیا position باز هست؟"""
        with self._lock:
            return symbol in self._positions
    
    def get_all_positions(self):
        """دریافت همه positions"""
        with self._lock:
            return dict(self._positions)
    
    def cleanup_expired_orders(self):
        """پاک کردن pending orders منقضی شده"""
        with self._lock:
            expired = []
            
            for symbol, order in self._pending_orders.items():
                if self._is_order_expired(order):
                    expired.append(symbol)
            
            for symbol in expired:
                del self._pending_orders[symbol]
                self._log(f"🗑️ [STATE] Removed expired order: {symbol}", "DEBUG")
            
            return len(expired)
    
    def _is_order_expired(self, order):
        """چک کردن انقضای order"""
        timestamp = order.get('timestamp')
        if not timestamp:
            return True
        
        seconds_ago = (datetime.now() - timestamp).total_seconds()
        return seconds_ago > self.order_timeout_seconds
    
    def _log(self, msg, level="INFO"):
        """Log با logger"""
        if self.logger:
            self.logger.add_log(msg, level)
    
    def get_status_summary(self):
        """خلاصه وضعیت"""
        with self._lock:
            return {
                'positions_count': len(self._positions),
                'pending_orders_count': len(self._pending_orders),
                'positions': list(self._positions.keys()),
                'pending': list(self._pending_orders.keys())
            }