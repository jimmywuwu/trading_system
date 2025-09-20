from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, Dict, Any, List, Callable
import logging

from .signal import Signal, SignalType


class BaseStrategy(ABC):
    """策略基類，所有策略都需要繼承此類"""
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.parameters = parameters or {}
        self.data_buffer: List[pd.Series] = []
        self.max_buffer_size = 1000  # 最大緩存大小
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    @abstractmethod
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """處理新的K線數據
        
        Args:
            bar: K線數據，包含OHLCV等信息
            
        Returns:
            交易信號或None
        """
        pass
    
    def on_tick(self, tick: Dict[str, Any]) -> Optional[Signal]:
        """處理tick數據（可選實現）
        
        Args:
            tick: tick數據
            
        Returns:
            交易信號或None
        """
        return None
    
    def get_parameters(self) -> Dict[str, Any]:
        """獲取策略參數"""
        return self.parameters.copy()
    
    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """設置策略參數"""
        self.parameters.update(parameters)
        self.logger.info(f"策略參數已更新: {parameters}")
    
    def warmup_period(self) -> int:
        """返回策略需要的暖身期長度"""
        return 0
    
    def reset(self) -> None:
        """重置策略狀態"""
        self.data_buffer.clear()
        self.logger.info("策略狀態已重置")
    
    def update_buffer(self, bar: pd.Series) -> None:
        """更新數據緩存"""
        self.data_buffer.append(bar)
        
        # 限制緩存大小
        if len(self.data_buffer) > self.max_buffer_size:
            self.data_buffer.pop(0)
    
    def get_buffer_data(self, period: int = None) -> List[pd.Series]:
        """獲取緩存數據
        
        Args:
            period: 獲取的期數，None表示獲取全部
            
        Returns:
            緩存的K線數據列表
        """
        if period is None:
            return self.data_buffer.copy()
        return self.data_buffer[-period:] if len(self.data_buffer) >= period else self.data_buffer.copy()
    
    def get_buffer_dataframe(self, period: int = None) -> pd.DataFrame:
        """獲取緩存數據作為DataFrame
        
        Args:
            period: 獲取的期數，None表示獲取全部
            
        Returns:
            緩存的K線數據DataFrame
        """
        buffer_data = self.get_buffer_data(period)
        if not buffer_data:
            return pd.DataFrame()
        
        return pd.DataFrame(buffer_data)
    
    def is_ready(self) -> bool:
        """檢查策略是否準備就緒（有足夠的歷史數據）"""
        return len(self.data_buffer) >= self.warmup_period()
    
    def get_last_price(self) -> Optional[float]:
        """獲取最新價格"""
        if self.data_buffer:
            return self.data_buffer[-1].get('close')
        return None
    
    def calculate_returns(self, period: int) -> Optional[float]:
        """計算指定期間的收益率
        
        Args:
            period: 計算期間
            
        Returns:
            收益率或None
        """
        if len(self.data_buffer) < period + 1:
            return None
        
        current_price = self.data_buffer[-1]['close']
        previous_price = self.data_buffer[-(period + 1)]['close']
        
        return (current_price - previous_price) / previous_price


class EnhancedBaseStrategy(BaseStrategy):
    """增強的策略基類，支持內建過濾器"""
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        super().__init__(name, parameters)
        self.entry_filters: List[Callable[[pd.Series, List], bool]] = []  # 進場過濾器
        self.exit_filters: List[Callable[[pd.Series, List], bool]] = []   # 出場過濾器
    
    def add_entry_filter(self, filter_func: Callable[[pd.Series, List], bool]) -> None:
        """添加進場過濾器"""
        self.entry_filters.append(filter_func)
        self.logger.info(f"已添加進場過濾器: {filter_func.__name__}")
    
    def add_exit_filter(self, filter_func: Callable[[pd.Series, List], bool]) -> None:
        """添加出場過濾器"""
        self.exit_filters.append(filter_func)
        self.logger.info(f"已添加出場過濾器: {filter_func.__name__}")
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """處理新的K線數據，應用過濾器"""
        # 更新緩存
        self.update_buffer(bar)
        
        # 生成原始信號
        raw_signal = self._generate_raw_signal(bar)
        
        if not raw_signal:
            return None
            
        # 應用相應的過濾器
        if raw_signal.is_buy_signal():
            if not self._apply_filters(bar, self.entry_filters):
                self.logger.debug("買入信號被進場過濾器拒絕")
                return None
        elif raw_signal.is_sell_signal():
            if not self._apply_filters(bar, self.exit_filters):
                self.logger.debug("賣出信號被出場過濾器拒絕")
                return None
                
        return raw_signal
    
    def _apply_filters(self, bar: pd.Series, filters: List[Callable]) -> bool:
        """應用過濾器列表"""
        for filter_func in filters:
            try:
                if not filter_func(bar, self.data_buffer):
                    return False
            except Exception as e:
                self.logger.error(f"過濾器執行錯誤: {e}")
                return False
        return True
    
    @abstractmethod
    def _generate_raw_signal(self, bar: pd.Series) -> Optional[Signal]:
        """生成原始信號（由子類實現）"""
        pass
import pdb

class SimpleMomentumStrategy(BaseStrategy):
    """簡單動量策略 - 基於移動平均線交叉的策略
    
    這是一個經典的移動平均線策略實現：
    - 當短期移動平均線上穿長期移動平均線時產生買入信號（金叉）
    - 當短期移動平均線下穿長期移動平均線時產生賣出信號（死叉）
    
    適用於教學和測試目的。
    """
    
    def __init__(self, short_period: int = 5, long_period: int = 15, name: str = "SimpleMomentum"):
        """初始化簡單動量策略
        
        Args:
            short_period: 短期移動平均線週期
            long_period: 長期移動平均線週期
            name: 策略名稱
        """
        super().__init__(name, {
            'short_period': short_period,
            'long_period': long_period
        })
        self.short_period = short_period
        self.long_period = long_period
        self.position_opened = False  # 追蹤持倉狀態
        
        # 參數驗證
        if short_period >= long_period:
            raise ValueError("短期週期必須小於長期週期")
        if short_period <= 0 or long_period <= 0:
            raise ValueError("週期必須為正數")
    
    def warmup_period(self) -> int:
        """返回策略需要的暖身期長度"""
        return self.long_period + 1  # 需要額外一期來計算穿越
    
    def reset(self) -> None:
        """重置策略狀態"""
        super().reset()
        self.position_opened = False
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """處理新的K線數據並生成交易信號
        
        Args:
            bar: K線數據，包含OHLCV等信息
            
        Returns:
            交易信號或None
        """
        # 更新數據緩存
        self.update_buffer(bar)
        
        if not self.is_ready():
            return None
        
        # 獲取最近的價格數據
        recent_data = self.get_buffer_dataframe()
        if len(recent_data) < self.long_period + 1:
            return None
        
        prices = recent_data['close']
        
        # 計算移動平均線
        short_ma = prices.rolling(window=self.short_period).mean().iloc[-1]
        long_ma = prices.rolling(window=self.long_period).mean().iloc[-1]
        
        # 獲取前一期的移動平均線用於判斷穿越
        prev_short_ma = prices.rolling(window=self.short_period).mean().iloc[-2]
        prev_long_ma = prices.rolling(window=self.long_period).mean().iloc[-2]
        
        current_price = bar['close']
        
        # 金叉：短均線上穿長均線，生成買入信號
        if (short_ma > long_ma and prev_short_ma <= prev_long_ma and not self.position_opened):
            self.position_opened = True
            self.logger.debug(f"金叉信號: short_ma={short_ma:.2f}, long_ma={long_ma:.2f}")
            return Signal(
                symbol="BTCUSDT",  # 默認交易對，會被回測引擎覆蓋
                signal_type=SignalType.BUY,
                price=current_price,
                confidence=0.8,
                metadata={
                    'short_ma': short_ma,
                    'long_ma': long_ma,
                    'signal_type': 'golden_cross',
                    'strategy': self.name
                }
            )
        
        # 死叉：短均線下穿長均線，生成賣出信號
        elif (short_ma < long_ma and prev_short_ma >= prev_long_ma and self.position_opened):
            self.position_opened = False
            self.logger.debug(f"死叉信號: short_ma={short_ma:.2f}, long_ma={long_ma:.2f}")
            return Signal(
                symbol="BTCUSDT",  # 默認交易對，會被回測引擎覆蓋
                signal_type=SignalType.SELL,
                price=current_price,
                confidence=0.8,
                metadata={
                    'short_ma': short_ma,
                    'long_ma': long_ma,
                    'signal_type': 'death_cross',
                    'strategy': self.name
                }
            )
        
        return None
    
    def get_current_mas(self) -> Optional[Dict[str, float]]:
        """獲取當前的移動平均線值
        
        Returns:
            包含短期和長期移動平均線的字典，如果數據不足則返回None
        """
        if len(self.data_buffer) < self.long_period:
            return None
        
        recent_data = self.get_buffer_dataframe()
        prices = recent_data['close']
        
        return {
            'short_ma': prices.rolling(window=self.short_period).mean().iloc[-1],
            'long_ma': prices.rolling(window=self.long_period).mean().iloc[-1]
        }