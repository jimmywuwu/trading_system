"""基礎策略類和數據結構"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import pandas as pd


class SignalType(Enum):
    """交易信號類型"""
    BUY = "BUY"
    SELL = "SELL" 
    HOLD = "HOLD"


@dataclass
class Signal:
    """交易信號數據結構"""
    symbol: str                           # 交易對
    signal_type: SignalType              # 信號類型
    price: Optional[float] = None        # 期望價格
    quantity: Optional[float] = None     # 數量
    timestamp: Optional[int] = None      # 時間戳
    confidence: float = 1.0              # 信心度 (0-1)
    metadata: Dict[str, Any] = field(default_factory=dict)  # 額外元數據
    
    def __post_init__(self):
        """後處理，確保數據正確性"""
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("Confidence must be between 0 and 1")
            
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("Quantity must be positive")


class BaseStrategy(ABC):
    """策略基類，所有策略都需要繼承此類"""
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        """
        初始化策略
        
        Args:
            name: 策略名稱
            parameters: 策略參數
        """
        self.name = name
        self.parameters = parameters or {}
        self.data_buffer: List[pd.Series] = []  # 數據緩存
        self._is_initialized = False
        
    @abstractmethod
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """
        處理新的K線數據
        
        Args:
            bar: K線數據，包含 open, high, low, close, volume 等
            
        Returns:
            交易信號或None
        """
        pass
    
    def on_tick(self, tick: Dict[str, Any]) -> Optional[Signal]:
        """
        處理tick數據（可選實現）
        
        Args:
            tick: tick數據
            
        Returns:
            交易信號或None
        """
        return None
    
    def on_init(self) -> None:
        """策略初始化（可選實現）"""
        pass
    
    def on_finish(self) -> None:
        """策略結束時調用（可選實現）"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """獲取策略參數"""
        return self.parameters.copy()
    
    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """
        設置策略參數
        
        Args:
            parameters: 新參數字典
        """
        self.parameters.update(parameters)
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """
        獲取單個參數
        
        Args:
            key: 參數鍵
            default: 默認值
            
        Returns:
            參數值
        """
        return self.parameters.get(key, default)
    
    def warmup_period(self) -> int:
        """
        返回策略需要的暖身期長度
        
        Returns:
            所需的歷史數據條數
        """
        return 0
    
    def reset(self) -> None:
        """重置策略狀態"""
        self.data_buffer.clear()
        self._is_initialized = False
        
    def add_data(self, bar: pd.Series) -> None:
        """
        添加數據到緩存
        
        Args:
            bar: K線數據
        """
        self.data_buffer.append(bar)
        
        # 保持緩存大小，避免內存溢出
        max_buffer_size = max(self.warmup_period() * 2, 200)
        if len(self.data_buffer) > max_buffer_size:
            self.data_buffer.pop(0)
    
    def get_latest_bars(self, n: int = 1) -> List[pd.Series]:
        """
        獲取最近n條數據
        
        Args:
            n: 數據條數
            
        Returns:
            最近n條數據
        """
        return self.data_buffer[-n:] if len(self.data_buffer) >= n else self.data_buffer
    
    def get_latest_prices(self, price_type: str = 'close', n: int = 1) -> List[float]:
        """
        獲取最近n個價格
        
        Args:
            price_type: 價格類型 ('open', 'high', 'low', 'close')
            n: 數據條數
            
        Returns:
            價格列表
        """
        bars = self.get_latest_bars(n)
        return [bar.get(price_type, 0.0) for bar in bars]
    
    def is_ready(self) -> bool:
        """
        檢查策略是否準備好交易
        
        Returns:
            是否準備好
        """
        return len(self.data_buffer) >= self.warmup_period()
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"