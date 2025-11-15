# ui/components.py - COMPLETE WebSocket-Ready Version
import streamlit as st
from datetime import datetime, timezone
from core.utils import calculate_refresh_delay
from core.risk_manager import safe_float
import pandas as pd
import time
import os

# =============================================================================
# TIME SYNC
# =============================================================================

def display_time_sync(api_client):
    """Simple server time display"""
    try:
        time_data = api_client.get_server_time()
        server_time = time_data.get('server_time_dt')
        
        if server_time:
            col1, col2, col3 = st.columns([6, 2, 2])
            with col2:
                st.metric("🕐 Server (UTC)", server_time.strftime('%H:%M:%S'))
    except:
        pass

# =============================================================================
# UNIFIED DASHBOARD
# =============================================================================

def display_unified_dashboard(api_client=None, portfolio_manager=None):
    """Unified Dashboard - 2 ROWS ONLY"""
    st.markdown("---")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    capital = st.session_state.get('current_capital', 0)
    initial = st.session_state.get('initial_capital', 0)
    pnl = st.session_state.get('total_realized_pnl', 0)
    roi = ((capital - initial) / initial * 100) if initial > 0 else 0
    
    if portfolio_manager:
        summary = portfolio_manager.get_portfolio_summary()
        active = summary['active_positions']
        max_pos = summary['max_positions']
        unrealized = summary['total_unrealized_pnl']
    else:
        active = 0
        max_pos = st.session_state.get('max_positions', 5)
        unrealized = 0
    
    capital_color = "#28a745" if capital >= initial else "#dc3545"
    pnl_color = "#28a745" if pnl >= 0 else "#dc3545"
    roi_color = "#28a745" if roi >= 0 else "#dc3545"
    positions_color = "#17a2b8"
    unrealized_color = "#28a745" if unrealized >= 0 else "#dc3545"
    
    with col1:
        st.markdown(f"""
            <div style='text-align: center; padding: 15px; border-radius: 10px; 
                        background: linear-gradient(135deg, {capital_color}20 0%, {capital_color}40 100%);
                        border: 3px solid {capital_color};
                        box-shadow: 0 4px 12px {capital_color}30;'>
                <p style='margin: 0; font-size: 0.9em; color: #555; font-weight: 600;'>Capital</p>
                <h2 style='margin: 8px 0; color: {capital_color}; font-weight: bold;'>{capital:,.0f}</h2>
                <p style='margin: 0; font-size: 0.8em; color: #777;'>USDT</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        sign = "+" if pnl >= 0 else ""
        st.markdown(f"""
            <div style='text-align: center; padding: 15px; border-radius: 10px; 
                        background: linear-gradient(135deg, {pnl_color}20 0%, {pnl_color}40 100%);
                        border: 3px solid {pnl_color};
                        box-shadow: 0 4px 12px {pnl_color}30;'>
                <p style='margin: 0; font-size: 0.9em; color: #555; font-weight: 600;'>PnL</p>
                <h2 style='margin: 8px 0; color: {pnl_color}; font-weight: bold;'>{sign}{pnl:,.1f}</h2>
                <p style='margin: 0; font-size: 0.8em; color: #777;'>USDT</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        sign = "+" if roi >= 0 else ""
        st.markdown(f"""
            <div style='text-align: center; padding: 15px; border-radius: 10px; 
                        background: linear-gradient(135deg, {roi_color}20 0%, {roi_color}40 100%);
                        border: 3px solid {roi_color};
                        box-shadow: 0 4px 12px {roi_color}30;'>
                <p style='margin: 0; font-size: 0.9em; color: #555; font-weight: 600;'>ROI</p>
                <h2 style='margin: 8px 0; color: {roi_color}; font-weight: bold;'>{sign}{roi:,.1f}%</h2>
                <p style='margin: 0; font-size: 0.8em; color: #777;'>Return</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div style='text-align: center; padding: 15px; border-radius: 10px; 
                        background: linear-gradient(135deg, {positions_color}20 0%, {positions_color}40 100%);
                        border: 3px solid {positions_color};
                        box-shadow: 0 4px 12px {positions_color}30;'>
                <p style='margin: 0; font-size: 0.9em; color: #555; font-weight: 600;'>Positions</p>
                <h2 style='margin: 8px 0; color: {positions_color}; font-weight: bold;'>{active}/{max_pos}</h2>
                <p style='margin: 0; font-size: 0.8em; color: #777;'>Active</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col5:
        sign = "+" if unrealized >= 0 else ""
        st.markdown(f"""
            <div style='text-align: center; padding: 15px; border-radius: 10px; 
                        background: linear-gradient(135deg, {unrealized_color}20 0%, {unrealized_color}40 100%);
                        border: 3px solid {unrealized_color};
                        box-shadow: 0 4px 12px {unrealized_color}30;'>
                <p style='margin: 0; font-size: 0.9em; color: #555; font-weight: 600;'>Unrealized</p>
                <h2 style='margin: 8px 0; color: {unrealized_color}; font-weight: bold;'>{sign}{unrealized:,.1f}</h2>
                <p style='margin: 0; font-size: 0.8em; color: #777;'>USDT</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")

# =============================================================================
# STATUS BANNER
# =============================================================================

def display_status_banner():
    """Display status banner"""
    capital_change = st.session_state.get('current_capital', 0) - st.session_state.get('initial_capital', 0)
    pnl_sign = "+" if capital_change >= 0 else ""
    status_bar_color = "#dc3545"
    
    if st.session_state.get("live", False):
        status_bar_color = "#28a745" if capital_change >= 0 else "#dc3545"
        
        # 🔥 WebSocket mode indicator
        if st.session_state.get('ws_active', False):
            mode_text = "⚡ WebSocket Mode"
        else:
            mode_text = "🔄 REST Mode"
        
        status_text = f"🟢 Live Active | {mode_text}"
        pnl_html = f"| PnL: <b>{pnl_sign}{capital_change:+.2f} USDT</b>"
        
        st.markdown(f"""
            <div style='color: white; background-color: {status_bar_color}; 
                        padding: 12px; border-radius: 8px; text-align: center; 
                        font-weight: bold; font-size: 1.1em;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.2);'>
                {status_text} {pnl_html}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style='color: white; background-color: {status_bar_color}; 
                        padding: 12px; border-radius: 8px; text-align: center; 
                        font-weight: bold; font-size: 1.1em;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.2);'>
                🔴 Bot Stopped | Capital: {st.session_state.get('current_capital', 0):.2f} USDT ({pnl_sign}{capital_change:.2f})
            </div>
        """, unsafe_allow_html=True)

# =============================================================================
# WEBSOCKET STATUS - 🔥 NEW
# =============================================================================

def display_websocket_status(ws_client, state_manager):
    """نمایش وضعیت WebSocket و State Manager"""
    
    status = ws_client.get_status()
    
    # Connection Status
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if status['public_connected']:
            st.markdown("""
                <div style='padding: 15px; background: #d4edda; border-radius: 8px; text-align: center;'>
                    <span class='ws-indicator ws-connected'></span>
                    <p style='margin: 0; color: #155724; font-weight: bold;'>Public Stream</p>
                    <p style='margin: 5px 0 0 0; color: #155724;'>🟢 Connected</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style='padding: 15px; background: #f8d7da; border-radius: 8px; text-align: center;'>
                    <span class='ws-indicator ws-disconnected'></span>
                    <p style='margin: 0; color: #721c24; font-weight: bold;'>Public Stream</p>
                    <p style='margin: 5px 0 0 0; color: #721c24;'>🔴 Disconnected</p>
                </div>
            """, unsafe_allow_html=True)
    
    with col2:
        if status['private_connected']:
            st.markdown("""
                <div style='padding: 15px; background: #d4edda; border-radius: 8px; text-align: center;'>
                    <span class='ws-indicator ws-connected'></span>
                    <p style='margin: 0; color: #155724; font-weight: bold;'>Private Stream</p>
                    <p style='margin: 5px 0 0 0; color: #155724;'>🟢 Connected</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style='padding: 15px; background: #f8d7da; border-radius: 8px; text-align: center;'>
                    <span class='ws-indicator ws-disconnected'></span>
                    <p style='margin: 0; color: #721c24; font-weight: bold;'>Private Stream</p>
                    <p style='margin: 5px 0 0 0; color: #721c24;'>🔴 Disconnected</p>
                </div>
            """, unsafe_allow_html=True)
    
    with col3:
        st.metric("Messages Received", status.get('messages_received', 0))
    
    with col4:
        last_msg = status.get('last_message_time')
        if last_msg:
            seconds_ago = (datetime.now() - last_msg).total_seconds()
            st.metric("Last Message", f"{seconds_ago:.0f}s ago")
        else:
            st.metric("Last Message", "Never")
    
    st.markdown("---")
    
    # Subscriptions
    st.subheader("📡 Active Subscriptions")
    
    subscriptions = status.get('subscriptions', [])
    
    if subscriptions:
        # گروه‌بندی subscriptions
        public_subs = [s for s in subscriptions if not any(k in s for k in ['position', 'order', 'execution', 'wallet'])]
        private_subs = [s for s in subscriptions if any(k in s for k in ['position', 'order', 'execution', 'wallet'])]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Public Subscriptions")
            if public_subs:
                for sub in public_subs:
                    st.markdown(f"- `{sub}`")
            else:
                st.caption("No public subscriptions")
        
        with col2:
            st.markdown("### 🔐 Private Subscriptions")
            if private_subs:
                for sub in private_subs:
                    st.markdown(f"- `{sub}`")
            else:
                st.caption("No private subscriptions")
    else:
        st.info("No active subscriptions")
    
    st.markdown("---")
    
    # State Manager Status
    if state_manager:
        st.subheader("🔐 State Manager")
        
        state_summary = state_manager.get_status_summary()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Active Positions", state_summary['positions_count'])
            if state_summary['positions']:
                st.caption(f"Symbols: {', '.join(state_summary['positions'])}")
        
        with col2:
            st.metric("Pending Orders", state_summary['pending_orders_count'])
            if state_summary['pending']:
                st.caption(f"Pending: {', '.join(state_summary['pending'])}")
        
        with col3:
            cooldown = state_manager.signal_cooldown_seconds
            timeout = state_manager.order_timeout_seconds
            st.metric("Signal Cooldown", f"{cooldown}s")
            st.caption(f"Order timeout: {timeout}s")
        
        # جزئیات positions
        with st.expander("🔍 Detailed State"):
            positions = state_manager.get_all_positions()
            
            if positions:
                st.markdown("### Active Positions")
                for symbol, pos in positions.items():
                    st.write(f"**{symbol}:** {pos['side']} @ {pos['entry_price']:.4f} | Qty: {pos['quantity']:.6f}")
            else:
                st.caption("No positions in state manager")

# =============================================================================
# CONNECTION STATUS
# =============================================================================

def display_connection_status(api_client):
    """Display REST API connection status"""
    
    status = api_client.get_connection_status()
    
    if status['is_connected']:
        if status['seconds_since_success'] < 60:
            status_color = "#28a745"
            status_icon = "🟢"
            status_text = "Connected"
        else:
            status_color = "#ffc107"
            status_icon = "🟡"
            status_text = "Slow"
    else:
        status_color = "#dc3545"
        status_icon = "🔴"
        status_text = "Disconnected"
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown(f"""
            <div style='text-align: center; padding: 10px; border-radius: 8px; 
                        background-color: {status_color}20; border: 3px solid {status_color};'>
                <span style='font-size: 2em;'>{status_icon}</span>
                <p style='margin: 5px 0 0 0; color: {status_color}; font-weight: bold; font-size: 1.1em;'>{status_text}</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.caption(f"Last success: {int(status['seconds_since_success'])}s ago")
        if status['total_retries'] > 0:
            st.caption(f"⚠️ Total retries: {status['total_retries']}")
    
    with col3:
        if st.button("🔄 Test Now", use_container_width=True, type="secondary"):
            success, result = api_client.test_connection()
            if success:
                st.success(f"✅ {result:.2f} USDT")
            else:
                st.error(f"❌ Failed")

# =============================================================================
# LOGS
# =============================================================================

def display_logs():
    """Display logs"""
    st.markdown("---")
    st.subheader("📋 Operations Log")
    
    operation_container = st.container(border=True, height=250)
    with operation_container:
        for lg_item in st.session_state.get("logs", []):
            if isinstance(lg_item, dict) and lg_item.get("is_operation", False):
                st.markdown(lg_item["message"], unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("🔍 Detailed Bot Logs")
    
    log_container = st.container(border=True, height=400)
    with log_container:
        for lg_item in st.session_state.get("logs", []):
            if isinstance(lg_item, dict):
                st.markdown(lg_item["message"], unsafe_allow_html=True)
            elif isinstance(lg_item, str):
                st.markdown(lg_item, unsafe_allow_html=True)

# =============================================================================
# POSITIONS AND TRADES TABLES
# =============================================================================

def display_positions_and_trades_tables(api_client, db, table_id="main"):
    """نمایش جداول معاملات باز و بسته شده"""
    
    # ========================================================================
    # جدول 1: معاملات باز
    # ========================================================================
    
    col_header_open, col_refresh = st.columns([4, 1])
    
    with col_header_open:
        st.subheader("📈 All Open Positions")
    
    with col_refresh:
        if st.button("🔄 Refresh", key=f"refresh_positions_btn_{table_id}", use_container_width=True):
            st.rerun()
    
    positions = st.session_state.get("positions_data", [])
    
    if positions:
        active_positions = [p for p in positions if safe_float(p.get('size')) > 0]
        
        if active_positions:
            positions_data = []
            
            for pos in active_positions:
                symbol_name = pos.get('symbol', 'N/A')
                side = pos.get('side', 'N/A')
                size = safe_float(pos.get('size'))
                entry_price = safe_float(pos.get('avgPrice'))
                mark_price = safe_float(pos.get('markPrice'))
                unrealized_pnl = safe_float(pos.get('unrealisedPnl'))
                leverage = pos.get('leverage', 'N/A')
                
                position_value = size * entry_price
                pnl_percent = (unrealized_pnl / position_value * 100) if position_value > 0 else 0
                margin_used = position_value / float(leverage) if leverage != 'N/A' else 0
                
                tp_price = pos.get('takeProfit', 'N/A')
                sl_price = pos.get('stopLoss', 'N/A')
                
                tp_display = f"{safe_float(tp_price):.4f}" if tp_price and tp_price != 'N/A' and safe_float(tp_price) > 0 else "-"
                sl_display = f"{safe_float(sl_price):.4f}" if sl_price and sl_price != 'N/A' and safe_float(sl_price) > 0 else "-"
                
                positions_data.append({
                    'Symbol': symbol_name,
                    'Side': side,
                    'Entry Price': f"{entry_price:.4f}",
                    'Current Price': f"{mark_price:.4f}",
                    'Quantity': f"{size:.6f}",
                    'Leverage': f"{leverage}x",
                    'Margin Used': f"{margin_used:.2f}",
                    'Unrealized PnL': f"{unrealized_pnl:+.2f}",
                    'PnL %': f"{pnl_percent:+.2f}",
                    'TP': tp_display,
                    'SL': sl_display
                })
            
            df_positions = pd.DataFrame(positions_data)
            
            def highlight_positions(row):
                pnl_str = row['Unrealized PnL'].replace('+', '').strip()
                try:
                    pnl_value = float(pnl_str)
                except:
                    pnl_value = 0.0
                
                colors = []
                for col in row.index:
                    if col == 'Unrealized PnL' or col == 'PnL %':
                        if pnl_value > 0:
                            colors.append('background-color: #d4edda; color: #155724; font-weight: bold')
                        elif pnl_value < 0:
                            colors.append('background-color: #f8d7da; color: #721c24; font-weight: bold')
                        else:
                            colors.append('background-color: #fff3cd; color: #856404')
                    elif col == 'Side':
                        if row[col] == 'Buy':
                            colors.append('background-color: #d1ecf1; color: #0c5460; font-weight: bold')
                        else:
                            colors.append('background-color: #f8d7da; color: #721c24; font-weight: bold')
                    else:
                        colors.append('')
                
                return colors
            
            st.dataframe(
                df_positions.style.apply(highlight_positions, axis=1),
                use_container_width=True,
                hide_index=True,
                height=min(len(df_positions) * 35 + 38, 400)
            )
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            
            total_positions = len(active_positions)
            total_margin = sum(safe_float(p['Margin Used']) for p in positions_data)
            total_unrealized = sum(safe_float(p['Unrealized PnL']) for p in positions_data)
            
            with col_stat1:
                st.metric("Total Positions", total_positions)
            
            with col_stat2:
                st.metric("Total Margin Used", f"{total_margin:.2f} USDT")
            
            with col_stat3:
                delta_color = "normal" if total_unrealized >= 0 else "inverse"
                st.metric("Total Unrealized PnL", f"{total_unrealized:+.2f} USDT", delta_color=delta_color)
        else:
            st.info("✅ No open positions at the moment.")
    else:
        st.info("🔍 Loading positions data...")
    
    # ========================================================================
    # جدول 2: معاملات بسته شده
    # ========================================================================
    st.markdown("---")
    
    col_header_closed, col_filter_days, col_filter_symbol = st.columns([2, 1, 1])
    
    with col_header_closed:
        st.subheader("📋 Recent Closed Trades")
    
    with col_filter_days:
        days_filter = st.selectbox(
            "Time Range:",
            [1, 7, 30, 90, 365, 9999],
            format_func=lambda x: "All Time" if x == 9999 else f"Last {x} days",
            index=2,
            key=f"closed_trades_days_filter_{table_id}"
        )
    
    if days_filter == 9999:
        df_all_trades = db.get_trade_history(days=None)
    else:
        df_all_trades = db.get_trade_history(days=days_filter)
    
    with col_filter_symbol:
        if not df_all_trades.empty:
            unique_symbols = ['All'] + sorted(df_all_trades['symbol'].unique().tolist())
            symbol_filter = st.selectbox(
                "Symbol:",
                unique_symbols,
                index=0,
                key=f"closed_trades_symbol_filter_{table_id}"
            )
        else:
            symbol_filter = "All"
    
    df_trades = df_all_trades.copy()
    if symbol_filter != "All" and not df_trades.empty:
        df_trades = df_trades[df_trades['symbol'] == symbol_filter]
    
    if not df_trades.empty:
        display_data = []
        
        df_trades = df_trades.sort_values('timestamp', ascending=False)
        
        for _, trade in df_trades.iterrows():
            duration = trade.get('duration_minutes', 0)
            if duration and duration > 0:
                hours = int(duration // 60)
                minutes = int(duration % 60)
                duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            else:
                duration_str = "N/A"
            
            timestamp = pd.to_datetime(trade['timestamp']).strftime('%Y-%m-%d %H:%M')
            
            display_data.append({
                'Time': timestamp,
                'Symbol': trade.get('symbol', 'N/A'),
                'Side': trade.get('side', 'N/A'),
                'Entry': f"{trade.get('entry_price', 0):.4f}",
                'Exit': f"{trade.get('exit_price', 0):.4f}",
                'Qty': f"{trade.get('quantity', 0):.6f}",
                'PnL (USDT)': trade.get('pnl_usdt', 0),
                'PnL (%)': trade.get('pnl_percent', 0),
                'Duration': duration_str,
                'Reason': trade.get('exit_reason', 'N/A')
            })
        
        df_display = pd.DataFrame(display_data)
        df_display_numeric = df_display.copy()
        
        def highlight_trades(row):
            idx = row.name
            pnl_usdt = df_display_numeric.loc[idx, 'PnL (USDT)']
            
            try:
                pnl_value = float(pnl_usdt)
            except (ValueError, TypeError):
                pnl_value = 0.0
            
            if pnl_value > 0:
                base_color = 'background-color: #d4edda; color: #155724'
            elif pnl_value < 0:
                base_color = 'background-color: #f8d7da; color: #721c24'
            else:
                base_color = 'background-color: #fff3cd; color: #856404'
            
            colors = []
            for col in row.index:
                if col in ['PnL (USDT)', 'PnL (%)']:
                    colors.append(base_color + '; font-weight: bold; font-size: 1.05em')
                else:
                    colors.append(base_color)
            
            return colors
        
        df_display['PnL (USDT)'] = df_display['PnL (USDT)'].apply(lambda x: f"{x:+.2f}")
        df_display['PnL (%)'] = df_display['PnL (%)'].apply(lambda x: f"{x:+.2f}%")
        
        st.dataframe(
            df_display.style.apply(highlight_trades, axis=1),
            use_container_width=True,
            hide_index=True,
            height=500
        )
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        total_trades = len(df_trades)
        winning_trades = len(df_trades[df_trades['pnl_usdt'] > 0])
        total_pnl = df_trades['pnl_usdt'].sum()
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        with col_stat1:
            st.metric("Total Trades", total_trades)
        
        with col_stat2:
            st.metric("Win Rate", f"{win_rate:.1f}%")
        
        with col_stat3:
            pnl_delta_color = "normal" if total_pnl >= 0 else "inverse"
            st.metric("Total PnL", f"{total_pnl:+.2f} USDT", delta_color=pnl_delta_color)
        
        with col_stat4:
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
            st.metric("Avg PnL/Trade", f"{avg_pnl:+.2f} USDT")
        
        st.markdown("---")
        col_export1, col_export2, col_export3, _ = st.columns([2, 2, 2, 4])
        
        with col_export1:
            if st.button("📥 Export to CSV", key=f"export_csv_btn_{table_id}", use_container_width=True):
                
                with st.spinner("Exporting..."):
                    try:
                        csv_path = db.export_to_csv(days=days_filter if days_filter != 9999 else None)
                        
                        if csv_path:
                            st.success(f"✅ Saved as: `{csv_path}`")
                            
                            try:
                                with open(csv_path, 'r', encoding='utf-8-sig') as f:
                                    csv_content = f.read()
                                
                                st.download_button(
                                    label="💾 Download Now",
                                    data=csv_content,
                                    file_name=os.path.basename(csv_path),
                                    mime='text/csv',
                                    key=f"download_{table_id}",
                                    use_container_width=True
                                )
                            except:
                                pass
                        else:
                            st.warning("⚠️ No trades to export")
                    
                    except PermissionError as e:
                        st.error(
                            "❌ **Cannot save file!**\n\n"
                            "The file is currently open in another program.\n\n"
                            "**Solutions:**\n"
                            "1. Close Excel/Notepad\n"
                            "2. Or rename/delete old `trades_export*.csv` files\n"
                            "3. Then try again"
                        )
                    
                    except Exception as e:
                        st.error(f"❌ Export failed: {str(e)[:200]}")
        
        with col_export2:
            db_size = db.get_database_size()
            st.metric("💾 DB Size", f"{db_size:.2f} MB")
        
        with col_export3:
            if symbol_filter != "All":
                st.caption(f"📊 Filtered: {symbol_filter}")
    
    else:
        time_range_text = "All Time" if days_filter == 9999 else f"last {days_filter} days"
        st.info(f"🔭 No closed trades found in the {time_range_text}.")
        
        if st.button("🔄 Reload from Database", key=f"reload_db_{table_id}"):
            st.rerun()