"""過濾器配置加載器"""

import yaml
from typing import Optional, Callable, Dict, Any
from pathlib import Path

from .filter_manager import FilterManager
from .common_filters import CommonFilters


class FilterConfigLoader:
    """過濾器配置加載器"""
    
    @staticmethod
    def load_filters_from_config(config_path: str, filter_manager: FilterManager) -> None:
        """
        從配置文件加載過濾器
        
        Args:
            config_path: 配置文件路径
            filter_manager: 過濾器管理器
        """
        config_file = Path(config_path)
        if not config_file.exists():
            print(f"Filter config file not found: {config_path}")
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading filter config: {e}")
            return
        
        if not config or 'filters' not in config:
            print("No filters section found in config")
            return
        
        filters_config = config['filters']
        
        # 加載全局過濾器
        FilterConfigLoader._load_global_filters(filters_config, filter_manager)
        
        # 加載交易對特定過濾器
        FilterConfigLoader._load_symbol_filters(filters_config, filter_manager)
        
        # 加載策略特定過濾器
        FilterConfigLoader._load_strategy_filters(filters_config, filter_manager)
    
    @staticmethod
    def _load_global_filters(config: Dict[str, Any], filter_manager: FilterManager) -> None:
        """加載全局過濾器"""
        if 'global' not in config:
            return
        
        for filter_config in config['global']:
            filter_func = FilterConfigLoader._create_system_filter(filter_config)
            if filter_func:
                filter_manager.add_global_filter(filter_func)
                print(f"Added global filter: {filter_config.get('type', 'unknown')}")
    
    @staticmethod
    def _load_symbol_filters(config: Dict[str, Any], filter_manager: FilterManager) -> None:
        """加載交易對特定過濾器"""
        if 'symbols' not in config:
            return
        
        for symbol, filters in config['symbols'].items():
            for filter_config in filters:
                filter_func = FilterConfigLoader._create_system_filter(filter_config)
                if filter_func:
                    filter_manager.add_symbol_filter(symbol, filter_func)
                    print(f"Added symbol filter for {symbol}: {filter_config.get('type', 'unknown')}")
    
    @staticmethod
    def _load_strategy_filters(config: Dict[str, Any], filter_manager: FilterManager) -> None:
        """加載策略特定過濾器"""
        if 'strategies' not in config:
            return
        
        for strategy_name, strategy_config in config['strategies'].items():
            # 處理進場過濾器
            if 'entry' in strategy_config:
                for filter_config in strategy_config['entry']:
                    filter_func = FilterConfigLoader._create_strategy_filter(filter_config, 'entry')
                    if filter_func:
                        filter_manager.add_strategy_filter(strategy_name, filter_func)
                        print(f"Added entry filter for {strategy_name}: {filter_config.get('type', 'unknown')}")
            
            # 處理出場過濾器
            if 'exit' in strategy_config:
                for filter_config in strategy_config['exit']:
                    filter_func = FilterConfigLoader._create_strategy_filter(filter_config, 'exit')
                    if filter_func:
                        filter_manager.add_strategy_filter(strategy_name, filter_func)
                        print(f"Added exit filter for {strategy_name}: {filter_config.get('type', 'unknown')}")
    
    @staticmethod
    def _create_system_filter(filter_config: Dict[str, Any]) -> Optional[Callable]:
        """
        創建系統級過濾器函數（全局和交易對特定過濾器）
        
        Args:
            filter_config: 過濾器配置
            
        Returns:
            過濾器函數或None
        """
        filter_type = filter_config.get('type')
        
        if filter_type == 'drawdown':
            return CommonFilters.drawdown_filter(filter_config['max_drawdown'])
        
        elif filter_type == 'position_limit':
            return CommonFilters.position_limit_filter(filter_config['max_positions'])
        
        elif filter_type == 'correlation':
            return CommonFilters.correlation_filter(
                filter_config['other_symbols'],
                filter_config.get('max_correlation', 0.7)
            )
        
        elif filter_type == 'volume':
            # 對於系統級volume過濾器，需要適配簽名
            volume_filter = CommonFilters.volume_filter(filter_config['min_volume'])
            return FilterConfigLoader._adapt_bar_filter_to_system(volume_filter)
        
        elif filter_type == 'price':
            price_filter = CommonFilters.price_filter(
                filter_config.get('min_price'),
                filter_config.get('max_price')
            )
            return FilterConfigLoader._adapt_bar_filter_to_system(price_filter)
        
        else:
            print(f"Unknown system filter type: {filter_type}")
            return None
    
    @staticmethod
    def _create_strategy_filter(filter_config: Dict[str, Any], filter_category: str) -> Optional[Callable]:
        """
        創建策略級過濾器函數
        
        Args:
            filter_config: 過濾器配置
            filter_category: 過濾器類別 ('entry' 或 'exit')
            
        Returns:
            過濾器函數或None
        """
        filter_type = filter_config.get('type')
        
        # 對於策略級過濾器，返回適配到系統級簽名的函數
        if filter_type == 'volume':
            bar_filter = CommonFilters.volume_filter(filter_config['min_volume'])
            return FilterConfigLoader._adapt_bar_filter_to_system(bar_filter)
        
        elif filter_type == 'volatility':
            bar_filter = CommonFilters.volatility_filter(
                filter_config['min_volatility'],
                filter_config.get('period', 20)
            )
            return FilterConfigLoader._adapt_bar_filter_to_system(bar_filter)
        
        elif filter_type == 'time':
            bar_filter = CommonFilters.time_filter(
                filter_config['start_hour'],
                filter_config['end_hour']
            )
            return FilterConfigLoader._adapt_bar_filter_to_system(bar_filter)
        
        elif filter_type == 'price':
            bar_filter = CommonFilters.price_filter(
                filter_config.get('min_price'),
                filter_config.get('max_price')
            )
            return FilterConfigLoader._adapt_bar_filter_to_system(bar_filter)
        
        elif filter_type == 'rsi':
            bar_filter = CommonFilters.rsi_filter(
                filter_config.get('oversold_threshold', 30),
                filter_config.get('overbought_threshold', 70),
                filter_config.get('period', 14)
            )
            return FilterConfigLoader._adapt_bar_filter_to_system(bar_filter)
        
        elif filter_type == 'moving_average':
            bar_filter = CommonFilters.moving_average_filter(
                filter_config.get('period', 20),
                filter_config.get('price_type', 'close')
            )
            return FilterConfigLoader._adapt_bar_filter_to_system(bar_filter)
        
        else:
            print(f"Unknown strategy filter type: {filter_type}")
            return None
    
    @staticmethod
    def _adapt_bar_filter_to_system(bar_filter: Callable) -> Callable:
        """
        將bar級過濾器適配為系統級過濾器
        
        Args:
            bar_filter: bar級過濾器函數 (bar, data_buffer) -> bool
            
        Returns:
            系統級過濾器函數 (signal, market_data, portfolio) -> bool
        """
        def adapted_filter(signal, market_data, portfolio):
            # 創建一個空的data_buffer，因為系統級過濾器通常不需要歷史數據
            return bar_filter(market_data, [])
        
        return adapted_filter
    
    @staticmethod
    def save_filter_config(filter_manager: FilterManager, config_path: str) -> None:
        """
        保存過濾器配置到文件（暫未實現）
        
        Args:
            filter_manager: 過濾器管理器
            config_path: 配置文件路径
        """
        # 這個功能比較複雜，因為需要將函數對象反序列化為配置
        # 暫時不實現，可以在後續版本中添加
        pass