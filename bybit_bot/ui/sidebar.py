# ui/sidebar.py - COMPLETE FIXED VERSION
import streamlit as st
from config.settings import ConfigManager
import time

def render_sidebar(api_client, logger):
    """Render settings sidebar"""
    
    with st.sidebar:
        st.title("Heikin-Ashi Bot")
        
        # ============================================================
        # 1 - Environment & API
        # ============================================================
        st.subheader("1️⃣ Environment & API")
        
        env = st.radio("Environment", options=["Demo", "Mainnet"], 
                      index=["Demo", "Mainnet"].index(st.session_state.env), 
                      key="env", on_change=ConfigManager.save_config)
        
        api_key = st.text_input("API Key", type="password", 
                               value=st.session_state.api_key or "", 
                               key="api_key", on_change=ConfigManager.save_config)
        
        api_secret = st.text_input("API Secret", type="password", 
                                  value=st.session_state.api_secret or "", 
                                  key="api_secret", on_change=ConfigManager.save_config)
        
        if st.session_state.env == "Mainnet":
            st.warning("⚠️ MAINNET — Real Money!")
            st.checkbox("Confirm real trading", 
                       value=st.session_state.confirm_real, 
                       key="confirm_real", on_change=ConfigManager.save_config)
        
        if st.button("🔌 Test API Connection", use_container_width=True):
            success, result = api_client.test_connection()
            if success:
                st.success(f"✅ Connected! Balance: {result:.2f} USDT")
            else:
                st.error(f"❌ Failed: {result}")
        
        st.markdown("---")
        
        # ============================================================
        # 1.5 - Initial Capital (Manual Input)
        # ============================================================
        st.subheader("💰 Initial Capital")
        
        st.number_input(
            "Starting Balance (USDT)",
            min_value=10.0,
            max_value=1000000.0,
            value=st.session_state.get('initial_balance_manual', 1000.0),
            step=100.0,
            key="initial_balance_manual",
            on_change=ConfigManager.save_config,
            help="Starting capital when bot starts"
        )
        
        st.caption("💡 Or sync from exchange in confirmation modal")
        
        st.markdown("---")
        
        # ============================================================
        # 2 - Multi-Symbol Trading
        # ============================================================
        st.subheader("2️⃣ Multi-Symbol Trading")
        
        if "instruments" not in st.session_state or not st.session_state.instruments:
            st.session_state.instruments = api_client.get_instruments()
        
        instruments = st.session_state.instruments
        all_symbols = sorted({it['symbol'] for it in instruments if it.get('status') == 'Trading'})
        
        selected_symbols = st.multiselect(
            "Select Symbols",
            options=all_symbols,
            default=st.session_state.get('multi_symbol_list', ['BTCUSDT', 'ETHUSDT']),
            key="multi_symbol_list_selector"
        )
        
        st.session_state['multi_symbol_list'] = selected_symbols
        st.session_state['multi_symbol_mode'] = len(selected_symbols) > 0
        
        st.number_input(
            "Max Positions",
            min_value=1,
            max_value=10,
            value=st.session_state.get('max_positions', 5),
            key="max_positions",
            on_change=ConfigManager.save_config
        )
        
        if selected_symbols:
            capital = st.session_state.get('initial_balance_manual', 1000)
            per_symbol = capital / len(selected_symbols)
            st.caption(f"💰 ~{per_symbol:.2f} USDT per symbol")
        
        st.markdown("---")
        
        # ============================================================
        # 3 - Timeframes (TradingView style)
        # ============================================================
        st.subheader("3️⃣ Timeframes")
        
        tf_display = {
            "1": "1m", "3": "3m", "5": "5m", "15": "15m", "30": "30m",
            "60": "1h", "120": "2h", "240": "4h", "D": "1D", "W": "1W"
        }
        
        tf_options = list(tf_display.keys())
        tf_labels = [tf_display[k] for k in tf_options]
        
        current_tf = st.session_state.get('timeframe', '15')
        current_idx = tf_options.index(current_tf) if current_tf in tf_options else 3
        
        selected_tf_idx = st.selectbox(
            "Entry Timeframe",
            options=range(len(tf_options)),
            format_func=lambda x: tf_labels[x],
            index=current_idx,
            key="timeframe_selector"
        )
        st.session_state['timeframe'] = tf_options[selected_tf_idx]
        
        current_exit_tf = st.session_state.get('exit_tf', '30')
        current_exit_idx = tf_options.index(current_exit_tf) if current_exit_tf in tf_options else 4
        
        selected_exit_tf_idx = st.selectbox(
            "Exit Timeframe",
            options=range(len(tf_options)),
            format_func=lambda x: tf_labels[x],
            index=current_exit_idx,
            key="exit_timeframe_selector"
        )
        st.session_state['exit_tf'] = tf_options[selected_exit_tf_idx]
        
        ConfigManager.save_config()
        
        st.markdown("---")
        
        # ============================================================
        # 3.5 - Strategy Selection (🔥 NEW)
        # ============================================================
        st.subheader("🎯 Strategy")
        
        # Get available strategies
        from strategies import get_available_strategies, get_strategy_info
        
        available_strategies = get_available_strategies()
        
        if not available_strategies:
            st.error("❌ No strategies found!")
        else:
            # Current selected strategy
            current_strategy = st.session_state.get('selected_strategy', available_strategies[0])
            
            # Ensure current strategy exists
            if current_strategy not in available_strategies:
                current_strategy = available_strategies[0]
                st.session_state['selected_strategy'] = current_strategy
            
            # Strategy selector
            selected_strategy = st.selectbox(
                "Select Strategy",
                options=available_strategies,
                index=available_strategies.index(current_strategy),
                key="strategy_selector"
            )
            
            # Update session state
            st.session_state['selected_strategy'] = selected_strategy
            
            # Show strategy info
            strategy_info = get_strategy_info(selected_strategy)
            
            if strategy_info:
                with st.expander("ℹ️ Strategy Details"):
                    st.write(f"**Version:** {strategy_info.get('version', 'N/A')}")
                    st.write(f"**Author:** {strategy_info.get('author', 'Unknown')}")
                    st.write(f"**Description:** {strategy_info.get('description', 'No description')}")
                    
                    # Recommended timeframes
                    recommended_tf = strategy_info.get('timeframes', [])
                    if recommended_tf:
                        st.caption(f"📊 Recommended TF: {', '.join(recommended_tf)}")
                    
                    # Recommended symbols
                    recommended_symbols = strategy_info.get('symbols', [])
                    if recommended_symbols:
                        st.caption(f"💱 Works well with: {', '.join(recommended_symbols)}")
            
            # Save config
            ConfigManager.save_config()
        
        st.markdown("---")

        
        # ============================================================
        # 4 - Trade Direction
        # ============================================================
        st.subheader("4️⃣ Trade Direction")
        
        trade_options = ["Both", "Long Only", "Short Only"]
        st.selectbox("Allowed Trades", options=trade_options, 
                    index=trade_options.index(st.session_state.get('trade_type', 'Both')), 
                    key="trade_type", on_change=ConfigManager.save_config)
        
        st.markdown("---")
        
        # ============================================================
        # 5 - Risk Management (Unified SL/TP)
        # ============================================================
        st.subheader("5️⃣ Risk Management")
        
        st.checkbox("Use Stop-Loss", value=st.session_state.get('use_sl', True), 
                   key="use_sl", on_change=ConfigManager.save_config)
        
        st.number_input("Stop-Loss %", min_value=0.1, max_value=50.0, 
                       value=st.session_state.get('sl_perc', 0.5), 
                       step=0.1, format="%.1f", 
                       key="sl_perc", on_change=ConfigManager.save_config,
                       disabled=not st.session_state.get('use_sl', True))
        
        st.checkbox("Use Take-Profit", value=st.session_state.get('use_tp', True), 
                   key="use_tp", on_change=ConfigManager.save_config)
        
        st.number_input("Take-Profit %", min_value=0.1, max_value=50.0, 
                       value=st.session_state.get('tp_perc', 3.0), 
                       step=0.1, format="%.1f", 
                       key="tp_perc", on_change=ConfigManager.save_config,
                       disabled=not st.session_state.get('use_tp', True))
        
        st.markdown("---")
        st.subheader("🚂 Trailing Stop Loss")
        
        use_trailing = st.checkbox("Enable Trailing SL", 
                                   value=st.session_state.get('use_trailing_sl', False), 
                                   key="use_trailing_sl", on_change=ConfigManager.save_config)
        
        if use_trailing:
            st.number_input(
                "Activation Threshold %", 
                value=st.session_state.get('trailing_activation_perc', 2.0), 
                min_value=0.1, max_value=10.0, step=0.1, format="%.1f",
                key="trailing_activation_perc", 
                on_change=ConfigManager.save_config,
                help="Profit required before TSL activates"
            )
        
        st.number_input(
            "Trailing Distance %", 
            value=st.session_state.get('trailing_distance_perc', 0.5), 
            min_value=0.1, max_value=5.0, step=0.1, format="%.1f",
            key="trailing_distance_perc", 
            on_change=ConfigManager.save_config,
            disabled=not use_trailing,
            help="Distance from peak/low"
        )
        
        st.markdown("---")
        
        # ============================================================
        # 6 - Position Size
        # ============================================================
        st.subheader("6️⃣ Position Size")
        
        qty_mode_options = ["Fixed USDT Amount", "Fixed Coin Quantity", "Fixed Risk %"]
        st.radio("Size Mode", options=qty_mode_options, 
                index=qty_mode_options.index(st.session_state.get('qty_mode', 'Fixed USDT Amount')), 
                key="qty_mode", on_change=ConfigManager.save_config)
        
        st.number_input("Leverage", min_value=1, max_value=125, 
                       value=st.session_state.get('leverage', 1), step=1,
                       key="leverage", on_change=ConfigManager.save_config)
        
        if st.session_state.qty_mode == "Fixed USDT Amount":
            st.number_input("Trade Size (USDT)", 
                           min_value=1.0, max_value=1000000.0, 
                           value=st.session_state.get('amount_value', 100.0), step=10.0,
                           key="amount_value", on_change=ConfigManager.save_config)
        
        elif st.session_state.qty_mode == "Fixed Coin Quantity":
            st.number_input("Desired Buying Power (USDT)", 
                           min_value=1.0, max_value=1000000.0, 
                           value=st.session_state.get('amount_value', 100.0), step=10.0,
                           key="amount_value", on_change=ConfigManager.save_config)
        
        elif st.session_state.qty_mode == "Fixed Risk %":
            st.number_input("Risk per Trade %", 
                           min_value=0.1, max_value=5.0, 
                           value=st.session_state.get('risk_perc', 1.0), step=0.1,
                           key="risk_perc", on_change=ConfigManager.save_config)
        
        st.markdown("---")
        
        # ============================================================
        # 7 - Order Type
        # ============================================================
        st.subheader("7️⃣ Order Type")
        
        order_type_options = ["Market", "Limit"]
        st.selectbox("Order Type", options=order_type_options, 
                    index=order_type_options.index(st.session_state.get('order_type', 'Market')), 
                    key="order_type", on_change=ConfigManager.save_config)
        
        if st.session_state.order_type == "Limit":
            st.number_input("Limit Price", min_value=0.0,
                           value=st.session_state.get('limit_price', 0.0),
                           step=0.01, format="%.8f",
                           key="limit_price", on_change=ConfigManager.save_config)
        
        st.markdown("---")
        
        # ============================================================
        # 8 - Connection
        # ============================================================
        st.subheader("8️⃣ Connection")
        
        st.number_input("Max Retries", min_value=1, max_value=10,
                       value=st.session_state.get('connection_max_retries', 3),
                       key="connection_max_retries", on_change=ConfigManager.save_config)
        
        st.number_input("Retry Delay (s)", min_value=1, max_value=30,
                       value=st.session_state.get('connection_retry_delay', 5),
                       key="connection_retry_delay", on_change=ConfigManager.save_config)
        
        st.number_input("Request Timeout (s)", min_value=5, max_value=60,
                       value=st.session_state.get('connection_timeout', 10),
                       key="connection_timeout", on_change=ConfigManager.save_config)
        
        st.markdown("---")
        
        # ============================================================
        # 9 - Telegram
        # ============================================================
        st.subheader("9️⃣ Telegram")
        
        st.checkbox("Enable Telegram", value=st.session_state.get('use_telegram', False),
                   key="use_telegram", on_change=ConfigManager.save_config)
        
        if st.session_state.use_telegram:
            st.text_input("Bot Token", type="password",
                         value=st.session_state.get('telegram_bot_token', ''),
                         key="telegram_bot_token", on_change=ConfigManager.save_config)
            
            st.text_input("Chat ID",
                         value=st.session_state.get('telegram_chat_id', ''),
                         key="telegram_chat_id", on_change=ConfigManager.save_config)
            
            if st.button("🧪 Test Telegram", use_container_width=True):
                from core.telegram_notifier import TelegramNotifier
                test_tg = TelegramNotifier(
                    bot_token=st.session_state.telegram_bot_token,
                    chat_id=st.session_state.telegram_chat_id,
                    enabled=True
                )
                result = test_tg.send_message("✅ Test successful!")
                if result:
                    st.success("✅ Message sent!")
                else:
                    st.error("❌ Failed")
        
        st.markdown("---")
        
        # ============================================================
        # START/STOP BUTTONS (Styled)
        # ============================================================
        st.markdown("### 🎮 Bot Control")
        
        # Start Button (Green)
        if not st.session_state.get('live', False):
            st.markdown("""
                <style>
                div.stButton > button[key="start_bot_sidebar"] {
                    background: linear-gradient(135deg, #28a745 0%, #20c997 100%) !important;
                    color: white !important;
                    font-size: 18px !important;
                    font-weight: bold !important;
                    padding: 15px !important;
                    border: none !important;
                    border-radius: 10px !important;
                    box-shadow: 0 4px 15px rgba(40, 167, 69, 0.4) !important;
                    width: 100% !important;
                }
                div.stButton > button[key="start_bot_sidebar"]:hover {
                    transform: translateY(-2px) !important;
                    box-shadow: 0 6px 20px rgba(40, 167, 69, 0.6) !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            if st.button("🟢 START BOT", 
                        key="start_bot_sidebar", 
                        use_container_width=True):
                st.session_state['show_start_confirmation'] = True
                st.rerun()
        
        # Stop Button (Red)
        else:
            st.markdown("""
                <style>
                div.stButton > button[key="stop_bot_sidebar"] {
                    background: linear-gradient(135deg, #dc3545 0%, #c82333 100%) !important;
                    color: white !important;
                    font-size: 18px !important;
                    font-weight: bold !important;
                    padding: 15px !important;
                    border: none !important;
                    border-radius: 10px !important;
                    box-shadow: 0 4px 15px rgba(220, 53, 69, 0.4) !important;
                    width: 100% !important;
                }
                div.stButton > button[key="stop_bot_sidebar"]:hover {
                    transform: translateY(-2px) !important;
                    box-shadow: 0 6px 20px rgba(220, 53, 69, 0.6) !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            if st.button("🔴 STOP BOT", 
                        key="stop_bot_sidebar", 
                        use_container_width=True):
                stop_bot_callback()
                st.rerun()


# ui/sidebar.py - فقط بخش show_start_confirmation_modal
# ui/sidebar.py - روش ساده‌تر

# @st.dialog("⚠️ Confirm Bot Start", width="large")
# def show_start_confirmation_modal(api_client):
#     """Show confirmation modal - SIMPLE VERSION"""
    
#     # ... همه بخش‌های قبلی بدون تغییر ...
    
#     # Confirmation buttons
#     st.markdown("---")
#     col1, col2 = st.columns(2)
    
#     with col1:
#         if st.button("✅ CONFIRM & START", 
#                     type="primary", 
#                     use_container_width=True,
#                     disabled=not can_start,
#                     key="confirm_start_btn"):
            
#             # Directly set values
#             initial_capital = st.session_state.get('initial_balance_manual', 1000.0)
            
#             st.session_state["initial_capital"] = initial_capital
#             st.session_state["current_capital"] = initial_capital
#             st.session_state["total_realized_pnl"] = 0.0
#             st.session_state["live"] = True
#             st.session_state['show_start_confirmation'] = False
#             st.session_state['bot_just_started'] = True  # 🔥 NEW FLAG
            
#             # Save config
#             ConfigManager.save_config()
            
#             # Log
#             from core.logger import BotLogger
#             logger = BotLogger(st.session_state)
#             logger.add_log(f"✅ BOT STARTED! Balance: {initial_capital:.2f} USDT", "SUCCESS")
            
#             # Send telegram
#             if st.session_state.get('use_telegram', False):
#                 try:
#                     from core.telegram_notifier import TelegramNotifier
#                     telegram = TelegramNotifier(
#                         bot_token=st.session_state.get('telegram_bot_token'),
#                         chat_id=st.session_state.get('telegram_chat_id'),
#                         enabled=True
#                     )
#                     telegram.notify_bot_started(initial_capital)
#                 except:
#                     pass
            
#             # Rerun
#             st.rerun()
    
#     with col2:
#         if st.button("❌ CANCEL", use_container_width=True, key="cancel_start_btn"):
#             st.session_state['show_start_confirmation'] = False
#             st.rerun()





# @st.dialog("⚠️ Confirm Bot Start", width="large")
# def show_start_confirmation_modal(api_client):
#     """Show confirmation modal before starting bot"""
    
#     st.markdown("### 📋 Review Your Settings")
    
#     # Environment
#     st.markdown("#### 🌍 Environment")
#     env_emoji = "🔴" if st.session_state.env == "Mainnet" else "🟢"
#     st.info(f"{env_emoji} **{st.session_state.env}** {'(REAL MONEY!)' if st.session_state.env == 'Mainnet' else '(Demo)'}")
    
#     # Initial Capital
#     st.markdown("#### 💰 Capital")
#     col1, col2 = st.columns(2)
    
#     with col1:
#         use_manual = st.radio(
#             "Capital Source",
#             ["Manual Input", "Sync from Exchange"],
#             index=0,
#             key="capital_source_choice"
#         )
    
#     with col2:
#         if use_manual == "Manual Input":
#             initial_capital = st.session_state.get('initial_balance_manual', 1000.0)
#             st.metric("Starting Balance", f"{initial_capital:.2f} USDT")
#         else:
#             if st.button("🔄 Fetch Balance Now", use_container_width=True):
#                 success, balance = api_client.test_connection()
#                 if success:
#                     st.session_state['fetched_balance'] = balance
#                     st.success(f"✅ Fetched: {balance:.2f} USDT")
#                     st.rerun()
#                 else:
#                     st.error(f"❌ Failed: {balance}")
            
#             fetched_balance = st.session_state.get('fetched_balance', 0.0)
#             if fetched_balance > 0:
#                 st.metric("Exchange Balance", f"{fetched_balance:.2f} USDT")
#                 initial_capital = fetched_balance
#             else:
#                 st.warning("⚠️ Click 'Fetch Balance Now'")
#                 initial_capital = st.session_state.get('initial_balance_manual', 1000.0)
    
#     st.markdown("---")
    
#     # Symbols
#     st.markdown("#### 🎯 Symbols")
#     symbols = st.session_state.get('multi_symbol_list', [])
#     if symbols:
#         st.write(", ".join(symbols))
#     else:
#         st.error("❌ No symbols selected!")
    
#     col1, col2 = st.columns(2)
#     with col1:
#         st.metric("Max Positions", st.session_state.get('max_positions', 5))
#     with col2:
#         if symbols:
#             capital_per = initial_capital / len(symbols)
#             st.metric("Capital/Symbol", f"{capital_per:.2f} USDT")
    
#     st.markdown("---")
    
#     # Timeframes
#     st.markdown("#### ⏰ Timeframes")
#     col1, col2 = st.columns(2)
#     with col1:
#         st.write(f"**Entry:** {st.session_state.get('timeframe', '15')}")
#     with col2:
#         st.write(f"**Exit:** {st.session_state.get('exit_tf', '30')}")
    
#     st.markdown("---")
    
#     # Risk Management
#     st.markdown("#### 🛡️ Risk Management")
#     col1, col2, col3 = st.columns(3)
    
#     with col1:
#         if st.session_state.get('use_sl', False):
#             st.success(f"✅ SL: {st.session_state.get('sl_perc', 0.5):.1f}%")
#         else:
#             st.warning("❌ No SL")
    
#     with col2:
#         if st.session_state.get('use_tp', False):
#             st.success(f"✅ TP: {st.session_state.get('tp_perc', 3.0):.1f}%")
#         else:
#             st.warning("❌ No TP")
    
#     with col3:
#         if st.session_state.get('use_trailing_sl', False):
#             st.success(f"✅ TSL: {st.session_state.get('trailing_activation_perc', 2.0):.1f}%")
#         else:
#             st.info("ℹ️ No TSL")
    
#     st.markdown("---")
    
    

#          # Warnings
#     can_start = True
    
#     if not symbols:
#         st.error("❌ No symbols selected! Bot cannot start.")
#         can_start = False
    
#     if initial_capital <= 0:
#         st.error("❌ Invalid capital!")
#         can_start = False
    
#     if st.session_state.env == "Mainnet" and not st.session_state.get('confirm_real', False):
#         st.error("❌ Confirm Mainnet trading in settings!")
#         can_start = False


    
#     # Confirmation buttons
#     st.markdown("---")
#     col1, col2 = st.columns(2)
    
#     with col1:
#         if st.button("✅ CONFIRM & START", 
#                     type="primary", 
#                     use_container_width=True,
#                     disabled=not can_start,
#                     key="confirm_start_btn"):
            
#             # Directly set values
#             initial_capital = st.session_state.get('initial_balance_manual', 1000.0)
            
#             st.session_state["initial_capital"] = initial_capital
#             st.session_state["current_capital"] = initial_capital
#             st.session_state["total_realized_pnl"] = 0.0
#             st.session_state["live"] = True
#             st.session_state['show_start_confirmation'] = False
#             st.session_state['bot_just_started'] = True  # 🔥 NEW FLAG
            
#             # Save config
#             ConfigManager.save_config()
            
#             # Log
#             from core.logger import BotLogger
#             logger = BotLogger(st.session_state)
#             logger.add_log(f"✅ BOT STARTED! Balance: {initial_capital:.2f} USDT", "SUCCESS")
            
#             # Send telegram
#             if st.session_state.get('use_telegram', False):
#                 try:
#                     from core.telegram_notifier import TelegramNotifier
#                     telegram = TelegramNotifier(
#                         bot_token=st.session_state.get('telegram_bot_token'),
#                         chat_id=st.session_state.get('telegram_chat_id'),
#                         enabled=True
#                     )
#                     telegram.notify_bot_started(initial_capital)
#                 except:
#                     pass
            
#             # Rerun
#             st.rerun()
    
#     with col2:
#         if st.button("❌ CANCEL", use_container_width=True, key="cancel_start_btn"):
#             st.session_state['show_start_confirmation'] = False
#             st.rerun()




# ui/sidebar.py - Modal تمیز و کامل
@st.dialog("⚠️ Confirm Bot Start", width="large")
def show_start_confirmation_modal(api_client):
    """Complete confirmation modal - FIXED"""
    
    # =========================================================================
    # Header
    # =========================================================================
    st.markdown("""
        <div style='text-align: center; padding: 25px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
            <h1 style='color: white; margin: 0; font-size: 2em;'>🚀 Ready to Start Trading?</h1>
            <p style='color: white; opacity: 0.95; margin: 8px 0 0 0; font-size: 1.1em;'>
                Review all settings carefully before starting
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # =========================================================================
    # 1. Environment
    # =========================================================================
    st.markdown("### 🌍 Environment")
    env_emoji = "🔴" if st.session_state.env == "Mainnet" else "🟢"
    env_text = "⚠️ REAL MONEY TRADING!" if st.session_state.env == "Mainnet" else "✅ Safe Demo Mode"
    
    if st.session_state.env == "Mainnet":
        st.error(f"## {env_emoji} **{st.session_state.env}** - {env_text}")
    else:
        st.success(f"## {env_emoji} **{st.session_state.env}** - {env_text}")
    
    st.markdown("---")
    
    # =========================================================================
    # 2. Initial Capital
    # =========================================================================
    st.markdown("### 💰 Initial Capital")
    
    col_radio, col_value = st.columns([1, 1])
    
    with col_radio:
        capital_source = st.radio(
            "**Capital Source:**",
            ["Manual Input", "Sync from Exchange"],
            index=0,
            key="capital_source_modal",
            help="Choose how to set your starting balance"
        )
    
    with col_value:
        if capital_source == "Manual Input":
            initial_capital = st.session_state.get('initial_balance_manual', 1000.0)
            st.metric("💵 Starting Balance", f"{initial_capital:.2f} USDT", help="From sidebar settings")
            
        else:
            if st.button("🔄 Fetch Balance Now", use_container_width=True, type="secondary"):
                with st.spinner("Fetching from Bybit..."):
                    success, balance = api_client.test_connection()
                    
                    if success:
                        st.session_state['fetched_balance'] = balance
                        st.session_state['use_fetched_balance'] = True
                        st.success(f"✅ Fetched: {balance:.2f} USDT")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed: {balance}")
                        st.session_state['use_fetched_balance'] = False
            
            if st.session_state.get('use_fetched_balance', False):
                fetched = st.session_state.get('fetched_balance', 0.0)
                st.metric("💵 Exchange Balance", f"{fetched:.2f} USDT", delta="Live")
                initial_capital = fetched
            else:
                st.warning("⚠️ Click button above to fetch")
                initial_capital = st.session_state.get('initial_balance_manual', 1000.0)
    
    st.markdown("---")
    
    # =========================================================================
    # 3. Trading Symbols
    # =========================================================================
    st.markdown("### 🎯 Trading Symbols")
    
    symbols = st.session_state.get('multi_symbol_list', [])
    max_positions = st.session_state.get('max_positions', 5)
    
    if symbols:
        symbols_display = ", ".join(symbols[:5])
        if len(symbols) > 5:
            symbols_display += f" ... (+{len(symbols) - 5} more)"
        
        st.info(f"**📊 Selected:** {symbols_display}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🔢 Total Symbols", len(symbols))
        
        with col2:
            st.metric("📌 Max Positions", max_positions)
        
        with col3:
            capital_per = initial_capital / len(symbols) if symbols else 0
            st.metric("💰 Per Symbol", f"~{capital_per:.2f} USDT")
    else:
        st.error("### ❌ **No symbols selected!** \nGo to sidebar to add symbols.")
    
    st.markdown("---")
    
    # =========================================================================
    # 4. Strategy & Settings
    # =========================================================================
    st.markdown("### 📊 Strategy Settings")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        strategy = st.session_state.get('selected_strategy', 'Unknown')
        st.markdown(f"**🎯 Strategy:**  \n`{strategy}`")
    
    with col2:
        timeframe = st.session_state.get('timeframe', '15')
        st.markdown(f"**⏰ Timeframe:**  \n`{timeframe}m`")
    
    with col3:
        trade_type = st.session_state.get('trade_type', 'Both')
        st.markdown(f"**📈 Type:**  \n`{trade_type}`")
    
    with col4:
        qty_mode = st.session_state.get('qty_mode', 'Fixed USDT Amount')
        st.markdown(f"**💵 Size Mode:**  \n`{qty_mode.split()[0]}`")
    
    st.markdown("---")
    
    # =========================================================================
    # 5. Risk Management
    # =========================================================================
    st.markdown("### 🛡️ Risk Management")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        leverage = st.session_state.get('leverage', 1)
        if leverage > 10:
            st.error(f"⚠️ **Leverage:** {leverage}x")
        elif leverage > 5:
            st.warning(f"⚡ **Leverage:** {leverage}x")
        else:
            st.success(f"✅ **Leverage:** {leverage}x")
    
    with col2:
        if st.session_state.get('use_sl', False):
            sl_perc = st.session_state.get('sl_perc', 0.5)
            st.success(f"### ✅ SL  \n**{sl_perc:.1f}%**")
        else:
            st.error("### ❌ SL  \n**Disabled**")
    
    with col3:
        if st.session_state.get('use_tp', False):
            tp_perc = st.session_state.get('tp_perc', 3.0)
            st.success(f"### ✅ TP  \n**{tp_perc:.1f}%**")
        else:
            st.error("### ❌ TP  \n**Disabled**")
    
    with col4:
        if st.session_state.get('use_trailing_sl', False):
            tsl_act = st.session_state.get('trailing_activation_perc', 2.0)
            st.success(f"### ✅ TSL  \n**{tsl_act:.1f}%**")
        else:
            st.info("### ℹ️ TSL  \n**Disabled**")
    
    st.markdown("---")
    
    # =========================================================================
    # 6. Validation
    # =========================================================================
    can_start = True
    errors = []
    warnings = []
    
    # Critical errors
    if not st.session_state.get('api_key') or not st.session_state.get('api_secret'):
        can_start = False
        errors.append("❌ **API credentials missing** - Add them in sidebar")
    
    if not symbols:
        can_start = False
        errors.append("❌ **No symbols selected** - Select at least one symbol")
    
    if initial_capital < 10:
        can_start = False
        errors.append("❌ **Capital too low** - Minimum: 10 USDT")
    
    if st.session_state.env == "Mainnet" and not st.session_state.get('confirm_real', False):
        can_start = False
        errors.append("❌ **Mainnet not confirmed** - Check 'Confirm real trading' in sidebar")
    
    # Warnings
    if not st.session_state.get('use_sl') and not st.session_state.get('use_tp'):
        warnings.append("⚠️ **No TP/SL** - Trades exit only on signal reversal")
    
    if leverage > 10:
        warnings.append(f"⚠️ **High leverage ({leverage}x)** - Risk is significantly increased")
    
    if len(symbols) > max_positions:
        warnings.append(f"⚠️ **Symbol overflow** - {len(symbols)} symbols but max {max_positions} positions")
    
    # Display
    if errors:
        st.markdown("### ❌ Critical Issues (Must Fix)")
        for err in errors:
            st.error(err)
        st.markdown("---")
    
    if warnings:
        st.markdown("### ⚠️ Warnings (Review Carefully)")
        for warn in warnings:
            st.warning(warn)
        st.markdown("---")
    
    # =========================================================================
    # 7. Final Confirmation (Mainnet only)
    # =========================================================================
    
    if st.session_state.env == "Mainnet" and can_start:
        st.markdown("### 🚨 FINAL CONFIRMATION")
        st.markdown("""
            <div style='background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ff9800;'>
                <p style='margin: 0; color: #856404; font-weight: bold;'>
                    ⚠️ You are about to start REAL money trading on Bybit Mainnet.
                    All trades will use actual funds and losses are real.
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        must_accept = st.checkbox(
            "✅ **I understand the risks and want to proceed with REAL trading**",
            key="final_mainnet_confirm",
            value=False
        )
        
        if not must_accept:
            can_start = False
    
    st.markdown("---")
    
    # =========================================================================
    # 8. Action Buttons (FIXED ORDER: Start on RIGHT, Cancel on LEFT)
    # =========================================================================
    
    col_cancel, col_space, col_start = st.columns([2, 1, 2])
    
    with col_cancel:
        if st.button("❌ CANCEL", use_container_width=True, key="modal_cancel", type="secondary"):
            st.session_state['show_start_confirmation'] = False
            st.session_state['use_fetched_balance'] = False
            st.rerun()
    
    with col_start:
        button_label = "✅ START TRADING NOW" if can_start else "🔒 FIX ERRORS FIRST"
        
        if st.button(
            button_label,
            type="primary",
            use_container_width=True,
            disabled=not can_start,
            key="modal_start"
        ):
            # 🔥 Close modal BEFORE any other action
            st.session_state['show_start_confirmation'] = False
            st.session_state['use_fetched_balance'] = False
            
            # Execute start
            _start_bot_now(initial_capital, api_client)


def _start_bot_now(initial_capital, api_client):
    """Execute bot start - FIXED to close modal properly"""
    
    # Set capital
    st.session_state["initial_capital"] = initial_capital
    st.session_state["current_capital"] = initial_capital
    st.session_state["total_realized_pnl"] = 0.0
    st.session_state["initial_balance_manual"] = initial_capital
    
    # Activate bot
    st.session_state["live"] = True
    st.session_state['bot_just_started'] = True
    
    # Save config
    from config.settings import ConfigManager
    ConfigManager.save_config()
    
    # Log
    from core.logger import BotLogger
    logger = BotLogger(st.session_state)
    
    symbols = st.session_state.get('multi_symbol_list', [])
    strategy = st.session_state.get('selected_strategy', 'Unknown')
    
    logger.add_log(
        f"🚀 BOT STARTED! Capital: {initial_capital:.2f} USDT | "
        f"Strategy: {strategy} | Symbols: {len(symbols)} | "
        f"Env: {st.session_state.get('env', 'Demo')}",
        "SUCCESS"
    )
    
    # Telegram
    if st.session_state.get('use_telegram', False):
        try:
            from core.telegram_notifier import TelegramNotifier
            telegram = TelegramNotifier(
                bot_token=st.session_state.get('telegram_bot_token'),
                chat_id=st.session_state.get('telegram_chat_id'),
                enabled=True
            )
            telegram.notify_bot_started(initial_capital)
        except Exception as e:
            logger.add_log(f"⚠️ Telegram failed: {e}", "WARNING")
    
    # 🔥 RERUN without any extra code
    st.rerun()


    

def _start_bot_now(initial_capital, api_client):
    """Execute bot start - Helper function"""
    
    # Set capital
    st.session_state["initial_capital"] = initial_capital
    st.session_state["current_capital"] = initial_capital
    st.session_state["total_realized_pnl"] = 0.0
    st.session_state["initial_balance_manual"] = initial_capital
    
    # Activate bot
    st.session_state["live"] = True
    st.session_state['show_start_confirmation'] = False
    st.session_state['bot_just_started'] = True
    st.session_state['use_fetched_balance'] = False
    
    # Save config
    from config.settings import ConfigManager
    ConfigManager.save_config()
    
    # Log
    from core.logger import BotLogger
    logger = BotLogger(st.session_state)
    
    symbols = st.session_state.get('multi_symbol_list', [])
    strategy = st.session_state.get('selected_strategy', 'Unknown')
    
    logger.add_log(
        f"🚀 BOT STARTED! Capital: {initial_capital:.2f} USDT | "
        f"Strategy: {strategy} | Symbols: {len(symbols)} | "
        f"Env: {st.session_state.get('env', 'Demo')}",
        "SUCCESS"
    )
    
    # Telegram notification
    if st.session_state.get('use_telegram', False):
        try:
            from core.telegram_notifier import TelegramNotifier
            telegram = TelegramNotifier(
                bot_token=st.session_state.get('telegram_bot_token'),
                chat_id=st.session_state.get('telegram_chat_id'),
                enabled=True
            )
            telegram.notify_bot_started(initial_capital)
        except Exception as e:
            logger.add_log(f"⚠️ Telegram notification failed: {e}", "WARNING")
    
    # Close modal with success message
    st.success("🎉 Bot started successfully! Redirecting...")
    time.sleep(0.8)
    st.rerun()


# ui/sidebar.py - stop_bot_callback

def stop_bot_callback():
    """
    Stop bot - ONLY stops trading, NOT connection
    """
    from config.settings import ConfigManager
    from core.logger import BotLogger
    
    logger = BotLogger(st.session_state)
    
    # 🔥 ONLY set live to False
    st.session_state["live"] = False
    
    # Clear connection alerts
    if 'connection_alert_sent' in st.session_state:
        del st.session_state['connection_alert_sent']
    
    pnl = st.session_state.get("total_realized_pnl", 0.0)
    initial = st.session_state.get("initial_capital", 0.0)
    current = st.session_state.get("current_capital", 0.0)
    pnl_percent = (pnl / initial * 100) if initial > 0 else 0
    
    # Telegram notification
    if st.session_state.get('use_telegram', False):
        from core.telegram_notifier import TelegramNotifier
        telegram = TelegramNotifier(
            bot_token=st.session_state.get('telegram_bot_token'),
            chat_id=st.session_state.get('telegram_chat_id'),
            enabled=True
        )
        telegram.notify_bot_stopped(current, pnl, pnl_percent)
    
    ConfigManager.save_config()
    logger.add_log(
        f"🛑 BOT STOPPED by user. PnL: {pnl:+.2f} USDT ({pnl_percent:+.2f}%)",
        "ERROR"
    )
    
    # 🔥 API connection remains active!
    # User can still test connection, sync balance, etc.