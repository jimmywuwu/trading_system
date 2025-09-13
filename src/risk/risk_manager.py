from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta
import numpy as np

from ..strategy.signal import Signal, SignalType
from ..backtest.portfolio import Portfolio


class RiskManager:
    """風險管理器"""
    
    def __init__(self, 
                 max_position_size: float = 0.1,
                 max_daily_loss: float = 0.02,
                 max_drawdown: float = 0.1,
                 max_correlation: float = 0.7,
                 max_positions: int = 10,
                 leverage_limit: float = 1.0):
        """
        Args:
            max_position_size: 單一持倉最大佔比（相對於總資產）
            max_daily_loss: 最大日損失限制（相對於總資產）
            max_drawdown: 最大回撤限制
            max_correlation: 最大相關性限制
            max_positions: 最大同時持倉數量
            leverage_limit: 槓桿限制
        """
        self.max_position_size = max_position_size
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown
        self.max_correlation = max_correlation
        self.max_positions = max_positions
        self.leverage_limit = leverage_limit
        
        # 風險監控數據
        self.daily_pnl_history: List[Dict] = []
        self.position_correlations: Dict[str, Dict[str, float]] = {}
        self.risk_metrics: Dict[str, float] = {}
        
        self.logger = logging.getLogger(__name__)
        
        # 風險事件記錄
        self.risk_events: List[Dict] = []
    
    def check_signal(self, signal: Signal, portfolio: Portfolio) -> bool:
        """檢查信號是否符合風險要求
        
        Args:
            signal: 交易信號
            portfolio: 投資組合
            
        Returns:
            是否通過風險檢查
        """
        try:
            # 檢查單一持倉大小
            if not self._check_position_size(signal, portfolio):
                self._log_risk_event("position_size_limit", signal.symbol, "單一持倉大小超限")
                return False
            
            # 檢查持倉數量限制
            if not self._check_position_count(signal, portfolio):
                self._log_risk_event("position_count_limit", signal.symbol, "持倉數量超限")
                return False
            
            # 檢查日損失限制
            if not self._check_daily_loss(portfolio):
                self._log_risk_event("daily_loss_limit", signal.symbol, "日損失超限")
                return False
            
            # 檢查最大回撤
            if not self._check_max_drawdown(portfolio):
                self._log_risk_event("max_drawdown_limit", signal.symbol, "最大回撤超限")
                return False
            
            # 檢查槓桿限制
            if not self._check_leverage_limit(signal, portfolio):
                self._log_risk_event("leverage_limit", signal.symbol, "槓桿超限")
                return False
            
            # 對於買入信號，檢查相關性
            if signal.is_buy_signal() and not self._check_correlation(signal, portfolio):
                self._log_risk_event("correlation_limit", signal.symbol, "相關性超限")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"風險檢查異常: {e}")
            return False
    
    def calculate_position_size(self, signal: Signal, portfolio: Portfolio) -> float:
        """計算建議倉位大小
        
        Args:
            signal: 交易信號
            portfolio: 投資組合
            
        Returns:
            建議的倉位大小
        """
        try:
            if not signal.price:
                return 0.0
            
            # 獲取賬戶總價值
            account_value = portfolio.get_total_value({signal.symbol: signal.price})
            
            # 基於風險的倉位計算
            max_risk_amount = account_value * self.max_position_size
            max_shares = max_risk_amount / signal.price
            
            # 考慮信號置信度
            confidence_adjusted_size = max_shares * signal.confidence
            
            # 考慮波動率調整（如果有歷史數據）
            volatility_adjusted_size = self._apply_volatility_adjustment(
                confidence_adjusted_size, signal.symbol, portfolio
            )
            
            # 對於賣出信號，檢查當前持倉
            if signal.is_sell_signal():
                position = portfolio.get_position(signal.symbol)
                if position:
                    return min(volatility_adjusted_size, position.quantity)
                else:
                    return 0.0
            
            # 最終數量不能超過信號指定的數量
            if signal.quantity:
                return min(volatility_adjusted_size, signal.quantity)
            
            return volatility_adjusted_size
            
        except Exception as e:
            self.logger.error(f"計算倉位大小異常: {e}")
            return 0.0
    
    def _check_position_size(self, signal: Signal, portfolio: Portfolio) -> bool:
        """檢查單一持倉大小"""
        if not signal.price:
            return True
        
        account_value = portfolio.get_total_value({signal.symbol: signal.price})
        if account_value <= 0:
            return False
        
        # 計算建議的倉位價值
        position_size = self.calculate_position_size(signal, portfolio)
        position_value = position_size * signal.price
        
        # 如果是增加持倉，考慮現有持倉
        if signal.is_buy_signal():
            existing_position = portfolio.get_position(signal.symbol)
            if existing_position:
                existing_value = existing_position.quantity * signal.price
                total_value = position_value + existing_value
                return total_value / account_value <= self.max_position_size
        
        return position_value / account_value <= self.max_position_size
    
    def _check_position_count(self, signal: Signal, portfolio: Portfolio) -> bool:
        """檢查持倉數量限制"""
        if signal.is_sell_signal():
            return True  # 賣出不增加持倉數量
        
        # 計算當前持倉數量（排除數量為0的持倉）
        current_positions = sum(1 for pos in portfolio.positions.values() if pos.quantity != 0)
        
        # 如果是新開倉位，檢查是否超過限制
        existing_position = portfolio.get_position(signal.symbol)
        if not existing_position or existing_position.quantity == 0:
            return current_positions < self.max_positions
        
        return True
    
    def _check_daily_loss(self, portfolio: Portfolio) -> bool:
        """檢查日損失限制"""
        try:
            today = datetime.now().date()
            
            # 計算今日損益
            today_pnl = 0.0
            for pnl_record in self.daily_pnl_history:
                if pnl_record['date'] == today:
                    today_pnl = pnl_record['pnl']
                    break
            
            # 如果沒有今日記錄，從交易記錄計算
            if today_pnl == 0.0:
                today_trades = [
                    trade for trade in portfolio.trades
                    if datetime.fromtimestamp(trade.timestamp / 1000).date() == today
                ]
                today_pnl = sum(trade.pnl for trade in today_trades)
            
            # 檢查是否超過日損失限制
            max_loss = portfolio.initial_capital * self.max_daily_loss
            return today_pnl > -max_loss
            
        except Exception as e:
            self.logger.error(f"檢查日損失異常: {e}")
            return True  # 異常時允許通過
    
    def _check_max_drawdown(self, portfolio: Portfolio) -> bool:
        """檢查最大回撤"""
        try:
            current_drawdown = portfolio.get_current_drawdown()
            return current_drawdown < self.max_drawdown
        except Exception as e:
            self.logger.error(f"檢查最大回撤異常: {e}")
            return True
    
    def _check_leverage_limit(self, signal: Signal, portfolio: Portfolio) -> bool:
        """檢查槓桿限制"""
        try:
            if not signal.price:
                return True
            
            # 計算當前槓桿
            total_position_value = 0.0
            for symbol, position in portfolio.positions.items():
                if position.quantity != 0:
                    # 這裡需要當前價格，簡化處理使用平均價格
                    total_position_value += abs(position.quantity * position.avg_price)
            
            # 如果是買入信號，加上新的倉位價值
            if signal.is_buy_signal():
                new_position_size = self.calculate_position_size(signal, portfolio)
                total_position_value += new_position_size * signal.price
            
            # 計算槓桿比率
            account_value = portfolio.get_total_value({signal.symbol: signal.price})
            if account_value <= 0:
                return False
            
            leverage = total_position_value / account_value
            return leverage <= self.leverage_limit
            
        except Exception as e:
            self.logger.error(f"檢查槓桿限制異常: {e}")
            return True
    
    def _check_correlation(self, signal: Signal, portfolio: Portfolio) -> bool:
        """檢查相關性限制"""
        try:
            # 簡化實現：檢查是否已持有高度相關的資產
            # 實際實現需要價格相關性計算
            
            current_symbols = [symbol for symbol, pos in portfolio.positions.items() 
                             if pos.quantity != 0]
            
            # 這裡是簡化的相關性檢查
            # 實際應該基於歷史價格數據計算相關係數
            similar_symbols = self._get_similar_symbols(signal.symbol)
            overlapping = set(current_symbols) & set(similar_symbols)
            
            return len(overlapping) == 0
            
        except Exception as e:
            self.logger.error(f"檢查相關性異常: {e}")
            return True
    
    def _get_similar_symbols(self, symbol: str) -> List[str]:
        """獲取相似的交易對（簡化實現）"""
        # 這是一個簡化的實現
        # 實際應該基於歷史數據計算相關性
        correlation_groups = {
            'crypto_majors': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
            'crypto_alts': ['ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'UNIUSDT'],
            'forex_majors': ['EURUSD', 'GBPUSD', 'USDJPY'],
            'commodities': ['XAUUSD', 'XAGUSD', 'WTIUSD']
        }
        
        for group, symbols in correlation_groups.items():
            if symbol in symbols:
                return [s for s in symbols if s != symbol]
        
        return []
    
    def _apply_volatility_adjustment(self, base_size: float, symbol: str, 
                                   portfolio: Portfolio) -> float:
        """應用波動率調整（簡化實現）"""
        # 這裡應該基於歷史波動率調整倉位大小
        # 高波動率 -> 減少倉位，低波動率 -> 增加倉位
        # 簡化實現直接返回原始大小
        return base_size
    
    def _log_risk_event(self, event_type: str, symbol: str, message: str) -> None:
        """記錄風險事件"""
        event = {
            'timestamp': datetime.now(),
            'type': event_type,
            'symbol': symbol,
            'message': message
        }
        self.risk_events.append(event)
        self.logger.warning(f"風險事件: {event_type} - {symbol}: {message}")
    
    def update_daily_pnl(self, portfolio: Portfolio) -> None:
        """更新日損益記錄"""
        try:
            today = datetime.now().date()
            
            # 計算今日損益
            today_trades = [
                trade for trade in portfolio.trades
                if datetime.fromtimestamp(trade.timestamp / 1000).date() == today
            ]
            today_pnl = sum(trade.pnl for trade in today_trades)
            
            # 更新或添加記錄
            for record in self.daily_pnl_history:
                if record['date'] == today:
                    record['pnl'] = today_pnl
                    return
            
            # 如果沒有找到今日記錄，添加新記錄
            self.daily_pnl_history.append({
                'date': today,
                'pnl': today_pnl
            })
            
            # 清理舊記錄（保留30天）
            cutoff_date = today - timedelta(days=30)
            self.daily_pnl_history = [
                record for record in self.daily_pnl_history
                if record['date'] >= cutoff_date
            ]
            
        except Exception as e:
            self.logger.error(f"更新日損益記錄異常: {e}")
    
    def get_risk_metrics(self, portfolio: Portfolio) -> Dict[str, float]:
        """獲取風險指標"""
        try:
            total_value = portfolio.get_total_value()
            
            # 計算當前持倉集中度
            position_concentration = 0.0
            if total_value > 0:
                max_position_value = 0.0
                for position in portfolio.positions.values():
                    if position.quantity != 0:
                        position_value = abs(position.quantity * position.avg_price)
                        max_position_value = max(max_position_value, position_value)
                position_concentration = max_position_value / total_value
            
            # 計算當前槓桿
            total_position_value = sum(
                abs(pos.quantity * pos.avg_price) 
                for pos in portfolio.positions.values() 
                if pos.quantity != 0
            )
            current_leverage = total_position_value / total_value if total_value > 0 else 0
            
            # 計算風險指標
            metrics = {
                'position_concentration': position_concentration,
                'current_leverage': current_leverage,
                'current_drawdown': portfolio.get_current_drawdown(),
                'position_count': sum(1 for pos in portfolio.positions.values() if pos.quantity != 0),
                'cash_ratio': portfolio.cash / total_value if total_value > 0 else 1.0,
                'total_unrealized_pnl': sum(pos.unrealized_pnl for pos in portfolio.positions.values()),
                'total_realized_pnl': sum(pos.realized_pnl for pos in portfolio.positions.values())
            }
            
            # 添加今日損益
            today = datetime.now().date()
            today_pnl = 0.0
            for record in self.daily_pnl_history:
                if record['date'] == today:
                    today_pnl = record['pnl']
                    break
            metrics['today_pnl'] = today_pnl
            
            self.risk_metrics = metrics
            return metrics
            
        except Exception as e:
            self.logger.error(f"計算風險指標異常: {e}")
            return {}
    
    def get_risk_report(self, portfolio: Portfolio) -> str:
        """生成風險報告"""
        metrics = self.get_risk_metrics(portfolio)
        
        report = f"""
=== 風險管理報告 ===
時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

持倉風險:
- 持倉集中度: {metrics.get('position_concentration', 0):.2%} (限制: {self.max_position_size:.2%})
- 當前槓桿: {metrics.get('current_leverage', 0):.2f}x (限制: {self.leverage_limit:.2f}x)
- 持倉數量: {int(metrics.get('position_count', 0))} (限制: {self.max_positions})
- 現金比例: {metrics.get('cash_ratio', 0):.2%}

損益風險:
- 當前回撤: {metrics.get('current_drawdown', 0):.2%} (限制: {self.max_drawdown:.2%})
- 今日損益: {metrics.get('today_pnl', 0):.2f}
- 未實現損益: {metrics.get('total_unrealized_pnl', 0):.2f}
- 已實現損益: {metrics.get('total_realized_pnl', 0):.2f}

風險事件數量: {len(self.risk_events)}
"""
        
        # 添加最近的風險事件
        if self.risk_events:
            report += "\n最近風險事件:\n"
            recent_events = self.risk_events[-5:]  # 最近5個事件
            for event in recent_events:
                report += f"- {event['timestamp'].strftime('%H:%M:%S')} {event['type']}: {event['message']}\n"
        
        return report
    
    def reset(self) -> None:
        """重置風險管理器"""
        self.daily_pnl_history.clear()
        self.position_correlations.clear()
        self.risk_metrics.clear()
        self.risk_events.clear()
        self.logger.info("風險管理器已重置")