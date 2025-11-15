# core/api_client.py - COMPLETE FIXED VERSION
import requests
import time
import hmac
import hashlib
import json
import pandas as pd
from core.connection_manager import ConnectionManager

class BybitAPIClient:
    """کلاینت API برای ارتباط با Bybit V5 - FIXED"""
    
    DEMO_HOST = "https://api-demo.bybit.com"
    MAIN_HOST = "https://api.bybit.com"
    RECV_WINDOW = "5000"
    
    def __init__(self, api_key, api_secret, is_demo=True, logger=None):
        self.api_key = api_key.strip() if api_key else ""
        self.api_secret = api_secret.strip() if api_secret else ""
        self.host = self.DEMO_HOST if is_demo else self.MAIN_HOST
        self.logger = logger
        
        # Connection Manager
        self.connection_manager = ConnectionManager(
            max_retries=3,
            retry_delay=5,
            timeout=10
        )
    
    def get_server_time(self):
        """Get Bybit server time (UTC)"""
        path = "/v5/market/time"
        res = self.send_request("GET", path, body=None)
        
        if res.get("retCode") == 0:
            time_now = res.get("result", {}).get("timeNano")
            
            if time_now:
                time_ms = int(time_now) // 1000000
                from datetime import datetime
                dt = datetime.utcfromtimestamp(time_ms / 1000)
                
                return {
                    'server_time': time_ms,
                    'server_time_dt': dt,
                    'server_time_str': dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'utc_offset': 0
                }
        
        from datetime import datetime
        now = datetime.utcnow()
        return {
            'server_time': int(now.timestamp() * 1000),
            'server_time_dt': now,
            'server_time_str': now.strftime('%Y-%m-%d %H:%M:%S'),
            'utc_offset': 0,
            'error': 'Failed to fetch server time'
        }
    
    def _generate_signature(self, ts, param_str):
        """تولید امضای HMAC-SHA256"""
        if param_str:
            sign_string = ts + self.api_key + self.RECV_WINDOW + param_str
        else:
            sign_string = ts + self.api_key + self.RECV_WINDOW
        
        hash_value = hmac.new(
            self.api_secret.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        )
        return hash_value.hexdigest()
    
    def send_request(self, method, path, body=None):
        """ارسال درخواست به API با پشتیبانی retry خودکار"""
        
        @self.connection_manager.with_retry(self.logger)
        def _do_request():
            ts = str(int(time.time() * 1000))
            
            payload_for_sign = ''
            final_body = body
            
            if method == "POST" and body:
                payload_for_sign = json.dumps(body)
            elif method == "GET" and body:
                final_body = {k: str(v) for k, v in body.items()}
                sorted_keys = sorted(final_body.keys())
                payload_for_sign = '&'.join([f"{k}={final_body[k]}" for k in sorted_keys])
            
            headers = {"Content-Type": "application/json"}
            
            if self.api_key and self.api_secret:
                try:
                    sign = self._generate_signature(ts, payload_for_sign)
                    headers.update({
                        "X-BAPI-API-KEY": self.api_key,
                        "X-BAPI-TIMESTAMP": ts,
                        "X-BAPI-SIGN": sign,
                        "X-BAPI-RECV-WINDOW": self.RECV_WINDOW,
                    })
                except Exception as e:
                    return {"retCode": -1, "retMsg": f"Signing error: {e}"}
            
            url = self.host + path
            timeout = self.connection_manager.timeout
            
            if method == "GET":
                if path in ["/v5/market/instruments-info", "/v5/market/kline"]:
                    r = requests.get(url, params=body, timeout=timeout)
                else:
                    r = requests.get(url, params=final_body, headers=headers, timeout=timeout)
            elif method == "POST":
                r = requests.post(url, headers=headers, data=payload_for_sign, timeout=timeout)
            else:
                return {"retCode": -1, "retMsg": f"Unsupported method: {method}"}
            
            r.raise_for_status()
            return r.json()
        
        try:
            return _do_request()
        except Exception as e:
            return {"retCode": -1, "retMsg": f"Request failed after retries: {str(e)}"}
    
    def get_instruments(self):
        """دریافت لیست نمادهای قابل معامله"""
        path = "/v5/market/instruments-info"
        params = {"category": "linear"}
        res = self.send_request("GET", path, params)
        
        if res.get("retCode") == 0:
            return res.get("result", {}).get("list", [])
        return []
    
    def get_klines(self, symbol, interval, limit=500):
        """دریافت داده‌های کندل"""
        path = "/v5/market/kline"
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        res = self.send_request("GET", path, params)
        
        if res.get("retCode") != 0:
            error_code = res.get("retCode", "N/A")
            error_msg = res.get("retMsg", "Unknown error")
            if self.logger:
                self.logger.add_log(
                    f"🚨 API Klines Error ({symbol} @ {interval}): Code {error_code} - {error_msg}",
                    "ERROR"
                )
            return pd.DataFrame()
        
        klines_list = res.get("result", {}).get("list")
        
        if not klines_list:
            if self.logger:
                self.logger.add_log(
                    f"⚠️ API Klines Warning ({symbol} @ {interval}): Success but 0 candles returned.",
                    "WARNING"
                )
            return pd.DataFrame()
        
        df = pd.DataFrame(klines_list, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df = df.iloc[::-1]
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms')
        df = df.astype({'open': float, 'high': float, 'low': float, 'close': float, 'volume': float, 'turnover': float})
        df = df.set_index('timestamp')
        
        if self.logger:
            self.logger.add_log(f"Klines fetched successfully: {len(df)} candles for {symbol} @ {interval}", "DEBUG")
        
        return df
    
    def get_positions(self, symbol):
        """دریافت پوزیشن‌های باز"""
        path = "/v5/position/list"
        params = {"category": "linear", "symbol": symbol}
        res = self.send_request("GET", path, params)
        
        if res.get("retCode") == 0:
            return res.get("result", {}).get("list", [])
        return []
    
    def place_order(self, symbol, side, qty, order_type="Market", price=None, leverage=1):
        """ثبت سفارش جدید"""
        body = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": f"{qty:.8f}",
            "timeInForce": "GTC",
            "isLeverage": 1,
            "leverage": str(leverage),
            "positionIdx": 0,
        }
        
        if order_type == "Limit" and price:
            body["price"] = f"{price:.8f}"
        
        path = "/v5/order/create"
        return self.send_request("POST", path, body)
    
    def close_position(self, symbol, side, size):
        """بستن پوزیشن باز"""
        close_side = "Sell" if side == "Buy" else "Buy"
        
        body = {
            "category": "linear",
            "symbol": symbol,
            "side": close_side,
            "orderType": "Market",
            "qty": str(size),
            "reduceOnly": True,
            "positionIdx": 0,
        }
        
        path = "/v5/order/create"
        return self.send_request("POST", path, body)
    
    def set_tpsl(self, symbol, tp_price=None, sl_price=None):
        """تنظیم Take Profit و Stop Loss"""
        body = {
            "category": "linear",
            "symbol": symbol,
            "tpslMode": "Full",
            "positionIdx": 0,
        }
        
        if tp_price is not None:
            body["takeProfit"] = f"{tp_price:.8f}"
        
        if sl_price is not None:
            body["stopLoss"] = f"{sl_price:.8f}"
        
        if not tp_price and not sl_price:
            return {"retCode": 0, "retMsg": "No action needed"}
        
        path = "/v5/position/trading-stop"
        return self.send_request("POST", path, body)
    
    def test_connection(self):
        """تست اتصال API و دریافت موجودی"""
        path = "/v5/account/wallet-balance"
        params = {"accountType": "UNIFIED"}
        
        res = self.send_request("GET", path, params)
        
        if res.get("retCode") == 0:
            balance = 0.0
            for item in res.get("result", {}).get("list", []):
                for coin_info in item.get("coins", []):
                    if coin_info.get("coin") == "USDT":
                        balance = float(coin_info.get("equity", "0"))
                        break
            return True, balance
        else:
            return False, res.get("retMsg", "Unknown error")
    
    # 🔥 NEW: دریافت اطلاعات order
    def get_order_info(self, order_id, symbol):
        """Get order details by order ID"""
        path = "/v5/order/realtime"
        params = {
            "category": "linear",
            "orderId": order_id,
            "symbol": symbol
        }
        
        res = self.send_request("GET", path, params)
        
        if res.get("retCode") == 0:
            orders = res.get("result", {}).get("list", [])
            if orders:
                return orders[0]
        
        return {}
    
    # 🔥 NEW: دریافت تاریخچه معاملات
    def get_trade_history(self, symbol, limit=50):
        """Get recent trades for a symbol"""
        path = "/v5/execution/list"
        params = {
            "category": "linear",
            "symbol": symbol,
            "limit": limit
        }
        
        res = self.send_request("GET", path, params)
        
        if res.get("retCode") == 0:
            return res.get("result", {}).get("list", [])
        
        return []
    
    def get_connection_status(self):
        """دریافت وضعیت اتصال"""
        return self.connection_manager.get_status_summary()