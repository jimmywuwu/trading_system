from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class SignalType(Enum):
    """交易信號類型"""
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
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """後初始化處理"""
        if self.timestamp is None:
            import time
            self.timestamp = int(time.time() * 1000)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'price': self.price,
            'quantity': self.quantity,
            'timestamp': self.timestamp,
            'confidence': self.confidence,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Signal':
        """從字典創建Signal實例"""
        signal_type = SignalType(data['signal_type'])
        return cls(
            symbol=data['symbol'],
            signal_type=signal_type,
            price=data.get('price'),
            quantity=data.get('quantity'),
            timestamp=data.get('timestamp'),
            confidence=data.get('confidence', 1.0),
            metadata=data.get('metadata', {})
        )
    
    def is_buy_signal(self) -> bool:
        """是否為買入信號"""
        return self.signal_type == SignalType.BUY
    
    def is_sell_signal(self) -> bool:
        """是否為賣出信號"""
        return self.signal_type == SignalType.SELL
    
    def is_hold_signal(self) -> bool:
        """是否為持有信號"""
        return self.signal_type == SignalType.HOLD