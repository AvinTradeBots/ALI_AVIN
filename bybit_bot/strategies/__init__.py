# strategies/__init__.py
"""
Strategies Module - Auto-Discovery System

To add a new strategy:
1. Create new .py file in this folder
2. Inherit from BaseStrategy
3. Add STRATEGY_METADATA
4. Implement required methods
5. Done!

No need to modify any other files!
"""

from strategies.strategy_loader import StrategyLoader

# 🔥 Auto-load all strategies on import
_loader = StrategyLoader()

def get_available_strategies():
    """Get list of all available strategies"""
    return _loader.get_available_strategies()

def load_strategy(strategy_name, config):
    """Load a strategy by name"""
    return _loader.load_strategy(strategy_name, config)

def get_strategy_info(strategy_name):
    """Get strategy metadata"""
    return _loader.get_strategy_metadata(strategy_name)

def get_all_strategies_info():
    """Get all strategies metadata"""
    return _loader.get_all_metadata()

# Export for easy import
__all__ = [
    'get_available_strategies',
    'load_strategy',
    'get_strategy_info',
    'get_all_strategies_info'
]