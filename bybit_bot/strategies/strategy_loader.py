# strategies/strategy_loader.py
import os
import importlib
import inspect
from strategies.base_strategy import BaseStrategy

class StrategyLoader:
    """
    Automatically discover and load all strategies in strategies/ folder
    
    Usage:
        loader = StrategyLoader()
        available = loader.get_available_strategies()
        strategy = loader.load_strategy('Heikin-Ashi Pure', config)
    """
    
    def __init__(self):
        self.strategies = {}
        self._discover_strategies()
    
    def _discover_strategies(self):
        """
        Scan strategies folder and auto-import all strategy classes
        """
        strategies_dir = os.path.dirname(__file__)
        
        # Get all .py files in strategies folder
        for filename in os.listdir(strategies_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]  # Remove .py
                
                # Skip base and loader
                if module_name in ['base_strategy', 'strategy_loader']:
                    continue
                
                try:
                    # Dynamic import
                    module = importlib.import_module(f'strategies.{module_name}')
                    
                    # Find all classes that inherit from BaseStrategy
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BaseStrategy) and obj != BaseStrategy:
                            # Get metadata
                            metadata = obj.STRATEGY_METADATA
                            
                            # Only load if enabled
                            if metadata.get('enabled', True):
                                strategy_name = metadata.get('name', name)
                                self.strategies[strategy_name] = {
                                    'class': obj,
                                    'metadata': metadata,
                                    'module': module_name
                                }
                                
                                print(f"✅ Loaded strategy: {strategy_name} (v{metadata.get('version', 'N/A')})")
                
                except Exception as e:
                    print(f"⚠️ Failed to load {module_name}: {e}")
    
    def get_available_strategies(self):
        """Get list of available strategy names"""
        return list(self.strategies.keys())
    
    def load_strategy(self, strategy_name, config):
        """
        Load and instantiate a strategy by name
        
        Args:
            strategy_name: Name of strategy
            config: Configuration dict (st.session_state)
        
        Returns:
            Strategy instance
        """
        if strategy_name not in self.strategies:
            available = ', '.join(self.get_available_strategies())
            raise ValueError(
                f"Strategy '{strategy_name}' not found. "
                f"Available: {available}"
            )
        
        strategy_class = self.strategies[strategy_name]['class']
        return strategy_class(config)
    
    def get_strategy_metadata(self, strategy_name):
        """Get metadata for a specific strategy"""
        if strategy_name in self.strategies:
            return self.strategies[strategy_name]['metadata']
        return None
    
    def get_all_metadata(self):
        """Get metadata for all strategies"""
        return {
            name: info['metadata'] 
            for name, info in self.strategies.items()
        }