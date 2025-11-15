# core/risk_manager.py
import math

def safe_float(value, default=0.0):
    """Safe float conversion"""
    if value is None or (isinstance(value, str) and value.strip() == ''):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

class RiskManager:
    """Risk management and position sizing"""
    
    @staticmethod
    def calculate_position_size(mode, params, latest_price, leverage):
        """
        Calculate position size
        
        Args:
            mode: Calculation method
            params: Parameters dictionary
            latest_price: Current price
            leverage: Leverage
        
        Returns:
            target_qty: Calculated quantity
        """
        if latest_price <= 0:
            raise ValueError("Invalid price")
        
        if mode == "Fixed USDT Amount":
            usdt_margin = params.get('amount_value', 100.0)
            target_qty = usdt_margin / latest_price * leverage
            
        elif mode == "Fixed Coin Quantity":
            desired_buying_power = params.get('amount_value', 100.0)
            target_qty = desired_buying_power / latest_price
            
        elif mode == "Fixed Risk %":
            account_equity = params.get('current_capital', 1000.0)
            risk_perc = params.get('risk_perc', 1.0) / 100
            sl_perc = params.get('sl_perc', 0.5) / 100  # Unified SL
            
            if sl_perc == 0:
                raise ValueError("SL distance cannot be zero")
            
            max_risk_usdt = account_equity * risk_perc
            margin_needed = max_risk_usdt / sl_perc
            target_qty = margin_needed / latest_price * leverage
        else:
            raise ValueError(f"Invalid mode: {mode}")
        
        return target_qty
    
    @staticmethod
    def normalize_quantity(instruments, symbol, target_qty, latest_price):
        """Normalize order quantity based on exchange filters"""
        instrument = next((i for i in instruments if i['symbol'] == symbol), None)
        
        if not instrument:
            raise ValueError(f"Symbol {symbol} not found")
        
        lot_size_filter = instrument.get('lotSizeFilter', {})
        price_filter = instrument.get('priceFilter', {})
        
        qty_step = safe_float(lot_size_filter.get('qtyStep', '0.001'))
        min_qty = safe_float(lot_size_filter.get('minOrderQty', '0.001'))
        min_order_value = safe_float(price_filter.get('minOrderVal', '0.0'))
        
        normalized_qty = math.floor(target_qty / qty_step) * qty_step
        
        if normalized_qty < min_qty:
            normalized_qty = min_qty
        
        current_value_usdt = normalized_qty * latest_price
        
        if min_order_value > 0.0 and current_value_usdt < min_order_value:
            required_qty = min_order_value / latest_price
            normalized_qty = math.ceil(required_qty / qty_step) * qty_step
        
        if normalized_qty == 0.0:
            raise ValueError("Calculated quantity is zero")
        
        return normalized_qty, qty_step, min_qty