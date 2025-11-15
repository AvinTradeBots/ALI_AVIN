# core/websocket_manager.py
import websocket
import json
import threading
import time
from datetime import datetime
import pandas as pd
from queue import Queue

class BybitWebSocketManager:
    """
    WebSocket Manager for real-time Bybit data
    
    Usage:
        ws_manager = BybitWebSocketManager(is_demo=True)
        ws_manager.subscribe_kline('BTCUSDT', '1', callback_function)
        ws_manager.connect()
    """
    
    def __init__(self, is_demo=True, logger=None):
        self.is_demo = is_demo
        self.logger = logger
        
        # URLs
        self.url = (
            "wss://stream-demo.bybit.com/v5/public/linear" if is_demo 
            else "wss://stream.bybit.com/v5/public/linear"
        )
        
        # WebSocket
        self.ws = None
        self.ws_thread = None
        self.is_running = False
        
        # Subscriptions
        self.subscriptions = {}  # {topic: callback}
        
        # Data buffers
        self.kline_buffers = {}  # {symbol: {'1': [candles], '3': [candles]}}
        
        # Message queue
        self.message_queue = Queue()
    
    def connect(self):
        """Connect to WebSocket"""
        if self.is_running:
            self._log("WebSocket already running", "WARNING")
            return
        
        self.is_running = True
        
        # Create WebSocket app
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        # Start in thread
        self.ws_thread = threading.Thread(target=self._run_forever, daemon=True)
        self.ws_thread.start()
        
        self._log("WebSocket connecting...", "INFO")
    
    def disconnect(self):
        """Disconnect from WebSocket"""
        self.is_running = False
        
        if self.ws:
            self.ws.close()
        
        self._log("WebSocket disconnected", "INFO")
    
    def subscribe_kline(self, symbol, interval, callback):
        """
        Subscribe to kline updates
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe ('1', '3', '5', '15', etc.)
            callback: Function to call on each update
                      callback(symbol, interval, candle_data)
        """
        topic = f"kline.{interval}.{symbol}"
        
        self.subscriptions[topic] = callback
        
        # Initialize buffer
        if symbol not in self.kline_buffers:
            self.kline_buffers[symbol] = {}
        
        self.kline_buffers[symbol][interval] = []
        
        # Send subscription message
        if self.ws and self.ws.sock and self.ws.sock.connected:
            self._subscribe(topic)
        
        self._log(f"Subscribed to {topic}", "INFO")
    
    def _subscribe(self, topic):
        """Send subscription message"""
        message = {
            "op": "subscribe",
            "args": [topic]
        }
        
        self.ws.send(json.dumps(message))
    
    def _on_open(self, ws):
        """Called when connection opens"""
        self._log("WebSocket connected!", "SUCCESS")
        
        # Re-subscribe to all topics
        for topic in self.subscriptions.keys():
            self._subscribe(topic)
    
    def _on_message(self, ws, message):
        """Called when message received"""
        try:
            data = json.loads(message)
            
            # Handle subscription confirmation
            if data.get('op') == 'subscribe':
                self._log(f"Subscription confirmed: {data.get('success')}", "DEBUG")
                return
            
            # Handle kline data
            if data.get('topic', '').startswith('kline'):
                self._handle_kline(data)
        
        except Exception as e:
            self._log(f"Error parsing message: {e}", "ERROR")
    
    def _handle_kline(self, data):
        """Process kline data"""
        topic = data.get('topic')  # e.g., "kline.1.BTCUSDT"
        
        if topic not in self.subscriptions:
            return
        
        # Parse topic
        parts = topic.split('.')
        if len(parts) != 3:
            return
        
        _, interval, symbol = parts
        
        # Get kline data
        kline_list = data.get('data', [])
        
        for kline in kline_list:
            # Bybit kline format:
            # {
            #   "start": 1672041600000,
            #   "end": 1672041660000,
            #   "interval": "1",
            #   "open": "16900.5",
            #   "close": "16901.2",
            #   "high": "16902.0",
            #   "low": "16899.8",
            #   "volume": "12.345",
            #   "turnover": "208567.89",
            #   "confirm": false
            # }
            
            candle_data = {
                'timestamp': datetime.fromtimestamp(int(kline['start']) / 1000),
                'open': float(kline['open']),
                'high': float(kline['high']),
                'low': float(kline['low']),
                'close': float(kline['close']),
                'volume': float(kline['volume']),
                'is_closed': kline.get('confirm', False)
            }
            
            # Update buffer
            if symbol in self.kline_buffers and interval in self.kline_buffers[symbol]:
                buffer = self.kline_buffers[symbol][interval]
                
                # Update or append
                if buffer and buffer[-1]['timestamp'] == candle_data['timestamp']:
                    # Update existing candle
                    buffer[-1] = candle_data
                else:
                    # New candle
                    buffer.append(candle_data)
                    
                    # Keep only last 100 candles
                    if len(buffer) > 100:
                        buffer.pop(0)
            
            # Call callback
            callback = self.subscriptions.get(topic)
            if callback:
                try:
                    callback(symbol, interval, candle_data)
                except Exception as e:
                    self._log(f"Callback error: {e}", "ERROR")
    
    def _on_error(self, ws, error):
        """Called on error"""
        self._log(f"WebSocket error: {error}", "ERROR")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Called when connection closes"""
        self._log(f"WebSocket closed: {close_status_code} - {close_msg}", "WARNING")
        
        # Auto-reconnect after 5 seconds
        if self.is_running:
            self._log("Reconnecting in 5 seconds...", "INFO")
            time.sleep(5)
            self.connect()
    
    def _run_forever(self):
        """Run WebSocket in thread"""
        self.ws.run_forever()
    
    def get_klines(self, symbol, interval, limit=100):
        """
        Get buffered klines as DataFrame
        
        Args:
            symbol: Trading pair
            interval: Timeframe
            limit: Number of candles
        
        Returns:
            pd.DataFrame with OHLCV data
        """
        if symbol not in self.kline_buffers or interval not in self.kline_buffers[symbol]:
            return pd.DataFrame()
        
        buffer = self.kline_buffers[symbol][interval]
        
        if not buffer:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(buffer[-limit:])
        df = df.set_index('timestamp')
        
        return df[['open', 'high', 'low', 'close', 'volume']]
    
    def get_latest_candle(self, symbol, interval):
        """Get latest candle (including incomplete)"""
        if symbol not in self.kline_buffers or interval not in self.kline_buffers[symbol]:
            return None
        
        buffer = self.kline_buffers[symbol][interval]
        
        if not buffer:
            return None
        
        return buffer[-1]
    
    def _log(self, msg, level="INFO"):
        """Log message"""
        if self.logger:
            self.logger.add_log(f"[WebSocket] {msg}", level)
        else:
            print(f"[{level}] {msg}")