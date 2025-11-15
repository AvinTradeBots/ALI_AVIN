# strategies/nikki_advanced.py
"""
NIKKI Strategy - Advanced Version (With State Management)

Full Implementation of Original Logic:
- 10-second intrabar entry validation (requires tick data)
- Re-entry immediately after exit
- State machine for trade management

Note: 10-second check requires real-time tick data.
Current implementation uses candle close as approximation.
"""

from strategies.base_strategy import BaseStrategy
from enum import Enum
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd

class TradeState(Enum):
    """Trade states"""
    NO_TRADE = 0
    LONG_OPEN = 1
    SHORT_OPEN = 2
    PENDING_LONG_ENTRY = 3
    PENDING_SHORT_ENTRY = 4

class NIKKIAdvanced(BaseStrategy):
    """
    NIKKI Heikin-Ashi Strategy - Advanced Version with State Management
    
    Entry Conditions:
    - Previous HA candle must be same color
    - Current HA candle confirms (after 10 seconds in original)
    
    Exit Conditions:
    - Color change (immediate exit)
    - TP/SL/TSL (handled externally)
    
    Re-Entry:
    - Immediate after exit if color confirms direction
    - No 10-second waiting period for re-entry
    
    State Machine:
    - NO_TRADE: Waiting for setup
    - PENDING_LONG/SHORT_ENTRY: Waiting for confirmation
    - LONG/SHORT_OPEN: Position active
    """
    
    # Metadata
    STRATEGY_METADATA = {
        'name': 'NIKKI Advanced',
        'version': '2.0.0',
        'author': 'NIKKI Team',
        'description': 'Full NIKKI strategy with state management and re-entry logic',
        'enabled': True,
        'timeframes': ['1', '3', '5'],  # Best for scalping
        'symbols': ['BTCUSDT', 'ETHUSDT'],
    }
    
    def __init__(self, config):
        super().__init__(config)
        
        # State management
        if 'nikki_state' not in st.session_state:
            st.session_state.nikki_state = TradeState.NO_TRADE
        
        if 'nikki_last_color' not in st.session_state:
            st.session_state.nikki_last_color = None
        
        if 'nikki_candle_open_time' not in st.session_state:
            st.session_state.nikki_candle_open_time = None
        
        if 'nikki_entry_pending_time' not in st.session_state:
            st.session_state.nikki_entry_pending_time = None
    
    def get_strategy_name(self):
        return "NIKKI - Heikin-Ashi Advanced (State Machine)"
    
    def get_required_candles(self):
        return 50
    
    def get_ha_color(self, ha_close, ha_open):
        """Get HA candle color"""
        if ha_close > ha_open:
            return 'green'
        elif ha_close < ha_open:
            return 'red'
        else:
            return 'doji'
    
    def reset_state(self):
        """Reset all state variables"""
        st.session_state.nikki_state = TradeState.NO_TRADE
        st.session_state.nikki_last_color = None
        st.session_state.nikki_entry_pending_time = None
    
    def check_reentry_condition(self, current_color):
        """
        Check if immediate re-entry is possible after exit
        
        Args:
            current_color: Current HA candle color
        
        Returns:
            tuple: (can_reentry, direction) - direction is 'long' or 'short'
        """
        if current_color == 'green':
            return True, 'long'
        elif current_color == 'red':
            return True, 'short'
        
        return False, None
    
    def calculate_signals(self, df_regular, df_ha=None):
        """
        Calculate entry/exit signals with state management
        
        Returns:
            tuple: (long_entry, short_entry, long_exit, short_exit)
        """
        
        # Calculate Heikin-Ashi
        if df_ha is None:
            df_ha = self.calculate_heikin_ashi(df_regular.copy())
        
        if len(df_ha) < 2:
            return False, False, False, False
        
        # Get colors
        current_color = self.get_ha_color(
            df_ha['ha_close'].iloc[-1], 
            df_ha['ha_open'].iloc[-1]
        )
        
        previous_color = self.get_ha_color(
            df_ha['ha_close'].iloc[-2], 
            df_ha['ha_open'].iloc[-2]
        )
        
        # Initialize signals
        long_entry = False
        short_entry = False
        long_exit = False
        short_exit = False
        
        current_state = st.session_state.nikki_state
        
        # === EXIT LOGIC (Always check first) ===
        
        if current_state == TradeState.LONG_OPEN:
            # Exit if color turns red
            if current_color == 'red':
                long_exit = True
                
                # Check for immediate re-entry
                can_reentry, reentry_direction = self.check_reentry_condition(current_color)
                
                if can_reentry and reentry_direction == 'short':
                    # Immediate re-entry to short
                    st.session_state.nikki_state = TradeState.SHORT_OPEN
                    st.session_state.nikki_last_color = 'red'
                    short_entry = True  # Signal re-entry
                else:
                    self.reset_state()
                
                return long_entry, short_entry, long_exit, short_exit
        
        elif current_state == TradeState.SHORT_OPEN:
            # Exit if color turns green
            if current_color == 'green':
                short_exit = True
                
                # Check for immediate re-entry
                can_reentry, reentry_direction = self.check_reentry_condition(current_color)
                
                if can_reentry and reentry_direction == 'long':
                    # Immediate re-entry to long
                    st.session_state.nikki_state = TradeState.LONG_OPEN
                    st.session_state.nikki_last_color = 'green'
                    long_entry = True  # Signal re-entry
                else:
                    self.reset_state()
                
                return long_entry, short_entry, long_exit, short_exit
        
        # === ENTRY LOGIC ===
        
        if current_state == TradeState.NO_TRADE:
            
            # Check for LONG setup
            if previous_color == 'green' and current_color == 'green':
                # In original: wait 10 seconds
                # In simplified: enter immediately
                
                # Option 1: Immediate entry (simplified)
                if self.config.get('nikki_immediate_entry', True):
                    long_entry = True
                    st.session_state.nikki_state = TradeState.LONG_OPEN
                    st.session_state.nikki_last_color = 'green'
                
                # Option 2: Pending entry (for future tick-based implementation)
                else:
                    st.session_state.nikki_state = TradeState.PENDING_LONG_ENTRY
                    st.session_state.nikki_last_color = 'green'
                    st.session_state.nikki_entry_pending_time = datetime.now()
            
            # Check for SHORT setup
            elif previous_color == 'red' and current_color == 'red':
                
                # Option 1: Immediate entry (simplified)
                if self.config.get('nikki_immediate_entry', True):
                    short_entry = True
                    st.session_state.nikki_state = TradeState.SHORT_OPEN
                    st.session_state.nikki_last_color = 'red'
                
                # Option 2: Pending entry
                else:
                    st.session_state.nikki_state = TradeState.PENDING_SHORT_ENTRY
                    st.session_state.nikki_last_color = 'red'
                    st.session_state.nikki_entry_pending_time = datetime.now()
        
        # === PENDING ENTRY VALIDATION ===
        # (For future tick-based implementation)
        
        elif current_state == TradeState.PENDING_LONG_ENTRY:
            # Validate color hasn't changed
            if current_color == 'green':
                long_entry = True
                st.session_state.nikki_state = TradeState.LONG_OPEN
            else:
                # Setup failed, reset
                self.reset_state()
        
        elif current_state == TradeState.PENDING_SHORT_ENTRY:
            # Validate color hasn't changed
            if current_color == 'red':
                short_entry = True
                st.session_state.nikki_state = TradeState.SHORT_OPEN
            else:
                # Setup failed, reset
                self.reset_state()
        
        return long_entry, short_entry, long_exit, short_exit
    
    def get_state_info(self):
        """Get current strategy state (for debugging)"""
        return {
            'state': st.session_state.nikki_state.name,
            'last_color': st.session_state.nikki_last_color,
            'pending_time': st.session_state.nikki_entry_pending_time
        }