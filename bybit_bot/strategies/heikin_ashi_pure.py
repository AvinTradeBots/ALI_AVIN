# strategies/heikin_ashi_pure.py
from strategies.base_strategy import BaseStrategy

class HeikinAshiPure(BaseStrategy):
    """
    Pure Heikin-Ashi Strategy (No filters)
    
    Entry: 2 consecutive same-color candles
    Exit: 2 consecutive opposite-color candles
    """
    
    # 🔥 Metadata (این رو حتماً باید بنویسی!)
    STRATEGY_METADATA = {
        'name': 'Heikin-Ashi Pure',
        'version': '1.0.0',
        'author': 'Your Name',
        'description': 'Simple HA strategy without any filters',
        'enabled': True,
        'timeframes': ['1', '3', '5', '15', '30', '60'],
        'symbols': ['BTCUSDT', 'ETHUSDT'],
    }
    
    def get_strategy_name(self):
        return "Heikin-Ashi Pure Strategy"
    
    def get_required_candles(self):
        return 50
    
    def calculate_signals(self, df_regular, df_ha=None):
        """Calculate entry/exit signals"""
        
        if df_ha is None:
            df_ha = self.calculate_heikin_ashi(df_regular.copy())
        
        if len(df_ha) < 2:
            return False, False, False, False
        
        # Entry: 2 green candles
        long_signal = (
            df_ha['ha_close'].iloc[-2] > df_ha['ha_open'].iloc[-2] and
            df_ha['ha_close'].iloc[-1] > df_ha['ha_open'].iloc[-1]
        )
        
        # Entry: 2 red candles
        short_signal = (
            df_ha['ha_close'].iloc[-2] < df_ha['ha_open'].iloc[-2] and
            df_ha['ha_close'].iloc[-1] < df_ha['ha_open'].iloc[-1]
        )
        
        # Exit: 2 red candles
        long_exit = (
            df_ha['ha_close'].iloc[-2] < df_ha['ha_open'].iloc[-2] and
            df_ha['ha_close'].iloc[-1] < df_ha['ha_open'].iloc[-1]
        )
        
        # Exit: 2 green candles
        short_exit = (
            df_ha['ha_close'].iloc[-2] > df_ha['ha_open'].iloc[-2] and
            df_ha['ha_close'].iloc[-1] > df_ha['ha_open'].iloc[-1]
        )
        
        return long_signal, short_signal, long_exit, short_exit