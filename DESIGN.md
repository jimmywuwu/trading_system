# 交易系統架構設計文檔

## 概述
本文檔詳細說明交易系統的架構設計、類別抽象和設計理由。系統以快速驗證和策略回測為目標，採用模塊化、事件驅動的架構。

## 核心設計原則

1. **統一介面**: 回測和實盤使用相同的API介面
2. **事件驱動**: 模擬真實市場的事件流
3. **模塊化**: 各組件可獨立開發和測試
4. **可擴展**: 易於添加新交易所和策略
5. **風險優先**: 內建風險管理機制

## 詳細類別抽象設計

### 1. 數據層 (Data Layer)

#### 1.1 MarketDataProvider (市場數據提供者基類)

```python
from abc import ABC, abstractmethod
import pandas as pd
from typing import Callable, Optional, Dict, Any

class MarketDataProvider(ABC):
    """市場數據提供者抽象基類"""
    
    @abstractmethod
    def get_klines(self, symbol: str, interval: str, 
                   start_time: int, end_time: int, 
                   limit: Optional[int] = None) -> pd.DataFrame:
        """獲取K線數據"""
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """獲取即時行情"""
        pass
    
    @abstractmethod
    def subscribe_klines(self, symbol: str, interval: str, 
                        callback: Callable) -> None:
        """訂閱K線數據"""
        pass
    
    @abstractmethod
    def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """獲取訂單簿"""
        pass
```

**設計理由**:
- **統一介面**: 不同交易所有不同的API格式，統一介面讓上層策略代碼無需關心具體實現
- **數據格式標準化**: 統一返回pandas DataFrame，便於後續分析
- **支持歷史和實時**: 回測需要歷史數據，實盤需要實時數據，同一介面兼顧兩者
- **擴展性**: 新增交易所只需實現這個介面

#### 1.2 DataManager (數據管理器)

```python
class DataManager:
    """數據管理器，負責數據緩存、存儲和檢索"""
    
    def __init__(self, provider: MarketDataProvider, 
                 cache_dir: str = "./data"):
        self.provider = provider
        self.cache_dir = cache_dir
    
    def get_historical_data(self, symbol: str, interval: str, 
                           days: int) -> pd.DataFrame:
        """獲取歷史數據，優先從緩存讀取"""
        pass
    
    def save_data(self, data: pd.DataFrame, symbol: str, 
                  interval: str) -> None:
        """保存數據到本地"""
        pass
    
    def update_data(self, symbol: str, interval: str) -> None:
        """更新最新數據"""
        pass
```

**設計理由**:
- **性能優化**: 避免重複請求相同的歷史數據
- **離線支持**: 緩存數據支持離線回測
- **增量更新**: 只更新缺失的數據，提高效率

### 2. 策略層 (Strategy Layer)

#### 2.1 Signal (交易信號)

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class Signal:
    """交易信號數據結構"""
    symbol: str
    signal_type: SignalType
    price: Optional[float] = None
    quantity: Optional[float] = None
    timestamp: Optional[int] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = None
```

**設計理由**:
- **標準化信號**: 統一的信號格式便於執行層處理
- **包含元數據**: 信號可攜帶額外信息用於分析
- **信心度**: 支持信號強度，可用於倉位管理

#### 2.2 BaseStrategy (策略基類)

```python
class BaseStrategy(ABC):
    """策略基類，所有策略都需要繼承此類"""
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.parameters = parameters or {}
        self.data_buffer = []
        
    @abstractmethod
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """處理新的K線數據"""
        pass
    
    def on_tick(self, tick: Dict[str, Any]) -> Optional[Signal]:
        """處理tick數據（可選實現）"""
        return None
    
    def get_parameters(self) -> Dict[str, Any]:
        """獲取策略參數"""
        return self.parameters.copy()
    
    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """設置策略參數"""
        self.parameters.update(parameters)
    
    def warmup_period(self) -> int:
        """返回策略需要的暖身期長度"""
        return 0
    
    def reset(self) -> None:
        """重置策略狀態"""
        self.data_buffer.clear()
```

**設計理由**:
- **事件驅動**: on_bar方法讓策略響應市場事件
- **參數化**: 支持策略參數調優和回測
- **狀態管理**: 內建數據緩存和狀態重置
- **暖身期**: 支持技術指標計算所需的歷史數據長度

### 3. 回測引擎 (Backtest Engine)

#### 3.1 Portfolio (投資組合)

```python
@dataclass
class Position:
    """持倉信息"""
    symbol: str
    quantity: float
    avg_price: float
    unrealized_pnl: float = 0.0
    
class Portfolio:
    """投資組合管理"""
    
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        
    def get_total_value(self, prices: Dict[str, float]) -> float:
        """計算總資產價值"""
        pass
    
    def update_position(self, symbol: str, quantity: float, 
                       price: float) -> None:
        """更新持倉"""
        pass
    
    def get_metrics(self) -> Dict[str, float]:
        """計算績效指標"""
        pass
```

**設計理由**:
- **狀態追蹤**: 完整記錄持倉和交易歷史
- **績效計算**: 內建常用績效指標計算
- **資金管理**: 自動管理現金和持倉價值

#### 3.2 BacktestEngine (回測引擎)

```python
class BacktestEngine:
    """回測引擎主類"""
    
    def __init__(self, initial_capital: float = 100000,
                 commission: float = 0.001):
        self.portfolio = Portfolio(initial_capital)
        self.commission = commission
        self.strategies: List[BaseStrategy] = []
        self.risk_manager: Optional[RiskManager] = None
        
    def add_strategy(self, strategy: BaseStrategy) -> None:
        """添加策略"""
        self.strategies.append(strategy)
    
    def set_risk_manager(self, risk_manager: RiskManager) -> None:
        """設置風險管理器"""
        self.risk_manager = risk_manager
    
    def run(self, data: pd.DataFrame) -> BacktestResult:
        """運行回測"""
        for timestamp, bar in data.iterrows():
            # 為每個策略生成信號
            signals = []
            for strategy in self.strategies:
                signal = strategy.on_bar(bar)
                if signal:
                    signals.append(signal)
            
            # 風險管理檢查
            if self.risk_manager:
                signals = [s for s in signals 
                          if self.risk_manager.check_signal(s, self.portfolio)]
            
            # 執行交易
            for signal in signals:
                self._execute_signal(signal, bar)
        
        return self._generate_result()
```

**設計理由**:
- **多策略支持**: 可同時運行多個策略
- **事件模擬**: 逐條處理數據模擬真實交易
- **風險整合**: 內建風險管理檢查
- **結果分析**: 自動生成詳細的回測報告

### 4. 執行層 (Execution Layer)

#### 4.1 Order (訂單類)

```python
from enum import Enum

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"

class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

@dataclass
class Order:
    """訂單數據結構"""
    id: str
    symbol: str
    side: str  # BUY/SELL
    order_type: OrderType
    quantity: float
    price: Optional[float]
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: Optional[float] = None
    timestamp: int = 0
    commission: float = 0.0
```

#### 4.2 OrderManager (訂單管理器)

```python
class OrderManager:
    """訂單管理器"""
    
    def __init__(self, exchange_connector):
        self.exchange = exchange_connector
        self.pending_orders: Dict[str, Order] = {}
        
    def place_order(self, signal: Signal) -> Order:
        """下單"""
        order = self._signal_to_order(signal)
        
        # 實盤模式
        if self.exchange:
            result = self.exchange.place_order(order)
            order.id = result['order_id']
        
        self.pending_orders[order.id] = order
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """撤單"""
        if order_id in self.pending_orders:
            if self.exchange:
                result = self.exchange.cancel_order(order_id)
                if result['success']:
                    self.pending_orders[order_id].status = OrderStatus.CANCELLED
                return result['success']
        return False
    
    def update_orders(self) -> None:
        """更新訂單狀態"""
        if self.exchange:
            for order_id in list(self.pending_orders.keys()):
                status = self.exchange.get_order_status(order_id)
                self._update_order_status(order_id, status)
```

**設計理由**:
- **統一訂單接口**: 回測和實盤使用相同的訂單結構
- **狀態追蹤**: 完整的訂單生命週期管理
- **交易所抽象**: 與具體交易所實現解耦

### 5. 風險管理 (Risk Management)

#### 5.1 RiskManager (風險管理器)

```python
class RiskManager:
    """風險管理器"""
    
    def __init__(self, max_position_size: float = 0.1,
                 max_daily_loss: float = 0.02,
                 max_drawdown: float = 0.1):
        self.max_position_size = max_position_size
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown
        
    def check_signal(self, signal: Signal, 
                    portfolio: Portfolio) -> bool:
        """檢查信號是否符合風險要求"""
        # 檢查單一持倉大小
        if not self._check_position_size(signal, portfolio):
            return False
            
        # 檢查日損失限制
        if not self._check_daily_loss(portfolio):
            return False
            
        # 檢查最大回撤
        if not self._check_max_drawdown(portfolio):
            return False
            
        return True
    
    def calculate_position_size(self, signal: Signal, 
                               portfolio: Portfolio) -> float:
        """計算建議倉位大小"""
        account_value = portfolio.get_total_value()
        max_risk_amount = account_value * self.max_position_size
        
        if signal.price:
            max_shares = max_risk_amount / signal.price
            return min(max_shares, signal.quantity or max_shares)
        
        return 0.0
```

**設計理由**:
- **多層次風險控制**: 從單筆交易到整體組合的風險管理
- **參數化配置**: 風險參數可根據需要調整
- **實時檢查**: 每個交易信號都要通過風險檢查
- **倉位計算**: 自動計算合理的倉位大小

### 6. 交易所連接器 (Exchange Connector)

#### 6.1 BybitConnector (Bybit連接器)

```python
class BybitConnector(MarketDataProvider):
    """Bybit交易所連接器"""
    
    def __init__(self, api_key: str = None, api_secret: str = None,
                 testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.client = self._init_client()
        
    def get_klines(self, symbol: str, interval: str,
                   start_time: int, end_time: int,
                   limit: Optional[int] = None) -> pd.DataFrame:
        """實現獲取K線數據"""
        # 調用Bybit API獲取數據
        # 轉換為標準格式
        pass
    
    def place_order(self, order: Order) -> Dict[str, Any]:
        """下單到Bybit"""
        pass
    
    def get_account_info(self) -> Dict[str, Any]:
        """獲取帳戶信息"""
        pass
```

**設計理由**:
- **標準接口實現**: 實現MarketDataProvider接口保證一致性
- **測試支持**: 支持測試網便於開發調試
- **錯誤處理**: 包含完整的API錯誤處理機制

## 配置管理

### ConfigManager (配置管理器)

```python
import yaml
from pathlib import Path

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加載配置文件"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
    def get(self, key: str, default=None):
        """獲取配置值"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            value = value.get(k, {})
        return value if value != {} else default
    
    def save(self) -> None:
        """保存配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False)
```

## 總結

這個架構設計的核心優勢：

1. **統一抽象**: 所有組件都有清晰的抽象層，便於測試和替換
2. **事件驅動**: 模擬真實市場環境，回測結果更可信
3. **模塊化**: 各組件職責分明，可獨立開發和測試
4. **擴展性**: 新增交易所、策略或風險規則都很容易
5. **實用性**: 重點解決實際交易中的核心問題

這樣的設計既保證了系統的靈活性，又能快速驗證策略的有效性。

## 7. 過濾器系統 (Filter System)

### 7.1 設計理念

過濾器系統是交易系統中的關鍵組件，用於在策略生成信號後、執行交易前進行額外的篩選和驗證。這個設計提供多層次的過濾機制，確保只有符合特定條件的信號才會被執行。

### 7.2 多層次過濾架構

#### 策略級過濾器 (Strategy Level Filters)
```python
class EnhancedBaseStrategy(BaseStrategy):
    """增強的策略基類，支持內建過濾器"""
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        super().__init__(name, parameters)
        self.entry_filters = []  # 進場過濾器
        self.exit_filters = []   # 出場過濾器
    
    def add_entry_filter(self, filter_func: Callable[[pd.Series, List], bool]) -> None:
        """添加進場過濾器"""
        self.entry_filters.append(filter_func)
    
    def add_exit_filter(self, filter_func: Callable[[pd.Series, List], bool]) -> None:
        """添加出場過濾器"""
        self.exit_filters.append(filter_func)
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        # 生成原始信號
        raw_signal = self._generate_raw_signal(bar)
        
        if not raw_signal:
            return None
            
        # 應用相應的過濾器
        if raw_signal.signal_type == SignalType.BUY:
            if not self._apply_filters(bar, self.entry_filters):
                return None
        elif raw_signal.signal_type == SignalType.SELL:
            if not self._apply_filters(bar, self.exit_filters):
                return None
                
        return raw_signal
    
    def _apply_filters(self, bar: pd.Series, filters: List[Callable]) -> bool:
        """應用過濾器列表"""
        for filter_func in filters:
            if not filter_func(bar, self.data_buffer):
                return False
        return True
    
    @abstractmethod
    def _generate_raw_signal(self, bar: pd.Series) -> Optional[Signal]:
        """生成原始信號（由子類實現）"""
        pass
```

#### 系統級過濾器 (System Level Filters)
```python
class FilterManager:
    """過濾器管理器"""
    
    def __init__(self):
        self.global_filters = []  # 全局過濾器
        self.symbol_filters = {}  # 針對特定交易對的過濾器
        self.strategy_filters = {}  # 針對特定策略的過濾器
        
    def add_global_filter(self, filter_func: Callable[[Signal, pd.Series, Portfolio], bool]) -> None:
        """添加全局過濾器"""
        self.global_filters.append(filter_func)
    
    def add_symbol_filter(self, symbol: str, filter_func: Callable[[Signal, pd.Series, Portfolio], bool]) -> None:
        """為特定交易對添加過濾器"""
        if symbol not in self.symbol_filters:
            self.symbol_filters[symbol] = []
        self.symbol_filters[symbol].append(filter_func)
    
    def add_strategy_filter(self, strategy_name: str, filter_func: Callable[[Signal, pd.Series, Portfolio], bool]) -> None:
        """為特定策略添加過濾器"""
        if strategy_name not in self.strategy_filters:
            self.strategy_filters[strategy_name] = []
        self.strategy_filters[strategy_name].append(filter_func)
    
    def check_signal(self, signal: Signal, market_data: pd.Series, 
                    portfolio: Portfolio, strategy_name: str = None) -> bool:
        """檢查信號是否通過所有過濾器"""
        
        # 檢查全局過濾器
        for filter_func in self.global_filters:
            if not filter_func(signal, market_data, portfolio):
                return False
        
        # 檢查交易對特定過濾器
        if signal.symbol in self.symbol_filters:
            for filter_func in self.symbol_filters[signal.symbol]:
                if not filter_func(signal, market_data, portfolio):
                    return False
        
        # 檢查策略特定過濾器
        if strategy_name and strategy_name in self.strategy_filters:
            for filter_func in self.strategy_filters[strategy_name]:
                if not filter_func(signal, market_data, portfolio):
                    return False
        
        return True
```

### 7.3 常用過濾器實現

```python
class CommonFilters:
    """常用過濾器集合"""
    
    @staticmethod
    def volume_filter(min_volume: float):
        """成交量過濾器 - 確保足夠的流動性"""
        def filter_func(bar: pd.Series, data_buffer: List) -> bool:
            return bar.get('volume', 0) >= min_volume
        return filter_func
    
    @staticmethod
    def volatility_filter(min_volatility: float, period: int = 20):
        """波動率過濾器 - 避免在低波動期間交易"""
        def filter_func(bar: pd.Series, data_buffer: List) -> bool:
            if len(data_buffer) < period:
                return False
            
            prices = [b['close'] for b in data_buffer[-period:]]
            volatility = np.std(prices) / np.mean(prices)
            return volatility >= min_volatility
        return filter_func
    
    @staticmethod
    def time_filter(start_hour: int, end_hour: int):
        """時間過濾器 - 只在特定時間段交易"""
        def filter_func(bar: pd.Series, data_buffer: List) -> bool:
            hour = pd.to_datetime(bar.name).hour
            return start_hour <= hour <= end_hour
        return filter_func
    
    @staticmethod
    def trend_filter(period: int = 50):
        """趨勢過濾器 - 只在上升趨勢中做多"""
        def filter_func(signal: Signal, market_data: pd.Series, 
                       portfolio: Portfolio) -> bool:
            if signal.signal_type != SignalType.BUY:
                return True  # 對賣出信號不限制
            
            # 需要從data_manager獲取更多歷史數據來計算趨勢
            # 這裡是簡化實現
            return True
        return filter_func
    
    @staticmethod
    def drawdown_filter(max_drawdown: float = 0.1):
        """回撤過濾器 - 回撤過大時停止交易"""
        def filter_func(signal: Signal, market_data: pd.Series, 
                       portfolio: Portfolio) -> bool:
            current_drawdown = portfolio.get_current_drawdown()
            return current_drawdown < max_drawdown
        return filter_func
    
    @staticmethod
    def correlation_filter(other_symbols: List[str], max_correlation: float = 0.7):
        """相關性過濾器 - 避免持有高度相關的資產"""
        def filter_func(signal: Signal, market_data: pd.Series, 
                       portfolio: Portfolio) -> bool:
            if signal.signal_type != SignalType.BUY:
                return True
            
            # 檢查與現有持倉的相關性
            # 實際實現需要計算價格相關性
            current_positions = list(portfolio.positions.keys())
            overlapping_symbols = set(current_positions) & set(other_symbols)
            
            # 簡化邏輯：如果已經持有相關資產，則拒絕新的買入信號
            return len(overlapping_symbols) == 0
        return filter_func
    
    @staticmethod
    def position_limit_filter(max_positions: int):
        """持倉數量限制過濾器"""
        def filter_func(signal: Signal, market_data: pd.Series, 
                       portfolio: Portfolio) -> bool:
            if signal.signal_type != SignalType.BUY:
                return True
            
            current_position_count = len([p for p in portfolio.positions.values() 
                                        if p.quantity > 0])
            return current_position_count < max_positions
        return filter_func
    
    @staticmethod
    def price_filter(min_price: float = None, max_price: float = None):
        """價格範圍過濾器"""
        def filter_func(bar: pd.Series, data_buffer: List) -> bool:
            price = bar.get('close', 0)
            if min_price is not None and price < min_price:
                return False
            if max_price is not None and price > max_price:
                return False
            return True
        return filter_func
```

### 7.4 配置化過濾器

```python
# config/filters.yaml
filters:
  global:
    - type: "drawdown"
      max_drawdown: 0.15
    - type: "position_limit"
      max_positions: 5
  
  symbols:
    BTCUSDT:
      - type: "volume"
        min_volume: 1000000
      - type: "correlation"
        other_symbols: ["ETHUSDT", "ADAUSDT"]
        max_correlation: 0.7
  
  strategies:
    momentum_strategy:
      entry:
        - type: "volume"
          min_volume: 500000
        - type: "volatility"  
          min_volatility: 0.02
        - type: "time"
          start_hour: 9
          end_hour: 15
      exit:
        - type: "time"
          start_hour: 15
          end_hour: 16

class FilterConfigLoader:
    """過濾器配置加載器"""
    
    @staticmethod
    def load_filters_from_config(config_path: str, filter_manager: FilterManager) -> None:
        """從配置文件加載過濾器"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 加載全局過濾器
        if 'global' in config.get('filters', {}):
            for filter_config in config['filters']['global']:
                filter_func = FilterConfigLoader._create_filter(filter_config)
                if filter_func:
                    filter_manager.add_global_filter(filter_func)
        
        # 加載交易對特定過濾器
        if 'symbols' in config.get('filters', {}):
            for symbol, filters in config['filters']['symbols'].items():
                for filter_config in filters:
                    filter_func = FilterConfigLoader._create_filter(filter_config)
                    if filter_func:
                        filter_manager.add_symbol_filter(symbol, filter_func)
    
    @staticmethod
    def _create_filter(filter_config: Dict[str, Any]) -> Optional[Callable]:
        """根據配置創建過濾器函數"""
        filter_type = filter_config.get('type')
        
        if filter_type == 'volume':
            return CommonFilters.volume_filter(filter_config['min_volume'])
        elif filter_type == 'volatility':
            return CommonFilters.volatility_filter(
                filter_config['min_volatility'],
                filter_config.get('period', 20)
            )
        elif filter_type == 'time':
            return CommonFilters.time_filter(
                filter_config['start_hour'],
                filter_config['end_hour']
            )
        elif filter_type == 'drawdown':
            return CommonFilters.drawdown_filter(filter_config['max_drawdown'])
        elif filter_type == 'correlation':
            return CommonFilters.correlation_filter(
                filter_config['other_symbols'],
                filter_config.get('max_correlation', 0.7)
            )
        elif filter_type == 'position_limit':
            return CommonFilters.position_limit_filter(filter_config['max_positions'])
        
        return None
```

### 7.5 在回測引擎中整合過濾器

```python
class BacktestEngine:
    """增強的回測引擎，整合過濾器系統"""
    
    def __init__(self, initial_capital: float = 100000, commission: float = 0.001):
        self.portfolio = Portfolio(initial_capital)
        self.commission = commission
        self.strategies: List[BaseStrategy] = []
        self.risk_manager: Optional[RiskManager] = None
        self.filter_manager = FilterManager()  # 過濾器管理器
        
    def add_strategy(self, strategy: BaseStrategy) -> None:
        """添加策略"""
        self.strategies.append(strategy)
    
    def set_filter_manager(self, filter_manager: FilterManager) -> None:
        """設置過濾器管理器"""
        self.filter_manager = filter_manager
    
    def load_filters_from_config(self, config_path: str) -> None:
        """從配置文件加載過濾器"""
        FilterConfigLoader.load_filters_from_config(config_path, self.filter_manager)
    
    def run(self, data: pd.DataFrame) -> BacktestResult:
        """運行回測"""
        for timestamp, bar in data.iterrows():
            # 為每個策略生成信號
            signals = []
            for strategy in self.strategies:
                signal = strategy.on_bar(bar)
                if signal:
                    # 應用系統級過濾器
                    if self.filter_manager.check_signal(signal, bar, self.portfolio, strategy.name):
                        signals.append(signal)
            
            # 風險管理檢查
            if self.risk_manager:
                signals = [s for s in signals 
                          if self.risk_manager.check_signal(s, self.portfolio)]
            
            # 執行交易
            for signal in signals:
                self._execute_signal(signal, bar)
        
        return self._generate_result()
```

### 7.6 使用範例

```python
# 創建策略並添加策略級過濾器
strategy = MyEnhancedStrategy("momentum_strategy")
strategy.add_entry_filter(CommonFilters.volume_filter(min_volume=1000000))
strategy.add_entry_filter(CommonFilters.time_filter(start_hour=9, end_hour=15))
strategy.add_exit_filter(CommonFilters.time_filter(start_hour=15, end_hour=16))

# 設置回測引擎
engine = BacktestEngine()
engine.add_strategy(strategy)

# 添加系統級過濾器
engine.filter_manager.add_global_filter(
    CommonFilters.drawdown_filter(max_drawdown=0.15)
)
engine.filter_manager.add_global_filter(
    CommonFilters.position_limit_filter(max_positions=5)
)

# 為特定交易對添加過濾器
engine.filter_manager.add_symbol_filter(
    "BTCUSDT", 
    CommonFilters.correlation_filter(other_symbols=["ETHUSDT"])
)

# 或者從配置文件加載
engine.load_filters_from_config("config/filters.yaml")

# 運行回測
result = engine.run(historical_data)
```

### 7.7 過濾器系統的優勢

1. **多層次控制**: 提供策略級、系統級、交易對級的靈活過濾
2. **可組合性**: 多個過濾器可以組合使用，形成複雜的篩選邏輯
3. **配置化**: 過濾器參數可以通過配置文件動態調整
4. **可擴展性**: 易於添加新的過濾器類型
5. **一致性**: 回測和實盤使用相同的過濾器邏輯
6. **性能優化**: 早期過濾可以減少不必要的計算
7. **風險控制**: 多重過濾機制提供額外的風險保護

這個過濾器系統讓交易者可以精確控制進出場時機，並且可以輕鬆測試不同過濾器組合對策略績效的影響。