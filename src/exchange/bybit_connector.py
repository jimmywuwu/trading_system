import requests
import time
import hmac
import hashlib
import pandas as pd
from typing import Dict, Any, Optional, Callable, List
import logging
import json
from urllib.parse import urlencode

from ..data.market_data_provider import MarketDataProvider
from ..execution.order import Order, OrderStatus, OrderType


class BybitConnector(MarketDataProvider):
    """Bybit交易所連接器"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        # API端點
        if testnet:
            self.base_url = "https://api-testnet.bybit.com"
            self.ws_url = "wss://stream-testnet.bybit.com"
        else:
            self.base_url = "https://api.bybit.com"
            self.ws_url = "wss://stream.bybit.com"
        
        self.logger = logging.getLogger(__name__)
        
        # 請求限制管理
        self.request_count = 0
        self.last_request_time = 0
        self.rate_limit_per_second = 10
        
    def _generate_signature(self, params: Dict[str, Any], timestamp: str) -> str:
        """生成簽名"""
        if not self.api_secret:
            return ""
        
        # 按鍵排序並構建查詢字符串
        sorted_params = dict(sorted(params.items()))
        query_string = urlencode(sorted_params)
        
        # 構建簽名字符串
        sign_string = timestamp + self.api_key + query_string
        
        # 生成HMAC SHA256簽名
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _make_request(self, method: str, endpoint: str, params: Dict[str, Any] = None, 
                     signed: bool = False) -> Dict[str, Any]:
        """發送HTTP請求"""
        if params is None:
            params = {}
        
        # 限流控制
        self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TradingSystem/1.0'
        }
        
        if signed and self.api_key:
            timestamp = str(int(time.time() * 1000))
            headers['X-BAPI-API-KEY'] = self.api_key
            headers['X-BAPI-TIMESTAMP'] = timestamp
            
            if method.upper() == 'GET':
                headers['X-BAPI-SIGN'] = self._generate_signature(params, timestamp)
            else:
                # POST請求的簽名處理
                headers['X-BAPI-SIGN'] = self._generate_signature(params, timestamp)
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(url, json=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"不支持的請求方法: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"請求失敗: {url}, 錯誤: {e}")
            return {'retCode': -1, 'retMsg': str(e)}
    
    def _rate_limit(self) -> None:
        """限流控制"""
        current_time = time.time()
        
        # 重置計數器（每秒）
        if current_time - self.last_request_time >= 1.0:
            self.request_count = 0
            self.last_request_time = current_time
        
        # 如果達到限制，等待
        if self.request_count >= self.rate_limit_per_second:
            sleep_time = 1.0 - (current_time - self.last_request_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.request_count = 0
            self.last_request_time = time.time()
        
        self.request_count += 1
    
    # 實現MarketDataProvider接口
    def get_klines(self, symbol: str, interval: str, start_time: int, end_time: int, 
                   limit: Optional[int] = None) -> pd.DataFrame:
        """獲取K線數據"""
        try:
            params = {
                'category': 'spot',  # 現貨
                'symbol': symbol,
                'interval': interval,
                'start': start_time,
                'end': end_time
            }
            
            if limit:
                params['limit'] = min(limit, 1000)  # Bybit限制
            
            response = self._make_request('GET', '/v5/market/kline', params)
            
            if response.get('retCode') != 0:
                self.logger.error(f"獲取K線數據失敗: {response.get('retMsg')}")
                return pd.DataFrame()
            
            # 解析數據
            klines = response.get('result', {}).get('list', [])
            if not klines:
                return pd.DataFrame()
            
            # 轉換為DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])
            
            # 數據類型轉換
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
                df[col] = pd.to_numeric(df[col])
            
            # 設置時間索引並排序
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"獲取K線數據異常: {e}")
            return pd.DataFrame()
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """獲取即時行情"""
        try:
            params = {
                'category': 'spot',
                'symbol': symbol
            }
            
            response = self._make_request('GET', '/v5/market/tickers', params)
            
            if response.get('retCode') != 0:
                self.logger.error(f"獲取行情失敗: {response.get('retMsg')}")
                return {}
            
            tickers = response.get('result', {}).get('list', [])
            if not tickers:
                return {}
            
            ticker = tickers[0]
            
            return {
                'symbol': ticker.get('symbol'),
                'price': float(ticker.get('lastPrice', 0)),
                'bid': float(ticker.get('bid1Price', 0)),
                'ask': float(ticker.get('ask1Price', 0)),
                'volume': float(ticker.get('volume24h', 0)),
                'change': float(ticker.get('price24hPcnt', 0)),
                'high': float(ticker.get('highPrice24h', 0)),
                'low': float(ticker.get('lowPrice24h', 0))
            }
            
        except Exception as e:
            self.logger.error(f"獲取行情異常: {e}")
            return {}
    
    def subscribe_klines(self, symbol: str, interval: str, callback: Callable) -> None:
        """訂閱K線數據（WebSocket實現）"""
        # WebSocket訂閱實現較複雜，這裡提供基本框架
        self.logger.warning("WebSocket訂閱功能需要額外實現")
        pass
    
    def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """獲取訂單簿"""
        try:
            params = {
                'category': 'spot',
                'symbol': symbol,
                'limit': min(limit, 500)  # Bybit限制
            }
            
            response = self._make_request('GET', '/v5/market/orderbook', params)
            
            if response.get('retCode') != 0:
                self.logger.error(f"獲取訂單簿失敗: {response.get('retMsg')}")
                return {}
            
            orderbook = response.get('result', {})
            
            return {
                'symbol': symbol,
                'bids': [[float(bid[0]), float(bid[1])] for bid in orderbook.get('b', [])],
                'asks': [[float(ask[0]), float(ask[1])] for ask in orderbook.get('a', [])],
                'timestamp': orderbook.get('ts')
            }
            
        except Exception as e:
            self.logger.error(f"獲取訂單簿異常: {e}")
            return {}
    
    # 交易相關方法
    def place_order(self, order: Order) -> Dict[str, Any]:
        """下單到Bybit"""
        try:
            if not self.api_key or not self.api_secret:
                return {'success': False, 'error': '需要API密鑰進行交易'}
            
            # 構建訂單參數
            params = {
                'category': 'spot',
                'symbol': order.symbol,
                'side': order.side.value,
                'orderType': self._convert_order_type(order.order_type),
                'qty': str(order.quantity)
            }
            
            # 添加價格（限價單）
            if order.price and order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
                params['price'] = str(order.price)
            
            # 添加止損價格
            if order.stop_price and order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
                params['triggerPrice'] = str(order.stop_price)
            
            # 添加客戶端訂單ID
            params['orderLinkId'] = order.id
            
            response = self._make_request('POST', '/v5/order/create', params, signed=True)
            
            if response.get('retCode') == 0:
                result = response.get('result', {})
                return {
                    'success': True,
                    'order_id': result.get('orderId'),
                    'order_link_id': result.get('orderLinkId')
                }
            else:
                return {
                    'success': False,
                    'error': response.get('retMsg', 'Unknown error')
                }
                
        except Exception as e:
            self.logger.error(f"下單異常: {e}")
            return {'success': False, 'error': str(e)}
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """撤單"""
        try:
            params = {
                'category': 'spot',
                'orderId': order_id
            }
            
            response = self._make_request('POST', '/v5/order/cancel', params, signed=True)
            
            if response.get('retCode') == 0:
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': response.get('retMsg', 'Unknown error')
                }
                
        except Exception as e:
            self.logger.error(f"撤單異常: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """獲取訂單狀態"""
        try:
            params = {
                'category': 'spot',
                'orderId': order_id
            }
            
            response = self._make_request('GET', '/v5/order/realtime', params, signed=True)
            
            if response.get('retCode') == 0:
                orders = response.get('result', {}).get('list', [])
                if orders:
                    order_data = orders[0]
                    return {
                        'orderId': order_data.get('orderId'),
                        'status': self._convert_order_status(order_data.get('orderStatus')),
                        'filled_quantity': float(order_data.get('cumExecQty', 0)),
                        'avg_price': float(order_data.get('avgPrice', 0)),
                        'commission': float(order_data.get('cumExecFee', 0))
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"獲取訂單狀態異常: {e}")
            return None
    
    def get_account_info(self) -> Dict[str, Any]:
        """獲取帳戶信息"""
        try:
            params = {
                'accountType': 'SPOT'  # 現貨帳戶
            }
            
            response = self._make_request('GET', '/v5/account/wallet-balance', params, signed=True)
            
            if response.get('retCode') == 0:
                accounts = response.get('result', {}).get('list', [])
                if accounts:
                    account = accounts[0]
                    coins = account.get('coin', [])
                    
                    balances = {}
                    for coin in coins:
                        balances[coin.get('coin')] = {
                            'free': float(coin.get('walletBalance', 0)),
                            'locked': float(coin.get('locked', 0)),
                            'total': float(coin.get('walletBalance', 0)) + float(coin.get('locked', 0))
                        }
                    
                    return {
                        'accountType': account.get('accountType'),
                        'balances': balances,
                        'totalEquity': float(account.get('totalEquity', 0))
                    }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"獲取帳戶信息異常: {e}")
            return {}
    
    def get_trading_symbols(self) -> List[Dict[str, Any]]:
        """獲取可交易的交易對信息"""
        try:
            params = {
                'category': 'spot'
            }
            
            response = self._make_request('GET', '/v5/market/instruments-info', params)
            
            if response.get('retCode') == 0:
                symbols = response.get('result', {}).get('list', [])
                return [{
                    'symbol': symbol.get('symbol'),
                    'baseCoin': symbol.get('baseCoin'),
                    'quoteCoin': symbol.get('quoteCoin'),
                    'status': symbol.get('status'),
                    'minOrderQty': float(symbol.get('lotSizeFilter', {}).get('minOrderQty', 0)),
                    'maxOrderQty': float(symbol.get('lotSizeFilter', {}).get('maxOrderQty', 0)),
                    'tickSize': float(symbol.get('priceFilter', {}).get('tickSize', 0))
                } for symbol in symbols]
            
            return []
            
        except Exception as e:
            self.logger.error(f"獲取交易對信息異常: {e}")
            return []
    
    def _convert_order_type(self, order_type: OrderType) -> str:
        """轉換訂單類型到Bybit格式"""
        mapping = {
            OrderType.MARKET: 'Market',
            OrderType.LIMIT: 'Limit',
            OrderType.STOP: 'Market',  # Bybit的止損市價單
            OrderType.STOP_LIMIT: 'Limit'  # Bybit的止損限價單
        }
        return mapping.get(order_type, 'Limit')
    
    def _convert_order_status(self, bybit_status: str) -> str:
        """轉換Bybit訂單狀態到標準格式"""
        mapping = {
            'New': 'SUBMITTED',
            'PartiallyFilled': 'PARTIALLY_FILLED',
            'Filled': 'FILLED',
            'Cancelled': 'CANCELLED',
            'Rejected': 'REJECTED',
            'PartiallyFilledCanceled': 'CANCELLED'
        }
        return mapping.get(bybit_status, 'PENDING')
    
    def test_connection(self) -> bool:
        """測試連接"""
        try:
            response = self._make_request('GET', '/v5/market/time')
            return response.get('retCode') == 0
        except Exception:
            return False
    
    def __str__(self) -> str:
        """字符串表示"""
        mode = "TestNet" if self.testnet else "MainNet"
        auth = "Authenticated" if self.api_key else "Public Only"
        return f"BybitConnector({mode}, {auth})"