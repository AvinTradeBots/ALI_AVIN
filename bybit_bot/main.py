# main.py - COMPLETE WebSocket-First Version
# Version: 6.0.0 - Pure WebSocket

import streamlit as st
import time
from datetime import datetime
import threading

# Import modules
from config.settings import ConfigManager
from core.api_client import BybitAPIClient
from core.position_manager import PositionManager
from core.logger import BotLogger
from core.risk_manager import RiskManager, safe_float
from core.utils import get_tradingview_html
from core.database import TradeDatabase
from core.telegram_notifier import TelegramNotifier

# 🔥 WebSocket imports
from core.bybit_websocket import BybitWebSocketClient
from core.state_manager import TradingStateManager

# Strategy Loader
from strategies import load_strategy, get_available_strategies, get_strategy_info

# UI Components
from ui.components import (
    display_unified_dashboard,
    display_status_banner,
    display_logs,
    display_connection_status,
    display_positions_and_trades_tables,
    display_time_sync,
    display_websocket_status  # 🔥 جدید
)
from ui.sidebar import render_sidebar, show_start_confirmation_modal
from ui.analytics import show_analytics_page
from core.portfolio_manager import PortfolioManager

# =============================================================================
# Streamlit Page Configuration
# =============================================================================
st.set_page_config(
    page_title="Heikin Ashi Bybit Bot - WebSocket", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# Custom CSS
# =============================================================================
st.markdown("""
<style>
/* RTL Support */
html, body, [class*="css"] { 
    direction: rtl; 
    text-align: right; 
    font-family: 'Tahoma', Arial, sans-serif; 
}

section[data-testid="stSidebar"] { 
    right: 0; 
    left: auto; 
    border-left: 1px solid #e6e6e6; 
    border-right: none; 
}

div[data-testid="stSidebarContent"] { 
    direction: rtl; 
    text-align: right; 
}

.stButton>button { 
    border-radius: 6px; 
    padding: 6px 10px; 
    font-weight: 500;
}

div[data-testid="stMetric"] {
    background-color: #f8f9fa;
    padding: 10px;
    border-radius: 5px;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 12px;
    padding: 8px 0;
}

.stTabs [data-baseweb="tab"] {
    padding: 12px 24px;
    background-color: #f0f2f6;
    border-radius: 8px;
    font-size: 18px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    background-color: #e0e4ea;
    transform: translateY(-2px);
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background-color: #4CAF50 !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

.element-container {
    margin-bottom: 0.5rem;
}

/* WebSocket indicator */
.ws-indicator {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 8px;
    animation: pulse 2s infinite;
}

.ws-connected {
    background-color: #28a745;
}

.ws-disconnected {
    background-color: #dc3545;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Initialize Session State
# =============================================================================
if 'initialized' not in st.session_state:
    ConfigManager.initialize_session_state()
    st.session_state['initialized'] = True
    st.session_state['live'] = False
    st.session_state['show_start_confirmation'] = False
    st.session_state['ws_active'] = False

# =============================================================================
# Create Core Objects
# =============================================================================

logger = BotLogger(st.session_state)

# Database
if 'db' not in st.session_state:
    st.session_state.db = TradeDatabase("bot_trades.db")
db = st.session_state.db

# REST API Client (فقط برای actions)
api_client = BybitAPIClient(
    api_key=st.session_state.get('api_key', ''),
    api_secret=st.session_state.get('api_secret', ''),
    is_demo=(st.session_state.get('env', 'Demo') == "Demo"),
    logger=logger
)

api_client.connection_manager.max_retries = st.session_state.get('connection_max_retries', 3)
api_client.connection_manager.retry_delay = st.session_state.get('connection_retry_delay', 5)
api_client.connection_manager.timeout = st.session_state.get('connection_timeout', 10)

# Telegram
telegram = TelegramNotifier(
    bot_token=st.session_state.get('telegram_bot_token'),
    chat_id=st.session_state.get('telegram_chat_id'),
    enabled=st.session_state.get('use_telegram', False)
)

# 🔥 State Manager
if 'state_manager' not in st.session_state:
    st.session_state.state_manager = TradingStateManager(logger=logger)
state_manager = st.session_state.state_manager

# 🔥 WebSocket Client
if 'ws_client' not in st.session_state:
    st.session_state.ws_client = BybitWebSocketClient(
        api_key=st.session_state.get('api_key'),
        api_secret=st.session_state.get('api_secret'),
        is_testnet=(st.session_state.get('env', 'Demo') == "Demo"),
        logger=logger
    )
ws_client = st.session_state.ws_client

# Position Manager (با state_manager)
position_manager = PositionManager(
    api_client=api_client, 
    logger=logger, 
    database=db, 
    telegram=telegram,
    state_manager=state_manager  # 🔥 اضافه شد
)

# Portfolio Manager
if 'portfolio_manager' not in st.session_state:
    st.session_state.portfolio_manager = PortfolioManager(
        max_positions=st.session_state.get('max_positions', 5),
        max_risk_per_symbol=st.session_state.get('max_risk_per_symbol', 2.0)
    )
portfolio_manager = st.session_state.portfolio_manager
portfolio_manager.logger = logger

# Risk Manager
risk_manager = RiskManager()

# =============================================================================
# Strategy Loading
# =============================================================================
try:
    available_strategies = get_available_strategies()
    
    if not available_strategies:
        st.error("❌ No strategies found!")
        st.stop()
    
    if 'selected_strategy' not in st.session_state:
        st.session_state['selected_strategy'] = available_strategies[0]
    
    selected_strategy_name = st.session_state.get('selected_strategy')
    
    if selected_strategy_name not in available_strategies:
        logger.add_log(f"⚠️ Strategy '{selected_strategy_name}' not found", "WARNING")
        selected_strategy_name = available_strategies[0]
        st.session_state['selected_strategy'] = selected_strategy_name
    
    # Load strategy
    strategy = load_strategy(selected_strategy_name, st.session_state)
    st.session_state['strategy_name'] = strategy.get_strategy_name()
    
    logger.add_log(f"✅ Strategy loaded: {selected_strategy_name}", "DEBUG")

except Exception as e:
    logger.add_log(f"❌ Strategy load failed: {e}", "ERROR")
    st.error(f"❌ Error: {e}")
    st.stop()

# =============================================================================
# WebSocket Callbacks
# =============================================================================

def on_position_update(data):
    """Position update callback از WebSocket"""
    logger.add_log(f"📊 [WS] Position update received", "DEBUG")
    # state_manager خودش در _handle_position_update بروز می‌کنه

def on_order_update(data):
    """Order update callback"""
    logger.add_log(f"📋 [WS] Order update received", "DEBUG")

def on_execution_update(data):
    """Execution (fill) callback"""
    execution_list = data.get('data', [])
    for execution in execution_list:
        symbol = execution.get('symbol')
        logger.add_log(f"✅ [WS] Order filled: {symbol}", "SUCCESS")

def on_wallet_update(data):
    """Wallet update callback"""
    logger.add_log(f"💼 [WS] Wallet updated", "DEBUG")

def on_kline_update(symbol, data):
    """Kline update callback - ارسال به strategy"""
    kline_list = data.get('data', [])
    
    if not kline_list:
        return
    
    candle = kline_list[0]
    
    # تبدیل به فرمت strategy
    candle_data = {
        'timestamp': datetime.fromtimestamp(int(candle['start']) / 1000),
        'open': float(candle['open']),
        'high': float(candle['high']),
        'low': float(candle['low']),
        'close': float(candle['close']),
        'volume': float(candle['volume']),
        'is_closed': candle.get('confirm', False)
    }
    
    # ارسال به strategy (اگه متد داره)
    if hasattr(strategy, 'on_kline_update'):
        try:
            interval = data.get('topic', '').split('.')[1]
            strategy.on_kline_update(symbol, interval, candle_data)
        except Exception as e:
            logger.add_log(f"❌ Strategy kline handler error: {e}", "ERROR")

# =============================================================================
# WebSocket Connection Management
# =============================================================================

def start_websocket():
    """شروع WebSocket connections"""
    
    if ws_client.is_connected():
        logger.add_log("⚠️ WebSocket already connected", "WARNING")
        return
    
    logger.add_log("🔄 Starting WebSocket connections...", "INFO")
    
    # Subscribe to private streams
    ws_client.subscribe_position(on_position_update)
    ws_client.subscribe_order(on_order_update)
    ws_client.subscribe_execution(on_execution_update)
    ws_client.subscribe_wallet(on_wallet_update)
    
    # Subscribe to klines for each symbol
    symbols = st.session_state.get('multi_symbol_list', [])
    timeframe = st.session_state.get('timeframe', '15')
    
    for symbol in symbols:
        ws_client.subscribe_kline(
            symbol,
            timeframe,
            lambda data, sym=symbol: on_kline_update(sym, data)
        )
    
    # Connect
    ws_client.connect()
    
    st.session_state['ws_active'] = True
    
    logger.add_log("✅ WebSocket connections established", "SUCCESS")

def stop_websocket():
    """توقف WebSocket"""
    if ws_client.is_connected():
        ws_client.disconnect()
        st.session_state['ws_active'] = False
        logger.add_log("🔌 WebSocket disconnected", "INFO")

# =============================================================================
# Strategy Execution (Event-Driven)
# =============================================================================

def execute_strategy_signal(symbol, signal_type, signal_data):
    """
    اجرای سیگنال استراتژی (Event-driven)
    
    این تابع فقط وقتی فراخوانی می‌شه که strategy یک signal بده
    دیگه polling نداریم!
    """
    
    logger.add_log(f"🎯 [SIGNAL] {signal_type} for {symbol}", "INFO")
    
    # بررسی با state manager
    if signal_type in ['long_entry', 'short_entry']:
        side = "Buy" if signal_type == 'long_entry' else "Sell"
        
        can_place, reason = state_manager.can_place_order(symbol, side, source="STRATEGY")
        
        if not can_place:
            logger.add_log(f"⛔ [SIGNAL] Blocked: {reason}", "WARNING")
            return
        
        # باز کردن position
        open_new_position(symbol, side, signal_data)
    
    elif signal_type in ['long_exit', 'short_exit']:
        # بستن position
        close_existing_position(symbol, signal_data.get('reason', 'Strategy Exit'))

def open_new_position(symbol, side, signal_data):
    """باز کردن position جدید"""
    
    # دریافت قیمت فعلی
    current_price = signal_data.get('price', 0)
    
    if current_price == 0:
        logger.add_log(f"❌ Invalid price for {symbol}", "ERROR")
        return
    
    # محاسبه quantity
    qty_mode = st.session_state.get('qty_mode', 'Fixed USDT Amount')
    leverage = st.session_state.get('leverage', 1)
    
    if qty_mode == "Fixed USDT Amount":
        amount_value = st.session_state.get('amount_value', 100.0)
        params = {
            'amount_value': amount_value,
            'risk_perc': st.session_state.get('risk_perc', 1.0),
            'current_capital': amount_value,
            'sl_perc': st.session_state.get('sl_perc', 0.5)
        }
    elif qty_mode == "Fixed Risk %":
        total_capital = st.session_state.get('current_capital', 1000.0)
        params = {
            'amount_value': 0,
            'risk_perc': st.session_state.get('risk_perc', 1.0),
            'current_capital': total_capital,
            'sl_perc': st.session_state.get('sl_perc', 0.5)
        }
    else:
        params = {'amount_value': 100.0, 'risk_perc': 1.0, 'current_capital': 100.0, 'sl_perc': 0.5}
    
    try:
        target_qty = risk_manager.calculate_position_size(qty_mode, params, current_price, leverage)
        instruments = st.session_state.get('instruments', [])
        qty, _, _ = risk_manager.normalize_quantity(instruments, symbol, target_qty, current_price)
        
        logger.add_log(f"📊 {symbol}: Qty={qty:.6f} | Leverage={leverage}x", "DEBUG")
    
    except ValueError as e:
        logger.add_log(f"❌ Size calculation failed: {e}", "ERROR")
        return
    
    # ثبت order در state manager
    state_manager.register_pending_order(symbol, side, qty, source="STRATEGY")
    
    # ارسال order به API
    order_result = position_manager.open_position(
        symbol, side, qty,
        order_type=st.session_state.get('order_type', 'Market'),
        price=st.session_state.get('limit_price', current_price),
        leverage=leverage
    )
    
    if order_result.get("retCode") == 0:
        logger.add_log(f"✅ Order placed successfully: {side} {symbol}", "SUCCESS")
        
        # Set TP/SL
        if st.session_state.get('use_tp') or st.session_state.get('use_sl'):
            tp_price = None
            sl_price = None
            
            if st.session_state.get('use_tp'):
                perc = st.session_state.get('tp_perc', 3.0)
                tp_price = current_price * (1 + perc/100) if side == "Buy" else current_price * (1 - perc/100)
            
            if st.session_state.get('use_sl'):
                perc = st.session_state.get('sl_perc', 0.5)
                sl_price = current_price * (1 - perc/100) if side == "Buy" else current_price * (1 + perc/100)
            
            if tp_price or sl_price:
                position_manager.set_tp_sl(symbol, side, tp_price, sl_price)
    else:
        logger.add_log(f"❌ Order failed: {order_result.get('retMsg')}", "ERROR")

def close_existing_position(symbol, reason="Strategy Exit"):
    """بستن position موجود"""
    
    # دریافت position از state manager
    position = state_manager.get_position(symbol)
    
    if not position:
        logger.add_log(f"⚠️ No position to close for {symbol}", "WARNING")
        return
    
    side = position.get('side')
    quantity = position.get('quantity')
    
    # بستن position
    result = position_manager.close_position(symbol, side, quantity, reason)
    
    if result.get("retCode") == 0:
        logger.add_log(f"✅ Position closed: {symbol}", "SUCCESS")
    else:
        logger.add_log(f"❌ Close failed: {result.get('retMsg')}", "ERROR")

# =============================================================================
# REST Fallback (Safety Sync)
# =============================================================================

def rest_fallback_sync():
    """
    REST fallback برای safety
    فقط هر 60 ثانیه یکبار - برای sync کردن state
    """
    try:
        logger.add_log("🔄 [REST] Safety sync...", "DEBUG")
        
        # Fetch positions from API
        symbols = st.session_state.get('multi_symbol_list', [])
        all_positions = []
        
        for symbol in symbols:
            try:
                positions = api_client.get_positions(symbol)
                all_positions.extend(positions)
            except:
                pass
        
        # Sync with state manager
        state_manager.update_positions_from_api(all_positions)
        
        # Update session state
        current_positions = [p for p in all_positions if safe_float(p.get('size')) > 0]
        st.session_state["positions_data"] = current_positions
        
        logger.add_log(f"✅ [REST] Synced {len(current_positions)} positions", "DEBUG")
    
    except Exception as e:
        logger.add_log(f"⚠️ [REST] Sync failed: {e}", "WARNING")

# =============================================================================
# Render Sidebar
# =============================================================================
render_sidebar(api_client, logger)

# =============================================================================
# Show Confirmation Modal
# =============================================================================
if st.session_state.get('show_start_confirmation', False):
    show_start_confirmation_modal(api_client)
    
    if st.session_state.get('live', False):
        st.session_state['show_start_confirmation'] = False

# =============================================================================
# Main Page
# =============================================================================
st.title("🤖 Heikin-Ashi Bybit Bot - WebSocket Edition")

# Display Time Sync
display_time_sync(api_client)

# Success message on bot start
if st.session_state.get('bot_just_started', False):
    st.success("🚀 **Bot Started!** WebSocket connections established.")
    
    # 🔥 Start WebSocket
    start_websocket()
    
    st.balloons()
    st.session_state['bot_just_started'] = False
    time.sleep(2)
    st.rerun()

# WebSocket status indicator
if st.session_state.get('ws_active', False):
    ws_status = ws_client.get_status()
    
    if ws_status['public_connected'] and ws_status['private_connected']:
        st.success("🟢 **WebSocket Active** - Real-time data streaming")
    elif ws_status['public_connected'] or ws_status['private_connected']:
        st.warning("🟡 **WebSocket Partial** - Some connections active")
    else:
        st.error("🔴 **WebSocket Disconnected** - Reconnecting...")

# Unified Dashboard
display_unified_dashboard(api_client, portfolio_manager)
display_status_banner()

st.markdown("---")

# =============================================================================
# TABS
# =============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Live Trading", 
    "📝 Logs", 
    "📈 Analytics", 
    "🌐 WebSocket Status"
])

with tab1:
    symbols_list = st.session_state.get('multi_symbol_list', [])
    display_symbol = symbols_list[0] if symbols_list else 'BTCUSDT'
    
    st.subheader(f"📊 Live Chart - {display_symbol}")
    
    tv_html = get_tradingview_html(
        display_symbol, 
        st.session_state.get('timeframe', '15'), 
        candle_type="Heikin-Ashi",
        theme="dark"
    )
    st.components.v1.html(tv_html, height=500)
    
    st.markdown("---")
    display_positions_and_trades_tables(api_client, db, table_id="live_tab")

with tab2:
    display_logs()

with tab3:
    show_analytics_page(db)

with tab4:
    st.subheader("🌐 WebSocket Status")
    
    if ws_client:
        display_websocket_status(ws_client, state_manager)
    else:
        st.warning("WebSocket client not initialized")
    
    st.markdown("---")
    st.subheader("🔌 Connection Manager")
    display_connection_status(api_client)

# =============================================================================
# Main Loop (Event-Driven با REST Fallback)
# =============================================================================

if st.session_state.get("live", False):
    
    # چک کردن WebSocket
    if not ws_client.is_connected():
        st.error("🔴 WebSocket disconnected! Attempting to reconnect...")
        try:
            start_websocket()
        except:
            pass
    
    # 🔥 Event-driven: فقط یک REST fallback برای safety
    # WebSocket همه چیز را real-time handle می‌کنه
    
    time_to_wait = 60  # هر 60 ثانیه فقط یک sync
    
    # REST fallback (safety only)
    rest_fallback_sync()
    
    # Cleanup expired orders
    if state_manager:
        expired_count = state_manager.cleanup_expired_orders()
        if expired_count > 0:
            logger.add_log(f"🗑️ Cleaned {expired_count} expired orders", "DEBUG")
    
    # Update last run
    st.session_state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    time.sleep(time_to_wait)
    st.rerun()

else:
    # Bot stopped - cleanup WebSocket
    if st.session_state.get('ws_active', False):
        stop_websocket()