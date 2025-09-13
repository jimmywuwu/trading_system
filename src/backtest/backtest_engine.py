import pandas as pd
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging
from datetime import datetime

from .portfolio import Portfolio
from ..strategy.base_strategy import BaseStrategy
from ..strategy.signal import Signal, SignalType


@dataclass
class BacktestResult:
    """回測結果"""
    portfolio: Portfolio
    metrics: Dict[str, float]
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    start_time: str
    end_time: str
    duration: str
    
    def summary(self) -> str:
        """生成結果摘要"""
        summary = f"""
=== 回測結果摘要 ===
回測期間: {self.start_time} 至 {self.end_time}
總收益率: {self.metrics.get('total_return', 0):.2%}
最大回撤: {self.metrics.get('max_drawdown', 0):.2%}
夏普比率: {self.metrics.get('sharpe_ratio', 0):.2f}
總交易次數: {int(self.metrics.get('total_trades', 0))}
勝率: {self.metrics.get('win_rate', 0):.2%}
平均盈利: {self.metrics.get('avg_win', 0):.2f}
平均虧損: {self.metrics.get('avg_loss', 0):.2f}
盈虧比: {self.metrics.get('profit_factor', 0):.2f}
總手續費: {self.metrics.get('total_commission', 0):.2f}
"""
        return summary


class BacktestEngine:
    """回測引擎主類"""
    
    def __init__(self, initial_capital: float = 100000, commission: float = 0.001):
        self.portfolio = Portfolio(initial_capital)
        self.commission = commission
        self.strategies: List[BaseStrategy] = []
        self.risk_manager = None
        self.filter_manager = None
        self.logger = logging.getLogger(__name__)
        
        # 回測配置
        self.slippage = 0.0001  # 滑點
        self.min_trade_amount = 10  # 最小交易金額
        
    def add_strategy(self, strategy: BaseStrategy) -> None:
        """添加策略"""
        self.strategies.append(strategy)
        self.logger.info(f"已添加策略: {strategy.name}")
    
    def set_risk_manager(self, risk_manager) -> None:
        """設置風險管理器"""
        self.risk_manager = risk_manager
        self.logger.info("已設置風險管理器")
    
    def set_filter_manager(self, filter_manager) -> None:
        """設置過濾器管理器"""
        self.filter_manager = filter_manager
        self.logger.info("已設置過濾器管理器")
    
    def run(self, data: pd.DataFrame, symbol: str = "BTCUSDT") -> BacktestResult:
        """運行回測
        
        Args:
            data: 市場數據DataFrame，包含OHLCV數據
            symbol: 交易對符號
            
        Returns:
            回測結果
        """
        self.logger.info(f"開始回測: {symbol}, 數據長度: {len(data)}")
        start_time = datetime.now()
        
        # 重置所有策略
        for strategy in self.strategies:
            strategy.reset()
        
        # 確保數據有時間索引
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        
        # 逐條處理數據
        for timestamp, bar in data.iterrows():
            self._process_bar(timestamp, bar, symbol)
        
        end_time = datetime.now()
        duration = str(end_time - start_time)
        
        # 生成結果
        result = self._generate_result(
            start_time=data.index[0].strftime("%Y-%m-%d %H:%M:%S"),
            end_time=data.index[-1].strftime("%Y-%m-%d %H:%M:%S"),
            duration=duration
        )
        
        self.logger.info("回測完成")
        return result
    
    def _process_bar(self, timestamp: pd.Timestamp, bar: pd.Series, symbol: str) -> None:
        """處理單個K線數據"""
        # 更新資產曲線
        current_prices = {symbol: bar['close']}
        bar_timestamp = int(timestamp.timestamp() * 1000)
        self.portfolio.update_equity_curve(current_prices, bar_timestamp)
        
        # 為每個策略生成信號
        signals = []
        for strategy in self.strategies:
            try:
                signal = strategy.on_bar(bar)
                if signal:
                    # 設置信號的symbol和timestamp
                    signal.symbol = symbol
                    signal.timestamp = bar_timestamp
                    signals.append((signal, strategy))
            except Exception as e:
                self.logger.error(f"策略 {strategy.name} 執行錯誤: {e}")
        
        # 應用過濾器
        if self.filter_manager:
            filtered_signals = []
            for signal, strategy in signals:
                if self.filter_manager.check_signal(signal, bar, self.portfolio, strategy.name):
                    filtered_signals.append((signal, strategy))
                else:
                    self.logger.debug(f"信號被過濾器拒絕: {signal.symbol} {signal.signal_type.value}")
            signals = filtered_signals
        
        # 風險管理檢查
        if self.risk_manager:
            risk_checked_signals = []
            for signal, strategy in signals:
                if self.risk_manager.check_signal(signal, self.portfolio):
                    risk_checked_signals.append((signal, strategy))
                else:
                    self.logger.debug(f"信號被風險管理器拒絕: {signal.symbol} {signal.signal_type.value}")
            signals = risk_checked_signals
        
        # 執行交易
        for signal, strategy in signals:
            self._execute_signal(signal, bar, bar_timestamp)
    
    def _execute_signal(self, signal: Signal, bar: pd.Series, timestamp: int) -> None:
        """執行交易信號"""
        try:
            # 確定交易價格（加入滑點）
            if signal.is_buy_signal():
                execution_price = bar['close'] * (1 + self.slippage)
            elif signal.is_sell_signal():
                execution_price = bar['close'] * (1 - self.slippage)
            else:
                return  # HOLD信號不執行交易
            
            # 確定交易數量
            trade_quantity = self._calculate_trade_quantity(signal, execution_price)
            
            if abs(trade_quantity) * execution_price < self.min_trade_amount:
                self.logger.debug(f"交易金額過小，跳過: {abs(trade_quantity) * execution_price}")
                return
            
            # 計算手續費
            trade_value = abs(trade_quantity) * execution_price
            commission = trade_value * self.commission
            
            # 檢查資金是否足夠
            if signal.is_buy_signal():
                required_cash = trade_value + commission
                if self.portfolio.cash < required_cash:
                    self.logger.warning(f"資金不足，無法執行買入: 需要 {required_cash:.2f}, 可用 {self.portfolio.cash:.2f}")
                    return
            
            # 執行交易
            self.portfolio.update_position(
                symbol=signal.symbol,
                quantity=trade_quantity,
                price=execution_price,
                commission=commission,
                timestamp=timestamp
            )
            
        except Exception as e:
            self.logger.error(f"執行交易失敗: {e}")
    
    def _calculate_trade_quantity(self, signal: Signal, price: float) -> float:
        """計算交易數量"""
        if signal.quantity:
            # 信號指定了數量
            quantity = signal.quantity
        else:
            # 根據信號類型計算數量
            if signal.is_buy_signal():
                # 買入：使用一定比例的可用資金
                available_cash = self.portfolio.cash * 0.95  # 留5%現金
                quantity = available_cash / price
            elif signal.is_sell_signal():
                # 賣出：賣出當前持倉
                position = self.portfolio.get_position(signal.symbol)
                if position and position.quantity > 0:
                    quantity = -position.quantity  # 負數表示賣出
                else:
                    return 0  # 沒有持倉，不執行賣出
            else:
                return 0
        
        # 確保買入為正數，賣出為負數
        if signal.is_sell_signal() and quantity > 0:
            quantity = -quantity
        
        return quantity
    
    def _generate_result(self, start_time: str, end_time: str, duration: str) -> BacktestResult:
        """生成回測結果"""
        metrics = self.portfolio.get_metrics()
        equity_curve = self.portfolio.get_equity_dataframe()
        trades = self.portfolio.get_trades_dataframe()
        
        return BacktestResult(
            portfolio=self.portfolio,
            metrics=metrics,
            equity_curve=equity_curve,
            trades=trades,
            start_time=start_time,
            end_time=end_time,
            duration=duration
        )
    
    def reset(self) -> None:
        """重置回測引擎"""
        self.portfolio = Portfolio(self.portfolio.initial_capital)
        for strategy in self.strategies:
            strategy.reset()
        self.logger.info("回測引擎已重置")


class MultiSymbolBacktestEngine(BacktestEngine):
    """多交易對回測引擎"""
    
    def run_multi_symbol(self, data_dict: Dict[str, pd.DataFrame]) -> BacktestResult:
        """運行多交易對回測
        
        Args:
            data_dict: 交易對到數據的映射
            
        Returns:
            回測結果
        """
        self.logger.info(f"開始多交易對回測: {list(data_dict.keys())}")
        start_time = datetime.now()
        
        # 重置所有策略
        for strategy in self.strategies:
            strategy.reset()
        
        # 獲取所有時間戳的聯集並排序
        all_timestamps = set()
        for symbol, data in data_dict.items():
            if not isinstance(data.index, pd.DatetimeIndex):
                data.index = pd.to_datetime(data.index)
                data_dict[symbol] = data
            all_timestamps.update(data.index)
        
        sorted_timestamps = sorted(all_timestamps)
        
        # 按時間順序處理所有數據
        for timestamp in sorted_timestamps:
            current_prices = {}
            
            # 收集當前時間點的所有數據
            for symbol, data in data_dict.items():
                if timestamp in data.index:
                    bar = data.loc[timestamp]
                    current_prices[symbol] = bar['close']
                    self._process_bar(timestamp, bar, symbol)
                elif len(data) > 0:
                    # 使用最近的價格
                    nearest_data = data[data.index <= timestamp]
                    if not nearest_data.empty:
                        current_prices[symbol] = nearest_data.iloc[-1]['close']
            
            # 更新資產曲線
            if current_prices:
                bar_timestamp = int(timestamp.timestamp() * 1000)
                self.portfolio.update_equity_curve(current_prices, bar_timestamp)
        
        end_time = datetime.now()
        duration = str(end_time - start_time)
        
        # 生成結果
        result = self._generate_result(
            start_time=sorted_timestamps[0].strftime("%Y-%m-%d %H:%M:%S"),
            end_time=sorted_timestamps[-1].strftime("%Y-%m-%d %H:%M:%S"),
            duration=duration
        )
        
        self.logger.info("多交易對回測完成")
        return result