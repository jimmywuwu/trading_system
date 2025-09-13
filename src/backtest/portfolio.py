from dataclasses import dataclass, field
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime
import logging


@dataclass
class Position:
    """持倉信息"""
    symbol: str
    quantity: float
    avg_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    def update_unrealized_pnl(self, current_price: float) -> None:
        """更新未實現損益"""
        if self.quantity != 0:
            self.unrealized_pnl = (current_price - self.avg_price) * self.quantity
    
    def get_total_pnl(self) -> float:
        """獲取總損益"""
        return self.realized_pnl + self.unrealized_pnl
    
    def get_market_value(self, current_price: float) -> float:
        """獲取市場價值"""
        return self.quantity * current_price


@dataclass
class Trade:
    """交易記錄"""
    timestamp: int
    symbol: str
    side: str  # BUY/SELL
    quantity: float
    price: float
    commission: float = 0.0
    pnl: float = 0.0
    
    def get_trade_value(self) -> float:
        """獲取交易價值"""
        return self.quantity * self.price


class Portfolio:
    """投資組合管理"""
    
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        self.logger = logging.getLogger(__name__)
        
        # 記錄初始狀態
        self.equity_curve.append({
            'timestamp': int(datetime.now().timestamp() * 1000),
            'cash': self.cash,
            'total_value': self.cash,
            'positions_value': 0.0
        })
    
    def get_total_value(self, prices: Dict[str, float] = None) -> float:
        """計算總資產價值
        
        Args:
            prices: 當前價格字典
            
        Returns:
            總資產價值
        """
        total_value = self.cash
        
        if prices:
            for symbol, position in self.positions.items():
                if symbol in prices and position.quantity != 0:
                    market_value = position.get_market_value(prices[symbol])
                    total_value += market_value
        
        return total_value
    
    def update_position(self, symbol: str, quantity: float, price: float, 
                       commission: float = 0.0, timestamp: int = None) -> None:
        """更新持倉
        
        Args:
            symbol: 交易對符號
            quantity: 交易數量（正數為買入，負數為賣出）
            price: 交易價格
            commission: 手續費
            timestamp: 時間戳
        """
        if timestamp is None:
            timestamp = int(datetime.now().timestamp() * 1000)
        
        trade_value = quantity * price
        side = "BUY" if quantity > 0 else "SELL"
        
        # 更新現金
        self.cash -= trade_value + commission
        
        # 創建交易記錄
        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            side=side,
            quantity=abs(quantity),
            price=price,
            commission=commission
        )
        
        # 更新持倉
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol, 0, 0)
        
        position = self.positions[symbol]
        
        if position.quantity == 0:
            # 新開倉
            position.quantity = quantity
            position.avg_price = price
            trade.pnl = 0
        elif (position.quantity > 0 and quantity > 0) or (position.quantity < 0 and quantity < 0):
            # 加倉
            new_quantity = position.quantity + quantity
            position.avg_price = ((position.avg_price * position.quantity) + 
                                 (price * quantity)) / new_quantity
            position.quantity = new_quantity
            trade.pnl = 0
        else:
            # 減倉或平倉
            if abs(quantity) <= abs(position.quantity):
                # 部分平倉
                pnl = quantity * (price - position.avg_price) if position.quantity > 0 else quantity * (position.avg_price - price)
                position.realized_pnl += pnl
                position.quantity += quantity
                trade.pnl = pnl
            else:
                # 超過持倉量，先平倉再反向開倉
                close_quantity = -position.quantity
                open_quantity = quantity + position.quantity
                
                # 平倉損益
                close_pnl = close_quantity * (price - position.avg_price) if position.quantity > 0 else close_quantity * (position.avg_price - price)
                position.realized_pnl += close_pnl
                
                # 反向開倉
                position.quantity = open_quantity
                position.avg_price = price
                trade.pnl = close_pnl
        
        self.trades.append(trade)
        self.logger.info(f"交易執行: {symbol} {side} {abs(quantity)} @ {price}, PnL: {trade.pnl:.2f}")
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """獲取指定持倉"""
        return self.positions.get(symbol)
    
    def get_current_drawdown(self) -> float:
        """計算當前回撤"""
        if not self.equity_curve:
            return 0.0
        
        equity_values = [point['total_value'] for point in self.equity_curve]
        peak = max(equity_values)
        current = equity_values[-1]
        
        if peak == 0:
            return 0.0
        
        return (peak - current) / peak
    
    def update_equity_curve(self, prices: Dict[str, float], timestamp: int = None) -> None:
        """更新資產曲線
        
        Args:
            prices: 當前價格字典
            timestamp: 時間戳
        """
        if timestamp is None:
            timestamp = int(datetime.now().timestamp() * 1000)
        
        # 更新持倉的未實現損益
        positions_value = 0.0
        for symbol, position in self.positions.items():
            if symbol in prices and position.quantity != 0:
                position.update_unrealized_pnl(prices[symbol])
                positions_value += position.get_market_value(prices[symbol])
        
        total_value = self.cash + positions_value
        
        self.equity_curve.append({
            'timestamp': timestamp,
            'cash': self.cash,
            'total_value': total_value,
            'positions_value': positions_value
        })
    
    def get_metrics(self) -> Dict[str, float]:
        """計算績效指標"""
        if len(self.equity_curve) < 2:
            return {}
        
        equity_values = [point['total_value'] for point in self.equity_curve]
        
        # 總收益
        total_return = (equity_values[-1] - equity_values[0]) / equity_values[0]
        
        # 最大回撤
        max_drawdown = 0.0
        peak = equity_values[0]
        for value in equity_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 收益率序列
        returns = []
        for i in range(1, len(equity_values)):
            if equity_values[i-1] != 0:
                ret = (equity_values[i] - equity_values[i-1]) / equity_values[i-1]
                returns.append(ret)
        
        # Sharpe比率（假設無風險利率為0）
        sharpe_ratio = 0.0
        if returns and np.std(returns) != 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # 年化
        
        # 交易統計
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]
        
        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        
        return {
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            'total_commission': sum(t.commission for t in self.trades)
        }
    
    def get_equity_dataframe(self) -> pd.DataFrame:
        """獲取資產曲線DataFrame"""
        if not self.equity_curve:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.equity_curve)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    
    def get_trades_dataframe(self) -> pd.DataFrame:
        """獲取交易記錄DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        
        trades_data = []
        for trade in self.trades:
            trades_data.append({
                'timestamp': pd.to_datetime(trade.timestamp, unit='ms'),
                'symbol': trade.symbol,
                'side': trade.side,
                'quantity': trade.quantity,
                'price': trade.price,
                'commission': trade.commission,
                'pnl': trade.pnl
            })
        
        return pd.DataFrame(trades_data)