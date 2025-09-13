"""市場數據提供者基類"""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any
import pandas as pd


class MarketDataProvider(ABC):
    """市場數據提供者抽象基類"""
    
    @abstractmethod
    def get_klines(self, symbol: str, interval: str, 
                   start_time: Optional[int] = None, 
                   end_time: Optional[int] = None, 
                   limit: Optional[int] = None) -> pd.DataFrame:
        """
        獲取K線數據
        
        Args:
            symbol: 交易對符號，如 "BTCUSDT"
            interval: 時間間隔，如 "1m", "5m", "1h", "1d"
            start_time: 開始時間戳 (秒)
            end_time: 結束時間戳 (秒)
            limit: 返回條數限制
            
        Returns:
            K線數據 DataFrame，包含列：
            - timestamp: 時間戳
            - open: 開盤價
            - high: 最高價
            - low: 最低價
            - close: 收盤價
            - volume: 成交量
        """
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        獲取即時行情
        
        Args:
            symbol: 交易對符號
            
        Returns:
            行情數據字典，包含：
            - symbol: 交易對
            - last_price: 最新價格
            - bid_price: 買一價
            - ask_price: 賣一價
            - volume_24h: 24小時成交量
            - change_24h: 24小時漲跌幅
            - timestamp: 時間戳
        """
        pass
    
    @abstractmethod
    def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        獲取訂單簿
        
        Args:
            symbol: 交易對符號
            limit: 深度限制
            
        Returns:
            訂單簿數據，包含：
            - bids: 買單列表 [[price, quantity], ...]
            - asks: 賣單列表 [[price, quantity], ...]
            - timestamp: 時間戳
        """
        pass
    
    def subscribe_klines(self, symbol: str, interval: str, 
                        callback: Callable[[Dict], None]) -> None:
        """
        訂閱K線數據 (可選實現)
        
        Args:
            symbol: 交易對符號
            interval: 時間間隔
            callback: 回調函數，接收K線數據
        """
        raise NotImplementedError("WebSocket subscription not implemented")
    
    def subscribe_ticker(self, symbol: str, 
                        callback: Callable[[Dict], None]) -> None:
        """
        訂閱行情數據 (可選實現)
        
        Args:
            symbol: 交易對符號
            callback: 回調函數，接收行情數據
        """
        raise NotImplementedError("WebSocket subscription not implemented")
    
    def get_exchange_info(self) -> Dict[str, Any]:
        """
        獲取交易所信息 (可選實現)
        
        Returns:
            交易所信息，包含交易對列表、交易規則等
        """
        return {}
    
    def get_symbols(self) -> list:
        """
        獲取所有可用交易對 (可選實現)
        
        Returns:
            交易對列表
        """
        info = self.get_exchange_info()
        return info.get('symbols', [])
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        驗證交易對是否有效
        
        Args:
            symbol: 交易對符號
            
        Returns:
            是否有效
        """
        try:
            symbols = self.get_symbols()
            return symbol in symbols if symbols else True
        except Exception:
            return True  # 無法驗證時假設有效