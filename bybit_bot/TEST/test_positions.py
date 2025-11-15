# test_positions.py
import streamlit as st
from config.settings import ConfigManager
from core.api_client import BybitAPIClient
from core.logger import BotLogger

# Initialize session state
if 'initialized' not in st.session_state:
    ConfigManager.initialize_session_state()

logger = BotLogger(st.session_state)

api_client = BybitAPIClient(
    api_key=st.session_state.api_key,
    api_secret=st.session_state.api_secret,
    is_demo=(st.session_state.env == "Demo"),
    logger=logger
)

# دریافت پوزیشن‌ها
symbols = ['BTCUSDT', 'ETHUSDT', 'AIXBTUSDT', 'MYXUSDT', 'OGUSDT', 'CAKEUSDT']

for symbol in symbols:
    print(f"\n{'='*50}")
    print(f"Symbol: {symbol}")
    print(f"{'='*50}")
    
    positions = api_client.get_positions(symbol)
    
    for pos in positions:
        print(f"Side: {pos.get('side')}")
        print(f"Size: {pos.get('size')}")
        print(f"Avg Price: {pos.get('avgPrice')}")
        print(f"Mark Price: {pos.get('markPrice')}")
        print(f"Unrealised PnL: {pos.get('unrealisedPnl')}")
        print(f"🔥 Closed PnL: {pos.get('closedPnl')}")  # این مهمه!
        print(f"Cumulative PnL: {pos.get('cumRealisedPnl')}")
        print()