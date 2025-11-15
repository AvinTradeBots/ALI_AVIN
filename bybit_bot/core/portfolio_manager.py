# core/portfolio_manager.py
import streamlit as st
from datetime import datetime

class PortfolioManager:
    """Multi-symbol portfolio management"""
    
    def __init__(self, max_positions=5, max_risk_per_symbol=2.0):
        self.max_positions = max_positions
        self.max_risk_per_symbol = max_risk_per_symbol
        self.active_symbols = {}
        self.logger = None
    
    def can_open_position(self, symbol):
        """Check if we can open a new position"""
        
        current_positions = len(self.active_symbols)
        
        if current_positions >= self.max_positions:
            return False, f"Max {self.max_positions} positions reached"
        
        if symbol in self.active_symbols:
            if self.logger:
                self.logger.add_log(f"🔒 {symbol} already has position", "DEBUG")
            return False, f"Position exists for {symbol}"
        
        return True, "OK"
    
    def add_position(self, symbol, side, entry_price, quantity, margin_used):
        """Add new position to portfolio"""
        
        if symbol in self.active_symbols:
            if self.logger:
                self.logger.add_log(f"⚠️ Duplicate position {symbol}, updating", "WARNING")
        
        self.active_symbols[symbol] = {
            'side': side,
            'entry_price': entry_price,
            'quantity': quantity,
            'margin_used': margin_used,
            'entry_time': datetime.now().isoformat()
        }
        
        if self.logger:
            self.logger.add_log(f"✅ Added {symbol}: {side} @ {entry_price:.4f}", "DEBUG")
    
    def remove_position(self, symbol):
        """Remove closed position"""
        if symbol in self.active_symbols:
            del self.active_symbols[symbol]
            if self.logger:
                self.logger.add_log(f"🗑️ Removed {symbol}", "DEBUG")
            return True
        return False
    
    def get_total_margin_used(self):
        """Calculate total margin used"""
        total = 0
        for pos in self.active_symbols.values():
            total += pos.get('margin_used', 0)
        return total
    
    def get_available_capital(self, total_capital):
        """Calculate available capital"""
        used = self.get_total_margin_used()
        available = total_capital - used
        return max(available, 0)
    
    def get_capital_per_symbol(self, total_capital):
        """Calculate capital per symbol (equal distribution)"""
        enabled_symbols = st.session_state.get('multi_symbol_list', [])
        
        if not enabled_symbols:
            enabled_symbols = ['BTCUSDT']
        
        num_symbols = len(enabled_symbols)
        capital_per = total_capital / num_symbols
        
        if self.logger:
            self.logger.add_log(f"💰 {capital_per:.2f} per symbol", "DEBUG")
        
        return capital_per
    
    def update_from_api(self, positions_data):
        """Update from API data"""
        
        if positions_data is None:
            if self.logger:
                self.logger.add_log("⚠️ positions_data is None", "WARNING")
            return
        
        old_count = len(self.active_symbols)
        old_symbols = set(self.active_symbols.keys())
        
        self.active_symbols.clear()
        
        active_count = 0
        new_symbols = set()
        
        for pos in positions_data:
            symbol = pos.get('symbol')
            size = float(pos.get('size', 0))
            
            if size > 0:
                self.active_symbols[symbol] = {
                    'side': pos.get('side'),
                    'entry_price': float(pos.get('avgPrice', 0)),
                    'quantity': size,
                    'margin_used': float(pos.get('positionIM', 0)),
                    'unrealized_pnl': float(pos.get('unrealisedPnl', 0))
                }
                active_count += 1
                new_symbols.add(symbol)
        
        closed_symbols = old_symbols - new_symbols
        opened_symbols = new_symbols - old_symbols
        
        if self.logger:
            log_parts = [f"📊 {active_count} active positions"]
            if closed_symbols:
                log_parts.append(f"| Closed: {', '.join(closed_symbols)}")
            if opened_symbols:
                log_parts.append(f"| New: {', '.join(opened_symbols)}")
            self.logger.add_log(" ".join(log_parts), "DEBUG")
    
    def get_portfolio_summary(self):
        """Portfolio summary"""
        total_margin = self.get_total_margin_used()
        total_unrealized_pnl = sum(
            pos.get('unrealized_pnl', 0) 
            for pos in self.active_symbols.values()
        )
        
        avg_pnl_percent = 0
        if self.active_symbols:
            pnl_percents = []
            for pos in self.active_symbols.values():
                pnl = pos.get('unrealized_pnl', 0)
                margin = pos.get('margin_used', 1)
                
                if margin > 0:
                    pnl_percent = (pnl / margin) * 100
                    pnl_percents.append(pnl_percent)
            
            if pnl_percents:
                avg_pnl_percent = sum(pnl_percents) / len(pnl_percents)
        
        return {
            'active_positions': len(self.active_symbols),
            'max_positions': self.max_positions,
            'total_margin_used': total_margin,
            'total_unrealized_pnl': total_unrealized_pnl,
            'avg_unrealized_pnl_percent': avg_pnl_percent,
            'symbols': list(self.active_symbols.keys())
        }
    
    def has_position(self, symbol):
        """Check if symbol has position"""
        return symbol in self.active_symbols
    
    def clear_all(self):
        """Clear all positions"""
        count = len(self.active_symbols)
        self.active_symbols.clear()
        
        if self.logger:
            self.logger.add_log(f"🗑️ Cleared {count} positions", "WARNING")