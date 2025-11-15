# ui/analytics.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

def show_analytics_page(db):
    """صفحه تحلیل و آمار معاملات"""
    
    st.title("📊 Trading Analytics Dashboard")
    
    # فیلتر بازه زمانی
    col_filter1, col_filter2 = st.columns([3, 1])
    
    with col_filter1:
        time_range = st.selectbox(
            "Time Range",
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"],
            index=1
        )
    
    with col_filter2:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
    
    # تعیین تعداد روزها
    days_map = {
        "Last 7 Days": 7,
        "Last 30 Days": 30,
        "Last 90 Days": 90,
        "All Time": None
    }
    days = days_map[time_range]
    
    # دریافت آمار
    stats = db.get_statistics(days=days)
    
    st.markdown("---")
    
    # ========================================================================
    # بخش 1: کارت‌های آماری
    # ========================================================================
    st.subheader("📈 Performance Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Trades",
            f"{stats['total_trades']}",
            delta=f"Win Rate: {stats['win_rate']:.1f}%"
        )
    
    with col2:
        pnl_color = "normal" if stats['total_pnl'] >= 0 else "inverse"
        st.metric(
            "Total PnL",
            f"{stats['total_pnl']:.2f} USDT",
            delta=f"Avg: {stats['avg_pnl']:.2f}",
            delta_color=pnl_color
        )
    
    with col3:
        st.metric(
            "Best Trade",
            f"+{stats['best_trade']:.2f} USDT",
            delta=f"Worst: {stats['worst_trade']:.2f}"
        )
    
    with col4:
        st.metric(
            "Profit Factor",
            f"{stats['profit_factor']:.2f}",
            delta=f"Avg Duration: {int(stats['avg_duration_minutes'])}m"
        )
    
    # ========================================================================
    # بخش 2: Win/Loss Breakdown
    # ========================================================================
    st.markdown("---")
    col_pie1, col_pie2 = st.columns(2)
    
    with col_pie1:
        st.subheader("🎯 Win/Loss Distribution")
        
        if stats['total_trades'] > 0:
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Winning Trades', 'Losing Trades'],
                values=[stats['winning_trades'], stats['losing_trades']],
                marker=dict(colors=['#28a745', '#dc3545']),
                hole=0.4
            )])
            
            fig_pie.update_layout(
                showlegend=True,
                height=300,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No trades yet")
    
    with col_pie2:
        st.subheader("🔥 Consecutive Performance")
        
        if stats['total_trades'] > 0:
            fig_bar = go.Figure(data=[
                go.Bar(
                    x=['Max Wins Streak', 'Max Losses Streak'],
                    y=[stats['max_consecutive_wins'], stats['max_consecutive_losses']],
                    marker=dict(color=['#28a745', '#dc3545'])
                )
            ])
            
            fig_bar.update_layout(
                showlegend=False,
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
                yaxis_title="Consecutive Trades"
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No trades yet")
    
    # ========================================================================
    # بخش 3: نمودار PnL روزانه
    # ========================================================================
    st.markdown("---")
    st.subheader("💰 Daily PnL Chart")
    
    df_trades = db.get_trade_history(days=days)
    
    if not df_trades.empty:
        # تبدیل timestamp به date
        df_trades['date'] = pd.to_datetime(df_trades['timestamp']).dt.date
        
        # گروه‌بندی بر اساس روز
        daily_pnl = df_trades.groupby('date').agg({
            'pnl_usdt': 'sum',
            'id': 'count'
        }).reset_index()
        
        daily_pnl.columns = ['date', 'pnl', 'trades']
        
        # نمودار میله‌ای
        fig_daily = go.Figure()
        
        colors = ['green' if x > 0 else 'red' for x in daily_pnl['pnl']]
        
        fig_daily.add_trace(go.Bar(
            x=daily_pnl['date'],
            y=daily_pnl['pnl'],
            marker_color=colors,
            text=daily_pnl['pnl'].round(2),
            textposition='outside',
            hovertemplate='<b>Date:</b> %{x}<br><b>PnL:</b> %{y:.2f} USDT<br><b>Trades:</b> %{customdata}<extra></extra>',
            customdata=daily_pnl['trades']
        ))
        
        fig_daily.update_layout(
            xaxis_title="Date",
            yaxis_title="PnL (USDT)",
            height=400,
            hovermode='x unified',
            showlegend=False
        )
        
        st.plotly_chart(fig_daily, use_container_width=True)
    else:
        st.info("No trade data available for the selected period")
    
    # ========================================================================
    # بخش 4: نمودار تجمعی سرمایه (Equity Curve)
    # ========================================================================
    st.markdown("---")
    st.subheader("📈 Equity Curve (Cumulative PnL)")
    
    if not df_trades.empty:
        # مرتب‌سازی بر اساس زمان
        df_trades_sorted = df_trades.sort_values('timestamp')
        
        # محاسبه PnL تجمعی
        df_trades_sorted['cumulative_pnl'] = df_trades_sorted['pnl_usdt'].cumsum()
        
        # نمودار خطی
        fig_equity = go.Figure()
        
        fig_equity.add_trace(go.Scatter(
            x=pd.to_datetime(df_trades_sorted['timestamp']),
            y=df_trades_sorted['cumulative_pnl'],
            mode='lines',
            fill='tozeroy',
            line=dict(color='#17a2b8', width=2),
            name='Cumulative PnL'
        ))
        
        # خط صفر
        fig_equity.add_hline(y=0, line_dash="dash", line_color="gray")
        
        fig_equity.update_layout(
            xaxis_title="Time",
            yaxis_title="Cumulative PnL (USDT)",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_equity, use_container_width=True)
    
    # ========================================================================
    # بخش 5: جدول آخرین معاملات
    # ========================================================================
    st.markdown("---")
    st.subheader("📋 Recent Trades")
    
    if not df_trades.empty:
        # انتخاب ستون‌های نمایشی
        display_columns = [
            'timestamp', 'symbol', 'side', 'entry_price', 'exit_price',
            'quantity', 'pnl_usdt', 'pnl_percent', 'exit_reason'
        ]
        
        # فیلتر ستون‌های موجود
        available_columns = [col for col in display_columns if col in df_trades.columns]
        
        df_display = df_trades[available_columns].head(20).copy()
        
        # فرمت کردن
        df_display['timestamp'] = pd.to_datetime(df_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        
        # رنگ‌آمیزی PnL
        def highlight_pnl(row):
            if row['pnl_usdt'] > 0:
                return ['background-color: #d4edda'] * len(row)
            elif row['pnl_usdt'] < 0:
                return ['background-color: #f8d7da'] * len(row)
            else:
                return [''] * len(row)
        
        st.dataframe(
            df_display.style.apply(highlight_pnl, axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        # دکمه Export
        col_export1, col_export2, _ = st.columns([2, 2, 6])
        
        with col_export1:
            if st.button("📥 Export to CSV", use_container_width=True):
                csv_path = db.export_to_csv(days=days)
                st.success(f"✅ Exported to {csv_path}")
        
        with col_export2:
            db_size = db.get_database_size()
            st.caption(f"Database size: {db_size:.2f} MB")
    
    else:
        st.info("No trades to display")