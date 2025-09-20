"""
Trading System - 模塊化、事件驅動的交易系統

主要組件:
- data: 數據管理和市場數據提供者
- strategy: 策略基類和信號定義
- backtest: 回測引擎和投資組合管理
- execution: 訂單管理和執行
- risk: 風險管理
- exchange: 交易所連接器
- config: 配置管理
- filters: 過濾器系統
"""

# 核心組件導入
try:
    from .strategy import Signal, SignalType, BaseStrategy, EnhancedBaseStrategy
    from .backtest import Portfolio, BacktestEngine, BacktestResult
    from .execution import Order, OrderManager, OrderType, OrderStatus
    from .risk import RiskManager
    from .exchange import BybitConnector
    from .config import ConfigManager
    from .filters import FilterManager, CommonFilters
except ImportError as e:
    # 如果某些模塊不存在，只導入基本組件
    print(f"Warning: Some modules could not be imported: {e}")
    try:
        from .strategy import Signal, SignalType, BaseStrategy
        from .backtest import BacktestEngine
    except ImportError:
        pass

__version__ = '1.0.0'

__all__ = [
    # Data layer
    'MarketDataProvider', 'DataManager',
    
    # Strategy layer
    'Signal', 'SignalType', 'BaseStrategy', 'EnhancedBaseStrategy',
    
    # Backtest layer
    'Portfolio', 'BacktestEngine', 'BacktestResult',
    
    # Execution layer
    'Order', 'OrderManager', 'OrderType', 'OrderStatus',
    
    # Risk management
    'RiskManager',
    
    # Exchange connectors
    'BybitConnector',
    
    # Configuration
    'ConfigManager', 'config',
    
    # Filters
    'FilterManager', 'CommonFilters',
]