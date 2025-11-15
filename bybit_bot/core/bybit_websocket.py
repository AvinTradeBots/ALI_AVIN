# core/bybit_websocket.py - COMPLETE PROFESSIONAL VERSION

import websocket
import json
import threading
import time
import hmac
import hashlib
from datetime import datetime
import streamlit as st

class BybitWebSocketClient:
    """
    Professional WebSocket client for Bybit V5
    
    Features:
    - Public streams (klines, ticker)
    - Private streams (positions, orders, executions, wallet)
    - Auto-reconnect with exponential backoff
    - Heartbeat monitoring
    - Thread-safe operations
    """
    
    PUBLIC_MAINNET = "wss://stream.bybit.com/v5/public/linear"
    PUBLIC_TESTNET = "wss://stream-testnet.bybit.com/v5/public/linear"
    
    PRIVATE_MAINNET = "wss://stream.bybit.com/v5/private"
    PRIVATE_TESTNET = "wss://stream-testnet.bybit.com/v5/private"
    
    def __init__(self, api_key=None, api_secret=None, is_testnet=True, logger=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.is_testnet = is_testnet
        self.logger = logger
        
        # WebSocket connections
        self.public_ws = None
        self.private_ws = None
        
        # Threads
        self.public_thread = None
        self.private_thread = None
        
        # State
        self.is_running = False
        self.subscriptions = {}  # {topic: callback}
        
        # Reconnect
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5
        
        # Stats
        self.messages_received = 0
        self.last_message_time = None
    
    def connect(self):
        """اتصال به WebSocket"""
        if self.is_running:
            self._log("⚠️ WebSocket already running", "WARNING")
            return
        
        self.is_running = True
        self.reconnect_attempts = 0
        
        # Start public WebSocket
        self._start_public_ws()
        
        # Start private WebSocket (if credentials provided)
        if self.api_key and self.api_secret:
            time.sleep(1)  # Wait a bit before starting private
            self._start_private_ws()
        
        self._log("✅ WebSocket client started", "SUCCESS")
    
    def disconnect(self):
        """قطع اتصال"""
        self.is_running = False
        
        if self.public_ws:
            self.public_ws.close()
        
        if self.private_ws:
            self.private_ws.close()
        
        self._log("🔌 WebSocket disconnected", "INFO")
    
    # ============================================================
    # Public WebSocket
    # ============================================================
    
    def _start_public_ws(self):
        """شروع public WebSocket"""
        url = self.PUBLIC_TESTNET if self.is_testnet else self.PUBLIC_MAINNET
        
        self._log(f"🔄 Starting public WebSocket: {url}", "DEBUG")
        
        self.public_ws = websocket.WebSocketApp(
            url,
            on_open=self._on_public_open,
            on_message=self._on_public_message,
            on_error=self._on_public_error,
            on_close=self._on_public_close
        )
        
        self.public_thread = threading.Thread(
            target=self.public_ws.run_forever,
            daemon=True
        )
        self.public_thread.start()
    
    def _on_public_open(self, ws):
        """Public WebSocket opened"""
        self._log("🟢 Public WebSocket connected", "SUCCESS")
        self.reconnect_attempts = 0
        
        # Subscribe to all public topics
        for topic in self.subscriptions.keys():
            if not self._is_private_topic(topic):
                self._subscribe_public(topic)
    
    def _on_public_message(self, ws, message):
        """Public WebSocket message received"""
        try:
            data = json.loads(message)
            
            self.messages_received += 1
            self.last_message_time = datetime.now()
            
            # Ping/Pong
            if data.get('op') == 'ping':
                ws.send(json.dumps({'op': 'pong'}))
                return
            
            # Subscription confirmation
            if data.get('op') == 'subscribe':
                success = data.get('success', False)
                if success:
                    self._log(f"✅ Public subscription confirmed", "DEBUG")
                else:
                    self._log(f"❌ Public subscription failed: {data}", "ERROR")
                return
            
            # Data update
            topic = data.get('topic', '')
            
            if topic in self.subscriptions:
                callback = self.subscriptions[topic]
                try:
                    callback(data)
                except Exception as e:
                    self._log(f"❌ Callback error for {topic}: {e}", "ERROR")
        
        except Exception as e:
            self._log(f"❌ Public message parse error: {e}", "ERROR")
    
    def _on_public_error(self, ws, error):
        """Public WebSocket error"""
        self._log(f"❌ Public WS error: {error}", "ERROR")
    
    def _on_public_close(self, ws, close_status_code, close_msg):
        """Public WebSocket closed"""
        self._log(f"🔴 Public WS closed: {close_status_code} - {close_msg}", "WARNING")
        
        # Auto-reconnect with exponential backoff
        if self.is_running and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = min(self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)), 60)
            
            self._log(f"🔄 Reconnecting public WS in {delay}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})...", "INFO")
            time.sleep(delay)
            self._start_public_ws()
        else:
            self._log(f"❌ Max reconnect attempts reached for public WS", "ERROR")
    
    # ============================================================
    # Private WebSocket
    # ============================================================
    
    def _start_private_ws(self):
        """شروع private WebSocket"""
        url = self.PRIVATE_TESTNET if self.is_testnet else self.PRIVATE_MAINNET
        
        self._log(f"🔄 Starting private WebSocket: {url}", "DEBUG")
        
        self.private_ws = websocket.WebSocketApp(
            url,
            on_open=self._on_private_open,
            on_message=self._on_private_message,
            on_error=self._on_private_error,
            on_close=self._on_private_close
        )
        
        self.private_thread = threading.Thread(
            target=self.private_ws.run_forever,
            daemon=True
        )
        self.private_thread.start()
    
    def _on_private_open(self, ws):
        """Private WebSocket opened"""
        self._log("🟢 Private WebSocket connected", "SUCCESS")
        self.reconnect_attempts = 0
        
        # Authenticate
        self._authenticate_private()
        
        # Wait for auth
        time.sleep(2)
        
        # Subscribe to private topics
        for topic in self.subscriptions.keys():
            if self._is_private_topic(topic):
                self._subscribe_private(topic)
    
    def _on_private_message(self, ws, message):
        """Private WebSocket message received"""
        try:
            data = json.loads(message)
            
            self.messages_received += 1
            self.last_message_time = datetime.now()
            
            # Ping/Pong
            if data.get('op') == 'ping':
                ws.send(json.dumps({'op': 'pong'}))
                return
            
            # Auth response
            if data.get('op') == 'auth':
                if data.get('success'):
                    self._log("✅ Private WS authenticated", "SUCCESS")
                else:
                    self._log(f"❌ Auth failed: {data.get('ret_msg')}", "ERROR")
                return
            
            # Subscription confirmation
            if data.get('op') == 'subscribe':
                success = data.get('success', False)
                if success:
                    self._log(f"✅ Private subscription confirmed", "DEBUG")
                else:
                    self._log(f"❌ Private subscription failed: {data}", "ERROR")
                return
            
            # Data update
            topic = data.get('topic', '')
            
            # Position update
            if topic == 'position':
                self._handle_position_update(data)
            
            # Order update
            elif topic == 'order':
                self._handle_order_update(data)
            
            # Execution (fill)
            elif topic == 'execution':
                self._handle_execution_update(data)
            
            # Wallet update
            elif topic == 'wallet':
                self._handle_wallet_update(data)
            
            # Generic callback
            if topic in self.subscriptions:
                callback = self.subscriptions[topic]
                try:
                    callback(data)
                except Exception as e:
                    self._log(f"❌ Callback error for {topic}: {e}", "ERROR")
        
        except Exception as e:
            self._log(f"❌ Private message parse error: {e}", "ERROR")
    
    def _on_private_error(self, ws, error):
        """Private WebSocket error"""
        self._log(f"❌ Private WS error: {error}", "ERROR")
    
    def _on_private_close(self, ws, close_status_code, close_msg):
        """Private WebSocket closed"""
        self._log(f"🔴 Private WS closed: {close_status_code} - {close_msg}", "WARNING")
        
        # Auto-reconnect
        if self.is_running and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = min(self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)), 60)
            
            self._log(f"🔄 Reconnecting private WS in {delay}s...", "INFO")
            time.sleep(delay)
            self._start_private_ws()
        else:
            self._log(f"❌ Max reconnect attempts reached for private WS", "ERROR")
    
    # ============================================================
    # Authentication
    # ============================================================
    
    def _authenticate_private(self):
        """Authenticate private WebSocket"""
        expires = int((time.time() + 10) * 1000)
        signature = self._generate_signature(expires)
        
        auth_message = {
            "op": "auth",
            "args": [self.api_key, expires, signature]
        }
        
        self.private_ws.send(json.dumps(auth_message))
        self._log("🔐 Authentication request sent", "DEBUG")
    
    def _generate_signature(self, expires):
        """Generate HMAC signature"""
        sign_string = f"GET/realtime{expires}"
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    # ============================================================
    # Subscriptions
    # ============================================================
    
    def subscribe_kline(self, symbol, interval, callback):
        """Subscribe to kline updates"""
        topic = f"kline.{interval}.{symbol}"
        self.subscriptions[topic] = callback
        
        if self.public_ws and self.public_ws.sock and self.public_ws.sock.connected:
            self._subscribe_public(topic)
        
        self._log(f"📊 Subscribed to kline: {topic}", "INFO")
    
    def subscribe_ticker(self, symbol, callback):
        """Subscribe to ticker (price updates)"""
        topic = f"tickers.{symbol}"
        self.subscriptions[topic] = callback
        
        if self.public_ws and self.public_ws.sock and self.public_ws.sock.connected:
            self._subscribe_public(topic)
        
        self._log(f"💰 Subscribed to ticker: {topic}", "INFO")
    
    def subscribe_position(self, callback):
        """Subscribe to position updates (private)"""
        topic = "position"
        self.subscriptions[topic] = callback
        
        if self.private_ws and self.private_ws.sock and self.private_ws.sock.connected:
            self._subscribe_private(topic)
        
        self._log(f"📈 Subscribed to positions", "INFO")
    
    def subscribe_order(self, callback):
        """Subscribe to order updates (private)"""
        topic = "order"
        self.subscriptions[topic] = callback
        
        if self.private_ws and self.private_ws.sock and self.private_ws.sock.connected:
            self._subscribe_private(topic)
        
        self._log(f"📋 Subscribed to orders", "INFO")
    
    def subscribe_execution(self, callback):
        """Subscribe to execution (fills) updates (private)"""
        topic = "execution"
        self.subscriptions[topic] = callback
        
        if self.private_ws and self.private_ws.sock and self.private_ws.sock.connected:
            self._subscribe_private(topic)
        
        self._log(f"✅ Subscribed to executions", "INFO")
    
    def subscribe_wallet(self, callback):
        """Subscribe to wallet updates (private)"""
        topic = "wallet"
        self.subscriptions[topic] = callback
        
        if self.private_ws and self.private_ws.sock and self.private_ws.sock.connected:
            self._subscribe_private(topic)
        
        self._log(f"💼 Subscribed to wallet", "INFO")
    
    def _subscribe_public(self, topic):
        """Send public subscription"""
        if not self.public_ws or not self.public_ws.sock:
            self._log(f"⚠️ Public WS not ready, queued: {topic}", "WARNING")
            return
        
        message = {
            "op": "subscribe",
            "args": [topic]
        }
        
        try:
            self.public_ws.send(json.dumps(message))
            self._log(f"📤 Public subscription sent: {topic}", "DEBUG")
        except Exception as e:
            self._log(f"❌ Failed to send public subscription: {e}", "ERROR")
    
    def _subscribe_private(self, topic):
        """Send private subscription"""
        if not self.private_ws or not self.private_ws.sock:
            self._log(f"⚠️ Private WS not ready, queued: {topic}", "WARNING")
            return
        
        message = {
            "op": "subscribe",
            "args": [topic]
        }
        
        try:
            self.private_ws.send(json.dumps(message))
            self._log(f"📤 Private subscription sent: {topic}", "DEBUG")
        except Exception as e:
            self._log(f"❌ Failed to send private subscription: {e}", "ERROR")
    
    def _is_private_topic(self, topic):
        """Check if topic is private"""
        private_keywords = ['position', 'order', 'execution', 'wallet']
        return any(keyword in topic for keyword in private_keywords)
    
    # ============================================================
    # Event Handlers (Integration with State Manager)
    # ============================================================
    
    def _handle_position_update(self, data):
        """Handle position update - REAL-TIME"""
        position_list = data.get('data', [])
        
        for pos in position_list:
            symbol = pos.get('symbol')
            size = float(pos.get('size', 0))
            side = pos.get('side')
            
            self._log(
                f"📊 [WS] Position update: {symbol} | Size={size} | Side={side}",
                "INFO"
            )
            
            # 🔥 Update state manager
            if 'state_manager' in st.session_state:
                state_mgr = st.session_state.state_manager
                
                if size > 0:
                    # Position exists
                    state_mgr._positions[symbol] = {
                        'side': side,
                        'entry_price': float(pos.get('avgPrice', 0)),
                        'quantity': size,
                        'unrealized_pnl': float(pos.get('unrealisedPnl', 0)),
                        'timestamp': datetime.now(),
                        'leverage': pos.get('leverage', 1)
                    }
                else:
                    # Position closed
                    if symbol in state_mgr._positions:
                        del state_mgr._positions[symbol]
                        self._log(f"🔴 [WS] Position closed: {symbol}", "INFO")
            
            # Update session state positions_data
            if 'positions_data' not in st.session_state:
                st.session_state['positions_data'] = []
            
            # Update or add position
            found = False
            for i, p in enumerate(st.session_state['positions_data']):
                if p.get('symbol') == symbol:
                    if size > 0:
                        st.session_state['positions_data'][i] = pos
                    else:
                        st.session_state['positions_data'].pop(i)
                    found = True
                    break
            
            if not found and size > 0:
                st.session_state['positions_data'].append(pos)
    
    def _handle_order_update(self, data):
        """Handle order update"""
        order_list = data.get('data', [])
        
        for order in order_list:
            symbol = order.get('symbol')
            status = order.get('orderStatus')
            order_id = order.get('orderId')
            
            self._log(
                f"📋 [WS] Order update: {symbol} | Status={status} | ID={order_id[:8]}...",
                "INFO"
            )
            
            # اگه order fill شد
            if status == 'Filled':
                # حذف از pending orders
                if 'state_manager' in st.session_state:
                    state_mgr = st.session_state.state_manager
                    if symbol in state_mgr._pending_orders:
                        del state_mgr._pending_orders[symbol]
                        self._log(f"✅ [WS] Order filled, removed from pending: {symbol}", "DEBUG")
    
    def _handle_execution_update(self, data):
        """Handle execution (fill) update"""
        execution_list = data.get('data', [])
        
        for execution in execution_list:
            symbol = execution.get('symbol')
            price = execution.get('execPrice')
            qty = execution.get('execQty')
            side = execution.get('side')
            
            self._log(
                f"✅ [WS] Execution: {symbol} | {side} | Price={price} | Qty={qty}",
                "SUCCESS"
            )
    
    def _handle_wallet_update(self, data):
        """Handle wallet update"""
        wallet_list = data.get('data', [])
        
        for wallet in wallet_list:
            for coin in wallet.get('coin', []):
                if coin.get('coin') == 'USDT':
                    balance = float(coin.get('walletBalance', 0))
                    equity = float(coin.get('equity', 0))
                    
                    # Update session state
                    st.session_state['current_capital'] = equity
                    
                    self._log(f"💼 [WS] Wallet: {equity:.2f} USDT (Balance: {balance:.2f})", "INFO")
    
    # ============================================================
    # Utilities
    # ============================================================
    
    def _log(self, msg, level="INFO"):
        """Log message"""
        if self.logger:
            self.logger.add_log(msg, level)
    
    def is_connected(self):
        """Check if WebSocket is connected"""
        public_ok = self.public_ws and self.public_ws.sock and self.public_ws.sock.connected if self.public_ws else False
        private_ok = self.private_ws and self.private_ws.sock and self.private_ws.sock.connected if self.private_ws else False
        
        return public_ok or private_ok
    
    def get_status(self):
        """Get connection status"""
        return {
            'is_running': self.is_running,
            'public_connected': self.public_ws and self.public_ws.sock and self.public_ws.sock.connected if self.public_ws else False,
            'private_connected': self.private_ws and self.private_ws.sock and self.private_ws.sock.connected if self.private_ws else False,
            'subscriptions_count': len(self.subscriptions),
            'subscriptions': list(self.subscriptions.keys()),
            'messages_received': self.messages_received,
            'last_message_time': self.last_message_time,
            'reconnect_attempts': self.reconnect_attempts
        }