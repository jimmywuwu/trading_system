"""增強的策略基類，支持過濾器系統"""

from typing import Optional, List, Callable
import pandas as pd

from .base import BaseStrategy, Signal, SignalType


class EnhancedBaseStrategy(BaseStrategy):
    """增強的策略基類，支持內建過濾器"""
    
    def __init__(self, name: str, parameters: dict = None):
        super().__init__(name, parameters)
        self.entry_filters: List[Callable[[pd.Series, List], bool]] = []  # 進場過濾器
        self.exit_filters: List[Callable[[pd.Series, List], bool]] = []   # 出場過濾器
    
    def add_entry_filter(self, filter_func: Callable[[pd.Series, List], bool]) -> None:
        """
        添加進場過濾器
        
        Args:
            filter_func: 過濾器函數，接受 (bar, data_buffer)，返回 bool
        """
        self.entry_filters.append(filter_func)
    
    def add_exit_filter(self, filter_func: Callable[[pd.Series, List], bool]) -> None:
        """
        添加出場過濾器
        
        Args:
            filter_func: 過濾器函數，接受 (bar, data_buffer)，返回 bool
        """
        self.exit_filters.append(filter_func)
    
    def remove_entry_filter(self, filter_func: Callable) -> bool:
        """
        移除進場過濾器
        
        Args:
            filter_func: 要移除的過濾器函數
            
        Returns:
            是否成功移除
        """
        try:
            self.entry_filters.remove(filter_func)
            return True
        except ValueError:
            return False
    
    def remove_exit_filter(self, filter_func: Callable) -> bool:
        """
        移除出場過濾器
        
        Args:
            filter_func: 要移除的過濾器函數
            
        Returns:
            是否成功移除
        """
        try:
            self.exit_filters.remove(filter_func)
            return True
        except ValueError:
            return False
    
    def clear_filters(self) -> None:
        """清除所有過濾器"""
        self.entry_filters.clear()
        self.exit_filters.clear()
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """
        處理新的K線數據，整合過濾器邏輯
        
        Args:
            bar: K線數據
            
        Returns:
            過濾後的交易信號或None
        """
        # 添加數據到緩存
        self.add_data(bar)
        
        # 檢查是否準備好
        if not self.is_ready():
            return None
        
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
        """
        應用過濾器列表
        
        Args:
            bar: 當前K線數據
            filters: 過濾器函數列表
            
        Returns:
            是否通過所有過濾器
        """
        for filter_func in filters:
            try:
                if not filter_func(bar, self.data_buffer):
                    return False
            except Exception as e:
                # 過濾器出錯時，記錄錯誤但不阻止交易
                print(f"Filter error in {self.name}: {e}")
                return False
        return True
    
    def _generate_raw_signal(self, bar: pd.Series) -> Optional[Signal]:
        """
        生成原始信號（由子類實現）
        
        Args:
            bar: K線數據
            
        Returns:
            原始交易信號
        """
        # 這個方法需要由具體策略實現
        # 保持向後兼容，如果子類沒有實現這個方法，就調用原來的方法
        return self._legacy_on_bar(bar)
    
    def _legacy_on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """向後兼容的方法，子類可以重寫這個方法而不是on_bar"""
        return None
    
    def reset(self) -> None:
        """重置策略狀態"""
        super().reset()
        # 注意：這裡不清除過濾器，因為過濾器是策略配置的一部分
    
    def get_filter_info(self) -> dict:
        """
        獲取過濾器信息
        
        Returns:
            過濾器信息字典
        """
        return {
            'entry_filters_count': len(self.entry_filters),
            'exit_filters_count': len(self.exit_filters),
            'total_filters': len(self.entry_filters) + len(self.exit_filters)
        }