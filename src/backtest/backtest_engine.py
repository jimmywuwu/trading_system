import pandas as pd
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging
from datetime import datetime

# 條件導入 - 支持單獨運行
try:
    from .portfolio import Portfolio
    from ..strategy.base_strategy import BaseStrategy  
    from ..strategy.signal import Signal, SignalType
except ImportError:
    # 當作為獨立腳本運行時的導入
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(current_dir))
    
    from portfolio import Portfolio
    from strategy.base_strategy import BaseStrategy
    from strategy.signal import Signal, SignalType


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

def main():
    """主函數 - 回測引擎單檔測試
    
    此函數演示如何使用回測引擎，包括：
    1. 生成模擬市場數據
    2. 創建簡單的移動平均策略
    3. 設置風險管理和過濾器
    4. 運行回測並分析結果
    """
    import numpy as np
    from datetime import datetime, timedelta
    import sys
    import os
    
    # 添加項目根目錄到路徑以便導入其他模塊
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    sys.path.insert(0, project_root)
    
    # 確保可以導入本地模塊
    sys.path.insert(0, os.path.dirname(current_dir))  # src目錄
    
    print("🚀 回測引擎單檔測試")
    print("=" * 60)
    try:
        # 設置日誌
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # =================== 1. 生成模擬市場數據 ===================
        print("\n📊 1. 生成模擬市場數據...")
        def generate_mock_data(days=60) -> pd.DataFrame:
            """生成模擬的BTCUSDT價格數據"""
            np.random.seed(42)  # 確保可重複性
            
            # 創建時間索引 (每小時一條數據)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            timestamps = pd.date_range(start=start_date, end=end_date, freq='1H')
            
            # 使用幾何布朗運動生成價格
            initial_price = 50000  # BTC初始價格
            volatility = 0.02     # 波動率
            drift = 0.0001        # 漂移率
            
            # 生成隨機收益率
            returns = np.random.normal(drift, volatility, len(timestamps))
            
            # 計算累積價格
            log_returns = np.cumsum(returns)
            prices = initial_price * np.exp(log_returns)
            
            # 生成OHLCV數據
            data = []
            for price in prices:
                # 在收盤價基礎上生成開高低
                noise = np.random.normal(0, price * 0.001)
                open_price = price + noise
                
                high_price = max(open_price, price) + abs(np.random.normal(0, price * 0.002))
                low_price = min(open_price, price) - abs(np.random.normal(0, price * 0.002))
                close_price = price
                volume = np.random.uniform(500, 2000)  # 隨機成交量
                
                data.append({
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })
            
            return pd.DataFrame(data, index=timestamps)
        # 生成數據
        market_data = generate_mock_data(days=30)  # 30天數據
        print(f"   ✅ 生成 {len(market_data)} 條數據")
        print(f"   📅 時間範圍: {market_data.index[0]} 至 {market_data.index[-1]}")
        print(f"   💰 價格範圍: ${market_data['close'].min():.2f} - ${market_data['close'].max():.2f}")
        
        # =================== 2. 創建簡單策略 ===================
        print("\n🎯 2. 創建簡單移動平均策略...")
        
        # 導入策略類
        try:
            from strategy.base_strategy import SimpleMomentumStrategy
        except ImportError:
            # 如果模塊導入失敗，使用絕對導入
            from src.strategy.base_strategy import SimpleMomentumStrategy
        
        # 創建策略實例
        strategy = SimpleMomentumStrategy(short_period=5, long_period=15)
        print(f"   ✅ 策略創建成功: {strategy.name}")
        print(f"   📊 參數: {strategy.get_parameters()}")
        print(f"   ⏰ 暖身期: {strategy.warmup_period()} 個週期")
        
        # =================== 3. 創建回測引擎 ===================
        print("\n🔧 3. 創建回測引擎...")
        
        engine = BacktestEngine(
            initial_capital=100000,  # 10萬美元初始資金
            commission=0.001         # 0.1% 手續費
        )
        
        engine.add_strategy(strategy)
        
        print(f"   ✅ 回測引擎創建成功")
        print(f"   💰 初始資金: ${engine.portfolio.initial_capital:,.2f}")
        print(f"   💸 手續費率: {engine.commission:.1%}")
        print(f"   📉 滑點: {engine.slippage:.2%}")
        
        # =================== 4. 添加風險管理 ===================
        print("\n🛡️ 4. 添加風險管理...")
        
        # 導入風險管理器（如果存在）
        try:
            from risk.risk_manager import RiskManager
            
            risk_manager = RiskManager(
                max_position_size=0.8,    # 單一持倉最大80%
                max_daily_loss=0.05,      # 日損失限制5%
                max_drawdown=0.2,         # 最大回撤20%
                max_positions=2           # 最多2個持倉
            )
            engine.set_risk_manager(risk_manager)
            print("   ✅ 風險管理器已設置")
            
        except ImportError:
            print("   ⚠️ 風險管理器模塊未找到，跳過風險管理設置")
        
        # =================== 5. 添加過濾器 ===================
        print("\n🔍 5. 添加信號過濾器...")
        
        try:
            from filters.filter_manager import FilterManager, CommonFilters
            
            filter_manager = FilterManager()
            
            # 添加成交量過濾器
            filter_manager.add_global_filter(
                CommonFilters.volume_filter(min_volume=1000),
                name="volume_filter"
            )
            
            # 添加現金保留過濾器
            filter_manager.add_global_filter(
                CommonFilters.cash_filter(min_cash_ratio=0.1),
                name="cash_reserve"
            )
            
            engine.set_filter_manager(filter_manager)
            print("   ✅ 過濾器已設置")
            
        except ImportError as e:
            print(f"   ⚠️ 過濾器模塊未找到，跳過過濾器設置: {e}")
        
        # =================== 6. 運行回測 ===================
        print("\n🚀 6. 運行回測...")
        print("   正在處理數據...")
        
        # 運行回測
        result = engine.run(market_data, symbol="BTCUSDT")
        
        print("   ✅ 回測完成!")
        
        # =================== 7. 分析結果 ===================
        print("\n📈 7. 回測結果分析")
        print("=" * 60)
        
        # 顯示回測摘要
        print(result.summary())
        
        # 詳細統計
        print("\n📊 詳細統計:")
        metrics = result.metrics
        portfolio = result.portfolio
        
        print(f"初始資金: ${portfolio.initial_capital:,.2f}")
        print(f"最終資產: ${portfolio.get_total_value():,.2f}")
        print(f"淨利潤: ${portfolio.get_total_value() - portfolio.initial_capital:,.2f}")
        print(f"總手續費: ${metrics.get('total_commission', 0):.2f}")
        
        # 交易統計
        trades_df = result.trades
        if not trades_df.empty:
            print(f"\n💼 交易統計:")
            print(f"總交易筆數: {len(trades_df)}")
            
            # 顯示最近幾筆交易
            print(f"\n最近 5 筆交易:")
            for _, trade in trades_df.tail(5).iterrows():
                timestamp = pd.to_datetime(trade['timestamp'], unit='ms')
                side_emoji = "📈" if trade['side'] == 'BUY' else "📉"
                print(f"  {side_emoji} {timestamp.strftime('%Y-%m-%d %H:%M')} | "
                      f"{trade['side']} {trade['quantity']:.6f} @ ${trade['price']:,.2f}")
        else:
            print("\n💼 交易統計: 無交易記錄")
        
        # 資產曲線
        equity_df = result.equity_curve
        if not equity_df.empty:
            print(f"\n📈 資產曲線統計:")
            print(f"最高淨值: ${equity_df['total_value'].max():,.2f}")
            print(f"最低淨值: ${equity_df['total_value'].min():,.2f}")
            print(f"淨值波動: {((equity_df['total_value'].max() - equity_df['total_value'].min()) / portfolio.initial_capital):.2%}")
        
        # 策略特定統計
        print(f"\n🎯 策略統計:")
        print(f"策略名稱: {strategy.name}")
        print(f"參數設置: {strategy.get_parameters()}")
        print(f"數據緩存: {len(strategy.data_buffer)} 條記錄")
        
        print("\n" + "=" * 60)
        print("🎉 測試完成！")
        print("\n💡 這個測試演示了:")
        print("   • 如何生成模擬市場數據")
        print("   • 如何創建簡單的交易策略")
        print("   • 如何設置回測引擎和風險管理")
        print("   • 如何分析回測結果")
        print("\n🔗 接下來您可以:")
        print("   • 修改策略參數進行實驗")
        print("   • 添加更多的過濾器和風險控制")
        print("   • 使用真實的市場數據進行回測")
        
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        print("\n🔧 調試提示:")
        print("   • 確保所有依賴模塊都已正確導入")
        print("   • 檢查數據格式是否符合預期")
        print("   • 查看日誌輸出獲取更多信息")


if __name__ == "__main__":
    main()