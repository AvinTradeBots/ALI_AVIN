# strategies/base_strategy.py
from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    """
    Base class for all strategies
    
    How to create a new strategy:
    1. Inherit from BaseStrategy
    2. Add STRATEGY_METADATA
    3. Implement required methods
    4. Drop file in strategies/ folder
    5. Done! It will auto-load
    """
    
    # 🔥 Metadata (هر استراتژی باید این رو داشته باشه)
    STRATEGY_METADATA = {
        'name': 'Base Strategy',           # نام نمایشی
        'version': '1.0.0',                # نسخه
        'author': 'Unknown',               # سازنده
        'description': 'Base strategy',    # توضیحات
        'enabled': True,                   # فعال/غیرفعال
        'timeframes': ['1', '5', '15'],    # تایم‌فریم‌های پشتیبانی شده
        'symbols': ['BTCUSDT'],            # نمادهای پیشنهادی
    }
    
    def __init__(self, config):
        self.config = config
    
    @abstractmethod
    def calculate_signals(self, df_regular, df_ha=None):
        """
        Calculate entry and exit signals
        
        Args:
            df_regular: Regular OHLCV dataframe
            df_ha: Heikin-Ashi dataframe (optional)
        
        Returns:
            tuple: (long_entry, short_entry, long_exit, short_exit)
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self):
        """Strategy display name"""
        pass
    
    @abstractmethod
    def get_required_candles(self):
        """Required number of candles for calculation"""
        pass
    
    # === Helper Methods (همه استراتژی‌ها میتونن ازشون استفاده کنن) ===
    
    @staticmethod
    def calculate_heikin_ashi(df):
        """Convert to Heikin-Ashi candles"""
        ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        
        ha_open = pd.Series(index=df.index, dtype=float)
        ha_open.iloc[0] = df['open'].iloc[0]
        
        for i in range(1, len(df)):
            ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2
        
        ha_df = pd.DataFrame({
            'ha_open': ha_open,
            'ha_close': ha_close,
            'ha_high': df[['high', 'open', 'close']].max(axis=1),
            'ha_low': df[['low', 'open', 'close']].min(axis=1)
        }, index=df.index)
        
        return ha_df.dropna()
    
    @staticmethod
    def calculate_sma(df, length, source='close'):
        """Calculate Simple Moving Average"""
        if source not in df.columns:
            source = 'close'
        return df[source].rolling(window=length).mean()
    
    @staticmethod
    def calculate_ema(df, length, source='close'):
        """Calculate Exponential Moving Average"""
        if source not in df.columns:
            source = 'close'
        return df[source].ewm(span=length, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(series, period=14):
        """Calculate RSI indicator"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_atr(df, period=14):
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def get_metadata(self):
        """Get strategy metadata"""
        return self.STRATEGY_METADATA