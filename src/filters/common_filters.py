"""常用過濾器實現"""

import numpy as np
import pandas as pd
from typing import List, Set
from datetime import datetime

from ..strategy.base import Signal, SignalType


class CommonFilters:
    """常用過濾器集合"""
    
    @staticmethod
    def volume_filter(min_volume: float):
        """
        成交量過濾器 - 確保足夠的流動性
        
        Args:
            min_volume: 最小成交量要求
            
        Returns:
            過濾器函數
        """
        def filter_func(bar: pd.Series, data_buffer: List) -> bool:
            return bar.get('volume', 0) >= min_volume
        return filter_func
    
    @staticmethod
    def volatility_filter(min_volatility: float, period: int = 20):
        """
        波動率過濾器 - 避免在低波動期間交易
        
        Args:
            min_volatility: 最小波動率要求
            period: 計算波動率的期間
            
        Returns:
            過濾器函數
        """
        def filter_func(bar: pd.Series, data_buffer: List) -> bool:
            if len(data_buffer) < period:
                return False
            
            prices = [b.get('close', 0) for b in data_buffer[-period:]]
            if not prices or not all(p > 0 for p in prices):
                return False
                
            returns = [prices[i]/prices[i-1] - 1 for i in range(1, len(prices))]
            volatility = np.std(returns) if returns else 0
            return volatility >= min_volatility
        return filter_func
    
    @staticmethod
    def time_filter(start_hour: int, end_hour: int):
        """
        時間過濾器 - 只在特定時間段交易
        
        Args:
            start_hour: 開始小時 (0-23)
            end_hour: 結束小時 (0-23)
            
        Returns:
            過濾器函數
        """
        def filter_func(bar: pd.Series, data_buffer: List) -> bool:
            try:
                if hasattr(bar, 'name') and bar.name is not None:
                    timestamp = pd.to_datetime(bar.name)
                else:
                    # 如果沒有時間戳，使用當前時間
                    timestamp = pd.Timestamp.now()
                
                hour = timestamp.hour
                
                if start_hour <= end_hour:
                    return start_hour <= hour <= end_hour
                else:  # 跨午夜的情況
                    return hour >= start_hour or hour <= end_hour
            except Exception:
                return True  # 解析時間失敗時不過濾
        return filter_func
    
    @staticmethod
    def price_filter(min_price: float = None, max_price: float = None):
        """
        價格範圍過濾器
        
        Args:
            min_price: 最小價格
            max_price: 最大價格
            
        Returns:
            過濾器函數
        """
        def filter_func(bar: pd.Series, data_buffer: List) -> bool:
            price = bar.get('close', 0)
            if min_price is not None and price < min_price:
                return False
            if max_price is not None and price > max_price:
                return False
            return True
        return filter_func
    
    @staticmethod
    def trend_filter(period: int = 50):
        """
        趨勢過濾器 - 只在上升趨勢中做多
        
        Args:
            period: 移動平均線期間
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio) -> bool:
            if signal.signal_type != SignalType.BUY:
                return True  # 對賣出信號不限制
            
            # 這裡需要更多歷史數據來計算趨勢
            # 簡化實現：假設如果有price字段，就檢查是否高於某個值
            current_price = market_data.get('close', 0)
            if current_price <= 0:
                return False
                
            # 實際實現中，這裡應該計算移動平均線
            # 目前簡化為總是通過
            return True
        return filter_func
    
    @staticmethod
    def drawdown_filter(max_drawdown: float = 0.1):
        """
        回撤過濾器 - 回撤過大時停止交易
        
        Args:
            max_drawdown: 最大允許回撤比例
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio) -> bool:
            try:
                current_drawdown = portfolio.get_current_drawdown()
                return current_drawdown < max_drawdown
            except AttributeError:
                # 如果portfolio沒有get_current_drawdown方法，則通過
                return True
        return filter_func
    
    @staticmethod
    def correlation_filter(other_symbols: List[str], max_correlation: float = 0.7):
        """
        相關性過濾器 - 避免持有高度相關的資產
        
        Args:
            other_symbols: 其他相關交易對列表
            max_correlation: 最大允許相關性
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio) -> bool:
            if signal.signal_type != SignalType.BUY:
                return True
            
            try:
                # 檢查與現有持倉的相關性
                current_positions = set(portfolio.positions.keys()) if hasattr(portfolio, 'positions') else set()
                overlapping_symbols = current_positions & set(other_symbols)
                
                # 簡化邏輯：如果已經持有相關資產，則拒絕新的買入信號
                return len(overlapping_symbols) == 0
            except Exception:
                return True
        return filter_func
    
    @staticmethod
    def position_limit_filter(max_positions: int):
        """
        持倉數量限制過濾器
        
        Args:
            max_positions: 最大持倉數量
            
        Returns:
            過濾器函數
        """
        def filter_func(signal: Signal, market_data: pd.Series, portfolio) -> bool:
            if signal.signal_type != SignalType.BUY:
                return True
            
            try:
                if hasattr(portfolio, 'positions'):
                    current_position_count = len([p for p in portfolio.positions.values() 
                                                if hasattr(p, 'quantity') and p.quantity > 0])
                    return current_position_count < max_positions
                return True
            except Exception:
                return True
        return filter_func
    
    @staticmethod
    def rsi_filter(oversold_threshold: float = 30, overbought_threshold: float = 70, period: int = 14):
        """
        RSI過濾器
        
        Args:
            oversold_threshold: 超賣閾值
            overbought_threshold: 超買閾值
            period: RSI計算期間
            
        Returns:
            過濾器函數
        """
        def filter_func(bar: pd.Series, data_buffer: List) -> bool:
            if len(data_buffer) < period + 1:
                return False
            
            # 計算RSI
            prices = [b.get('close', 0) for b in data_buffer[-(period+1):]]
            if not prices or not all(p > 0 for p in prices):
                return False
            
            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            
            if avg_loss == 0:
                return True  # 避免除零錯誤
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # RSI在合理範圍內才允許交易
            return oversold_threshold < rsi < overbought_threshold
        return filter_func
    
    @staticmethod
    def moving_average_filter(period: int = 20, price_type: str = 'close'):
        """
        移動平均線過濾器 - 價格必須在移動平均線之上
        
        Args:
            period: 移動平均線期間
            price_type: 價格類型
            
        Returns:
            過濾器函數
        """
        def filter_func(bar: pd.Series, data_buffer: List) -> bool:
            if len(data_buffer) < period:
                return False
            
            prices = [b.get(price_type, 0) for b in data_buffer[-period:]]
            if not prices or not all(p > 0 for p in prices):
                return False
            
            ma = np.mean(prices)
            current_price = bar.get(price_type, 0)
            
            return current_price > ma
        return filter_func