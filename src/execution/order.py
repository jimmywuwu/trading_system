from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import uuid
import time


class OrderType(Enum):
    """訂單類型"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(Enum):
    """訂單狀態"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderSide(Enum):
    """訂單方向"""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Order:
    """訂單數據結構"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: Optional[float] = None
    avg_filled_price: Optional[float] = None
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    updated_timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    commission: float = 0.0
    exchange_order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """後初始化處理"""
        if isinstance(self.side, str):
            self.side = OrderSide(self.side)
        if isinstance(self.order_type, str):
            self.order_type = OrderType(self.order_type)
        if isinstance(self.status, str):
            self.status = OrderStatus(self.status)
    
    @property
    def remaining_quantity(self) -> float:
        """剩餘數量"""
        return self.quantity - self.filled_quantity
    
    @property
    def is_buy(self) -> bool:
        """是否為買單"""
        return self.side == OrderSide.BUY
    
    @property
    def is_sell(self) -> bool:
        """是否為賣單"""
        return self.side == OrderSide.SELL
    
    @property
    def is_market_order(self) -> bool:
        """是否為市價單"""
        return self.order_type == OrderType.MARKET
    
    @property
    def is_limit_order(self) -> bool:
        """是否為限價單"""
        return self.order_type == OrderType.LIMIT
    
    @property
    def is_active(self) -> bool:
        """訂單是否活躍（可能被執行）"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def is_completed(self) -> bool:
        """訂單是否完成（已填滿或已取消）"""
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]
    
    @property
    def is_filled(self) -> bool:
        """訂單是否已完全成交"""
        return self.status == OrderStatus.FILLED
    
    @property
    def fill_percentage(self) -> float:
        """成交百分比"""
        if self.quantity == 0:
            return 0.0
        return self.filled_quantity / self.quantity
    
    def update_fill(self, fill_quantity: float, fill_price: float, commission: float = 0.0) -> None:
        """更新成交信息
        
        Args:
            fill_quantity: 成交數量
            fill_price: 成交價格
            commission: 手續費
        """
        if fill_quantity <= 0:
            return
        
        # 更新成交數量
        self.filled_quantity += fill_quantity
        self.commission += commission
        
        # 計算平均成交價格
        if self.avg_filled_price is None:
            self.avg_filled_price = fill_price
        else:
            total_value = (self.avg_filled_price * (self.filled_quantity - fill_quantity) + 
                          fill_price * fill_quantity)
            self.avg_filled_price = total_value / self.filled_quantity
        
        self.filled_price = fill_price
        self.updated_timestamp = int(time.time() * 1000)
        
        # 更新狀態
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED
    
    def cancel(self) -> None:
        """取消訂單"""
        if self.is_active:
            self.status = OrderStatus.CANCELLED
            self.updated_timestamp = int(time.time() * 1000)
    
    def reject(self, reason: str = "") -> None:
        """拒絕訂單"""
        self.status = OrderStatus.REJECTED
        self.updated_timestamp = int(time.time() * 1000)
        if reason:
            self.metadata['reject_reason'] = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'avg_filled_price': self.avg_filled_price,
            'timestamp': self.timestamp,
            'updated_timestamp': self.updated_timestamp,
            'commission': self.commission,
            'exchange_order_id': self.exchange_order_id,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """從字典創建Order實例"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            symbol=data['symbol'],
            side=OrderSide(data['side']),
            order_type=OrderType(data['order_type']),
            quantity=data['quantity'],
            price=data.get('price'),
            stop_price=data.get('stop_price'),
            status=OrderStatus(data.get('status', 'PENDING')),
            filled_quantity=data.get('filled_quantity', 0.0),
            filled_price=data.get('filled_price'),
            avg_filled_price=data.get('avg_filled_price'),
            timestamp=data.get('timestamp', int(time.time() * 1000)),
            updated_timestamp=data.get('updated_timestamp', int(time.time() * 1000)),
            commission=data.get('commission', 0.0),
            exchange_order_id=data.get('exchange_order_id'),
            metadata=data.get('metadata', {})
        )
    
    def validate(self) -> tuple[bool, str]:
        """驗證訂單有效性
        
        Returns:
            (是否有效, 錯誤信息)
        """
        if self.quantity <= 0:
            return False, "訂單數量必須大於0"
        
        if self.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and self.price is None:
            return False, "限價單必須指定價格"
        
        if self.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and self.stop_price is None:
            return False, "止損單必須指定止損價格"
        
        if self.price is not None and self.price <= 0:
            return False, "價格必須大於0"
        
        if self.stop_price is not None and self.stop_price <= 0:
            return False, "止損價格必須大於0"
        
        return True, ""
    
    def __str__(self) -> str:
        """字符串表示"""
        return (f"Order(id={self.id[:8]}, symbol={self.symbol}, "
                f"side={self.side.value}, type={self.order_type.value}, "
                f"qty={self.quantity}, price={self.price}, status={self.status.value})")
    
    def __repr__(self) -> str:
        """詳細字符串表示"""
        return self.__str__()