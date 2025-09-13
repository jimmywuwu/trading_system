from typing import Dict, List, Optional, Callable, Any
import logging
import threading
from datetime import datetime, timedelta

from .order import Order, OrderStatus, OrderType, OrderSide
from ..strategy.signal import Signal, SignalType


class OrderManager:
    """訂單管理器"""
    
    def __init__(self, exchange_connector=None):
        self.exchange = exchange_connector
        self.pending_orders: Dict[str, Order] = {}
        self.completed_orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        
        # 回調函數
        self.on_order_update: Optional[Callable[[Order], None]] = None
        self.on_order_filled: Optional[Callable[[Order], None]] = None
        self.on_order_cancelled: Optional[Callable[[Order], None]] = None
        
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        
        # 訂單管理配置
        self.auto_cancel_time = timedelta(hours=24)  # 24小時後自動取消未成交訂單
        self.max_pending_orders = 100  # 最大待處理訂單數
    
    def place_order(self, signal: Signal, order_type: OrderType = OrderType.MARKET, 
                   price: Optional[float] = None, quantity: Optional[float] = None) -> Optional[Order]:
        """下單
        
        Args:
            signal: 交易信號
            order_type: 訂單類型
            price: 價格（限價單必需）
            quantity: 數量（覆蓋信號中的數量）
            
        Returns:
            訂單對象或None
        """
        try:
            with self._lock:
                # 檢查待處理訂單數量
                if len(self.pending_orders) >= self.max_pending_orders:
                    self.logger.warning("待處理訂單數量已達上限，無法下單")
                    return None
                
                # 創建訂單
                order = self._signal_to_order(signal, order_type, price, quantity)
                if not order:
                    return None
                
                # 驗證訂單
                is_valid, error_msg = order.validate()
                if not is_valid:
                    self.logger.error(f"訂單驗證失敗: {error_msg}")
                    return None
                
                # 實盤模式：提交到交易所
                if self.exchange:
                    try:
                        result = self.exchange.place_order(order)
                        if result.get('success'):
                            order.exchange_order_id = result.get('order_id')
                            order.status = OrderStatus.SUBMITTED
                        else:
                            order.reject(result.get('error', 'Unknown error'))
                            self.logger.error(f"交易所下單失敗: {result.get('error')}")
                            return None
                    except Exception as e:
                        order.reject(str(e))
                        self.logger.error(f"下單異常: {e}")
                        return None
                
                # 添加到待處理訂單
                if order.is_active:
                    self.pending_orders[order.id] = order
                else:
                    self.completed_orders[order.id] = order
                
                self.order_history.append(order)
                self.logger.info(f"訂單已提交: {order}")
                
                # 觸發回調
                if self.on_order_update:
                    self.on_order_update(order)
                
                return order
                
        except Exception as e:
            self.logger.error(f"下單失敗: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """撤單
        
        Args:
            order_id: 訂單ID
            
        Returns:
            是否成功
        """
        try:
            with self._lock:
                order = self.pending_orders.get(order_id)
                if not order:
                    self.logger.warning(f"訂單不存在或已完成: {order_id}")
                    return False
                
                if not order.is_active:
                    self.logger.warning(f"訂單不是活躍狀態: {order_id}")
                    return False
                
                # 實盤模式：向交易所發送撤單請求
                if self.exchange and order.exchange_order_id:
                    try:
                        result = self.exchange.cancel_order(order.exchange_order_id)
                        if not result.get('success'):
                            self.logger.error(f"交易所撤單失敗: {result.get('error')}")
                            return False
                    except Exception as e:
                        self.logger.error(f"撤單異常: {e}")
                        return False
                
                # 更新訂單狀態
                order.cancel()
                
                # 移動到完成訂單
                self.completed_orders[order_id] = order
                del self.pending_orders[order_id]
                
                self.logger.info(f"訂單已撤銷: {order}")
                
                # 觸發回調
                if self.on_order_cancelled:
                    self.on_order_cancelled(order)
                if self.on_order_update:
                    self.on_order_update(order)
                
                return True
                
        except Exception as e:
            self.logger.error(f"撤單失敗: {e}")
            return False
    
    def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """撤銷所有訂單
        
        Args:
            symbol: 交易對符號，None表示所有交易對
            
        Returns:
            成功撤銷的訂單數量
        """
        cancelled_count = 0
        order_ids = list(self.pending_orders.keys())
        
        for order_id in order_ids:
            order = self.pending_orders.get(order_id)
            if order and (symbol is None or order.symbol == symbol):
                if self.cancel_order(order_id):
                    cancelled_count += 1
        
        self.logger.info(f"批量撤單完成: {cancelled_count} 個訂單")
        return cancelled_count
    
    def update_orders(self) -> None:
        """更新訂單狀態（實盤模式）"""
        if not self.exchange:
            return
        
        try:
            with self._lock:
                order_ids = list(self.pending_orders.keys())
                
                for order_id in order_ids:
                    order = self.pending_orders.get(order_id)
                    if not order or not order.exchange_order_id:
                        continue
                    
                    try:
                        status_data = self.exchange.get_order_status(order.exchange_order_id)
                        if status_data:
                            self._update_order_from_exchange(order, status_data)
                    except Exception as e:
                        self.logger.error(f"更新訂單狀態失敗 {order_id}: {e}")
        
        except Exception as e:
            self.logger.error(f"批量更新訂單狀態失敗: {e}")
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """獲取訂單"""
        return (self.pending_orders.get(order_id) or 
                self.completed_orders.get(order_id))
    
    def get_pending_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """獲取待處理訂單"""
        orders = list(self.pending_orders.values())
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders
    
    def get_completed_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """獲取已完成訂單"""
        orders = list(self.completed_orders.values())
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders
    
    def get_order_history(self, symbol: Optional[str] = None, 
                         limit: Optional[int] = None) -> List[Order]:
        """獲取訂單歷史"""
        orders = self.order_history.copy()
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        if limit:
            orders = orders[-limit:]
        return orders
    
    def cleanup_expired_orders(self) -> int:
        """清理過期訂單
        
        Returns:
            清理的訂單數量
        """
        cleaned_count = 0
        current_time = datetime.now()
        order_ids = list(self.pending_orders.keys())
        
        for order_id in order_ids:
            order = self.pending_orders.get(order_id)
            if not order:
                continue
            
            order_time = datetime.fromtimestamp(order.timestamp / 1000)
            if current_time - order_time > self.auto_cancel_time:
                self.logger.info(f"清理過期訂單: {order}")
                if self.cancel_order(order_id):
                    cleaned_count += 1
        
        return cleaned_count
    
    def _signal_to_order(self, signal: Signal, order_type: OrderType, 
                        price: Optional[float], quantity: Optional[float]) -> Optional[Order]:
        """將信號轉換為訂單"""
        try:
            # 確定訂單方向
            if signal.is_buy_signal():
                side = OrderSide.BUY
            elif signal.is_sell_signal():
                side = OrderSide.SELL
            else:
                self.logger.warning(f"不支持的信號類型: {signal.signal_type}")
                return None
            
            # 確定數量
            order_quantity = quantity or signal.quantity
            if not order_quantity or order_quantity <= 0:
                self.logger.warning("訂單數量無效")
                return None
            
            # 確定價格
            order_price = price or signal.price
            
            # 創建訂單
            order = Order(
                symbol=signal.symbol,
                side=side,
                order_type=order_type,
                quantity=order_quantity,
                price=order_price
            )
            
            # 添加信號元數據
            order.metadata.update(signal.metadata or {})
            order.metadata['signal_confidence'] = signal.confidence
            order.metadata['signal_timestamp'] = signal.timestamp
            
            return order
            
        except Exception as e:
            self.logger.error(f"信號轉換訂單失敗: {e}")
            return None
    
    def _update_order_from_exchange(self, order: Order, status_data: Dict[str, Any]) -> None:
        """根據交易所數據更新訂單狀態"""
        try:
            # 更新狀態
            old_status = order.status
            new_status = status_data.get('status')
            if new_status:
                order.status = OrderStatus(new_status)
            
            # 更新成交信息
            filled_quantity = status_data.get('filled_quantity', 0)
            if filled_quantity > order.filled_quantity:
                new_fill = filled_quantity - order.filled_quantity
                fill_price = status_data.get('avg_price', order.price or 0)
                commission = status_data.get('commission', 0)
                
                order.update_fill(new_fill, fill_price, commission)
                
                if self.on_order_filled:
                    self.on_order_filled(order)
            
            # 如果訂單完成，移動到完成列表
            if order.is_completed and order.id in self.pending_orders:
                self.completed_orders[order.id] = order
                del self.pending_orders[order.id]
            
            # 觸發更新回調
            if old_status != order.status and self.on_order_update:
                self.on_order_update(order)
                
        except Exception as e:
            self.logger.error(f"更新訂單狀態異常: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計信息"""
        total_orders = len(self.order_history)
        pending_count = len(self.pending_orders)
        filled_orders = [o for o in self.order_history if o.is_filled]
        cancelled_orders = [o for o in self.order_history if o.status == OrderStatus.CANCELLED]
        
        return {
            'total_orders': total_orders,
            'pending_orders': pending_count,
            'filled_orders': len(filled_orders),
            'cancelled_orders': len(cancelled_orders),
            'fill_rate': len(filled_orders) / total_orders if total_orders > 0 else 0,
            'cancel_rate': len(cancelled_orders) / total_orders if total_orders > 0 else 0,
            'total_commission': sum(o.commission for o in self.order_history)
        }
    
    def reset(self) -> None:
        """重置訂單管理器"""
        with self._lock:
            self.pending_orders.clear()
            self.completed_orders.clear()
            self.order_history.clear()
            self.logger.info("訂單管理器已重置")