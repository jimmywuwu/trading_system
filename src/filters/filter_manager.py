from typing import Dict, List, Callable, Any, Optional
import logging
import pandas as pd
import numpy as np

from ..strategy.signal import Signal, SignalType
from ..backtest.portfolio import Portfolio


class FilterManager:
    """過濾器管理器"""
    
    def __init__(self):
        self.global_filters: List[Callable[[Signal, pd.Series, Portfolio], bool]] = []  # 全局過濾器
        self.symbol_filters: Dict[str, List[Callable]] = {}  # 針對特定交易對的過濾器
        self.strategy_filters: Dict[str, List[Callable]] = {}  # 針對特定策略的過濾器
        
        self.logger = logging.getLogger(__name__)
        
        # 過濾統計
        self.filter_stats: Dict[str, Dict] = {
            'total_signals': 0,
            'filtered_signals': 0,
            'filter_reasons': {}
        }
        
    def add_global_filter(self, filter_func: Callable[[Signal, pd.Series, Portfolio], bool], 
                         name: Optional[str] = None) -> None:
        """添加全局過濾器
        
        Args:
            filter_func: 過濾器函數，返回True表示通過
            name: 過濾器名稱（用於統計）
        """
        self.global_filters.append(filter_func)
        filter_name = name or filter_func.__name__
        self.logger.info(f"已添加全局過濾器: {filter_name}")
    
    def add_symbol_filter(self, symbol: str, 
                         filter_func: Callable[[Signal, pd.Series, Portfolio], bool],
                         name: Optional[str] = None) -> None:
        """為特定交易對添加過濾器
        
        Args:
            symbol: 交易對符號
            filter_func: 過濾器函數
            name: 過濾器名稱
        """
        if symbol not in self.symbol_filters:
            self.symbol_filters[symbol] = []
        self.symbol_filters[symbol].append(filter_func)
        
        filter_name = name or filter_func.__name__
        self.logger.info(f"已為 {symbol} 添加過濾器: {filter_name}")
    
    def add_strategy_filter(self, strategy_name: str, 
                           filter_func: Callable[[Signal, pd.Series, Portfolio], bool],
                           name: Optional[str] = None) -> None:
        """為特定策略添加過濾器
        
        Args:
            strategy_name: 策略名稱
            filter_func: 過濾器函數
            name: 過濾器名稱
        """
        if strategy_name not in self.strategy_filters:
            self.strategy_filters[strategy_name] = []
        self.strategy_filters[strategy_name].append(filter_func)
        
        filter_name = name or filter_func.__name__
        self.logger.info(f"已為策略 {strategy_name} 添加過濾器: {filter_name}")
    
    def check_signal(self, signal: Signal, market_data: pd.Series, 
                    portfolio: Portfolio, strategy_name: str = None) -> bool:
        """檢查信號是否通過所有過濾器
        
        Args:
            signal: 交易信號
            market_data: 市場數據
            portfolio: 投資組合
            strategy_name: 策略名稱（可選）
            
        Returns:
            是否通過所有過濾器
        """
        self.filter_stats['total_signals'] += 1
        
        try:
            # 檢查全局過濾器
            for i, filter_func in enumerate(self.global_filters):
                if not self._apply_filter(filter_func, signal, market_data, portfolio, f"global_{i}"):
                    return False
            
            # 檢查交易對特定過濾器
            if signal.symbol in self.symbol_filters:
                for i, filter_func in enumerate(self.symbol_filters[signal.symbol]):
                    if not self._apply_filter(filter_func, signal, market_data, portfolio, f"symbol_{signal.symbol}_{i}"):
                        return False
            
            # 檢查策略特定過濾器
            if strategy_name and strategy_name in self.strategy_filters:
                for i, filter_func in enumerate(self.strategy_filters[strategy_name]):
                    if not self._apply_filter(filter_func, signal, market_data, portfolio, f"strategy_{strategy_name}_{i}"):
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"過濾器檢查異常: {e}")
            return False  # 異常時拒絕信號
    
    def _apply_filter(self, filter_func: Callable, signal: Signal, market_data: pd.Series,
                     portfolio: Portfolio, filter_name: str) -> bool:
        """應用單個過濾器"""
        try:
            result = filter_func(signal, market_data, portfolio)
            if not result:
                self.filter_stats['filtered_signals'] += 1
                if filter_name not in self.filter_stats['filter_reasons']:
                    self.filter_stats['filter_reasons'][filter_name] = 0
                self.filter_stats['filter_reasons'][filter_name] += 1
                
                self.logger.debug(f"信號被過濾器拒絕: {filter_name}")
            return result
        except Exception as e:
            self.logger.error(f"過濾器 {filter_name} 執行異常: {e}")
            return False
    
    def remove_global_filter(self, index: int) -> bool:
        """移除全局過濾器
        
        Args:
            index: 過濾器索引
            
        Returns:
            是否成功移除
        """
        try:
            if 0 <= index < len(self.global_filters):
                removed = self.global_filters.pop(index)
                self.logger.info(f"已移除全局過濾器: {index}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"移除全局過濾器失敗: {e}")
            return False
    
    def remove_symbol_filters(self, symbol: str) -> bool:
        """移除交易對的所有過濾器
        
        Args:
            symbol: 交易對符號
            
        Returns:
            是否成功移除
        """
        try:
            if symbol in self.symbol_filters:
                count = len(self.symbol_filters[symbol])
                del self.symbol_filters[symbol]
                self.logger.info(f"已移除 {symbol} 的 {count} 個過濾器")
                return True
            return False
        except Exception as e:
            self.logger.error(f"移除交易對過濾器失敗: {e}")
            return False
    
    def remove_strategy_filters(self, strategy_name: str) -> bool:
        """移除策略的所有過濾器
        
        Args:
            strategy_name: 策略名稱
            
        Returns:
            是否成功移除
        """
        try:
            if strategy_name in self.strategy_filters:
                count = len(self.strategy_filters[strategy_name])
                del self.strategy_filters[strategy_name]
                self.logger.info(f"已移除策略 {strategy_name} 的 {count} 個過濾器")
                return True
            return False
        except Exception as e:
            self.logger.error(f"移除策略過濾器失敗: {e}")
            return False
    
    def clear_all_filters(self) -> None:
        """清除所有過濾器"""
        self.global_filters.clear()
        self.symbol_filters.clear()
        self.strategy_filters.clear()
        self.logger.info("已清除所有過濾器")
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """獲取過濾器統計信息"""
        total = self.filter_stats['total_signals']
        filtered = self.filter_stats['filtered_signals']
        
        return {
            'total_signals': total,
            'filtered_signals': filtered,
            'passed_signals': total - filtered,
            'filter_rate': filtered / total if total > 0 else 0,
            'filter_reasons': self.filter_stats['filter_reasons'].copy(),
            'global_filters_count': len(self.global_filters),
            'symbol_filters_count': sum(len(filters) for filters in self.symbol_filters.values()),
            'strategy_filters_count': sum(len(filters) for filters in self.strategy_filters.values())
        }
    
    def reset_stats(self) -> None:
        """重置統計信息"""
        self.filter_stats = {
            'total_signals': 0,
            'filtered_signals': 0,
            'filter_reasons': {}
        }
        self.logger.info("過濾器統計信息已重置")
    
    def __str__(self) -> str:
        """字符串表示"""
        return (f"FilterManager(global={len(self.global_filters)}, "
                f"symbol={len(self.symbol_filters)}, "
                f"strategy={len(self.strategy_filters)})")


class CommonFilters:
    """常用過濾器集合"""
    
    @staticmethod
    def volume_filter(min_volume: float):
        """成交量過濾器 - 確保足夠的流動性
        
        Args:
            min_volume: 最小成交量
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio: Portfolio) -> bool:
            volume = market_data.get('volume', 0)
            return volume >= min_volume
        
        filter_func.__name__ = f"volume_filter_min_{min_volume}"
        return filter_func
    
    @staticmethod
    def volatility_filter(min_volatility: float, period: int = 20):
        """波動率過濾器 - 避免在低波動期間交易
        
        Args:
            min_volatility: 最小波動率
            period: 計算期間
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio: Portfolio) -> bool:
            # 這裡需要歷史數據來計算波動率
            # 簡化實現，實際需要從數據管理器獲取歷史數據
            return True  # 暫時總是通過
        
        filter_func.__name__ = f"volatility_filter_min_{min_volatility}"
        return filter_func
    
    @staticmethod
    def time_filter(start_hour: int, end_hour: int):
        """時間過濾器 - 只在特定時間段交易
        
        Args:
            start_hour: 開始小時
            end_hour: 結束小時
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio: Portfolio) -> bool:
            if hasattr(market_data, 'name') and market_data.name:
                if isinstance(market_data.name, pd.Timestamp):
                    hour = market_data.name.hour
                else:
                    hour = pd.to_datetime(market_data.name).hour
                return start_hour <= hour <= end_hour
            return True  # 如果沒有時間信息，默認通過
        
        filter_func.__name__ = f"time_filter_{start_hour}_{end_hour}"
        return filter_func
    
    @staticmethod
    def trend_filter(period: int = 50):
        """趨勢過濾器 - 只在上升趨勢中做多
        
        Args:
            period: 趨勢計算期間
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio: Portfolio) -> bool:
            if signal.signal_type != SignalType.BUY:
                return True  # 對賣出信號不限制
            
            # 簡化實現：檢查當前價格是否高於某個基準
            # 實際實現需要計算移動平均線等趨勢指標
            return True
        
        filter_func.__name__ = f"trend_filter_period_{period}"
        return filter_func
    
    @staticmethod
    def drawdown_filter(max_drawdown: float = 0.1):
        """回撤過濾器 - 回撤過大時停止交易
        
        Args:
            max_drawdown: 最大允許回撤
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio: Portfolio) -> bool:
            current_drawdown = portfolio.get_current_drawdown()
            return current_drawdown < max_drawdown
        
        filter_func.__name__ = f"drawdown_filter_max_{max_drawdown}"
        return filter_func
    
    @staticmethod
    def correlation_filter(other_symbols: List[str], max_correlation: float = 0.7):
        """相關性過濾器 - 避免持有高度相關的資產
        
        Args:
            other_symbols: 其他相關交易對
            max_correlation: 最大相關性
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio: Portfolio) -> bool:
            if signal.signal_type != SignalType.BUY:
                return True
            
            # 檢查與現有持倉的相關性
            current_positions = list(portfolio.positions.keys())
            overlapping_symbols = set(current_positions) & set(other_symbols)
            
            # 簡化邏輯：如果已經持有相關資產，則拒絕新的買入信號
            return len(overlapping_symbols) == 0
        
        filter_func.__name__ = f"correlation_filter_max_{max_correlation}"
        return filter_func
    
    @staticmethod
    def position_limit_filter(max_positions: int):
        """持倉數量限制過濾器
        
        Args:
            max_positions: 最大持倉數量
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio: Portfolio) -> bool:
            if signal.signal_type != SignalType.BUY:
                return True
            
            current_position_count = len([p for p in portfolio.positions.values() 
                                        if p.quantity > 0])
            return current_position_count < max_positions
        
        filter_func.__name__ = f"position_limit_filter_max_{max_positions}"
        return filter_func
    
    @staticmethod
    def price_filter(min_price: float = None, max_price: float = None):
        """價格範圍過濾器
        
        Args:
            min_price: 最小價格
            max_price: 最大價格
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio: Portfolio) -> bool:
            price = market_data.get('close', 0)
            if min_price is not None and price < min_price:
                return False
            if max_price is not None and price > max_price:
                return False
            return True
        
        name_parts = []
        if min_price is not None:
            name_parts.append(f"min_{min_price}")
        if max_price is not None:
            name_parts.append(f"max_{max_price}")
        
        filter_func.__name__ = f"price_filter_{'_'.join(name_parts) if name_parts else 'no_limit'}"
        return filter_func
    
    @staticmethod
    def confidence_filter(min_confidence: float):
        """信號置信度過濾器
        
        Args:
            min_confidence: 最小置信度
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio: Portfolio) -> bool:
            return signal.confidence >= min_confidence
        
        filter_func.__name__ = f"confidence_filter_min_{min_confidence}"
        return filter_func
    
    @staticmethod
    def cash_filter(min_cash_ratio: float):
        """現金比例過濾器 - 確保保留足夠現金
        
        Args:
            min_cash_ratio: 最小現金比例
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio: Portfolio) -> bool:
            if signal.signal_type != SignalType.BUY:
                return True
            
            current_prices = {signal.symbol: market_data.get('close', 0)}
            total_value = portfolio.get_total_value(current_prices)
            
            if total_value <= 0:
                return False
            
            cash_ratio = portfolio.cash / total_value
            return cash_ratio >= min_cash_ratio
        
        filter_func.__name__ = f"cash_filter_min_{min_cash_ratio}"
        return filter_func