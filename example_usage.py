#!/usr/bin/env python3
"""
交易系統使用示例

這個示例展示了如何使用交易系統的各個組件：
1. 創建一個簡單的動量策略
2. 設置回測引擎
3. 添加風險管理和過濾器
4. 運行回測並查看結果
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)

# 導入交易系統組件
from src import (
    BaseStrategy, Signal, SignalType,
    BacktestEngine, RiskManager,
    FilterManager, CommonFilters,
    config
)


class SimpleMovingAverageStrategy(BaseStrategy):
    """簡單移動平均策略示例"""
    
    def __init__(self, name="SMA_Strategy", short_window=10, long_window=20):
        super().__init__(name, {
            'short_window': short_window,
            'long_window': long_window
        })
        self.short_window = short_window
        self.long_window = long_window
    
    def warmup_period(self) -> int:
        """返回需要的暖身期長度"""
        return max(self.short_window, self.long_window)
    
    def on_bar(self, bar: pd.Series) -> Signal:
        """處理新的K線數據"""
        # 更新數據緩存
        self.update_buffer(bar)
        
        # 檢查是否有足夠的數據
        if not self.is_ready():
            return None
        
        # 獲取最近的收盤價
        recent_data = self.get_buffer_dataframe()
        if len(recent_data) < self.long_window:
            return None
        
        prices = recent_data['close']
        
        # 計算移動平均線
        short_ma = prices.rolling(window=self.short_window).mean().iloc[-1]
        long_ma = prices.rolling(window=self.long_window).mean().iloc[-1]
        prev_short_ma = prices.rolling(window=self.short_window).mean().iloc[-2]
        prev_long_ma = prices.rolling(window=self.long_window).mean().iloc[-2]
        
        current_price = bar['close']
        
        # 生成交易信號
        # 金叉：短期均線上穿長期均線，買入信號
        if (short_ma > long_ma and prev_short_ma <= prev_long_ma):
            return Signal(
                symbol="BTCUSDT",  # 這裡會被回測引擎設置
                signal_type=SignalType.BUY,
                price=current_price,
                confidence=0.8,
                metadata={
                    'short_ma': short_ma,
                    'long_ma': long_ma,
                    'strategy': 'golden_cross'
                }
            )
        
        # 死叉：短期均線下穿長期均線，賣出信號
        elif (short_ma < long_ma and prev_short_ma >= prev_long_ma):
            return Signal(
                symbol="BTCUSDT",
                signal_type=SignalType.SELL,
                price=current_price,
                confidence=0.8,
                metadata={
                    'short_ma': short_ma,
                    'long_ma': long_ma,
                    'strategy': 'death_cross'
                }
            )
        
        return None


def generate_sample_data(days=365) -> pd.DataFrame:
    """生成示例市場數據"""
    # 生成模擬的BTCUSDT價格數據
    np.random.seed(42)  # 確保可重複性
    
    # 創建時間索引
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    date_range = pd.date_range(start=start_date, end=end_date, freq='1H')
    
    # 生成價格數據（幾何布朗運動）
    initial_price = 30000  # 初始BTC價格
    volatility = 0.02
    drift = 0.0001
    
    returns = np.random.normal(drift, volatility, len(date_range))
    price_series = [initial_price]
    
    for ret in returns[1:]:
        new_price = price_series[-1] * (1 + ret)
        price_series.append(new_price)
    
    # 創建OHLCV數據
    data = []
    for i, (timestamp, price) in enumerate(zip(date_range, price_series)):
        # 生成開高低收數據
        noise = np.random.normal(0, price * 0.001)  # 小幅波動
        open_price = price + noise
        high_price = max(open_price, price) + abs(np.random.normal(0, price * 0.002))
        low_price = min(open_price, price) - abs(np.random.normal(0, price * 0.002))
        close_price = price
        volume = np.random.uniform(100, 1000)  # 隨機成交量
        
        data.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data, index=date_range)
    return df


def main():
    """主函數 - 運行回測示例"""
    
    print("=== 交易系統回測示例 ===\n")
    
    # 1. 生成示例數據
    print("1. 生成示例市場數據...")
    market_data = generate_sample_data(days=180)  # 6個月數據
    print(f"   數據期間: {market_data.index[0]} 至 {market_data.index[-1]}")
    print(f"   數據長度: {len(market_data)} 條記錄")
    print(f"   價格範圍: ${market_data['close'].min():.2f} - ${market_data['close'].max():.2f}\n")
    
    # 2. 創建策略
    print("2. 創建移動平均策略...")
    strategy = SimpleMovingAverageStrategy(
        name="SMA_10_20",
        short_window=10,
        long_window=20
    )
    print(f"   策略: {strategy.name}")
    print(f"   參數: {strategy.get_parameters()}\n")
    
    # 3. 設置回測引擎
    print("3. 設置回測引擎...")
    engine = BacktestEngine(
        initial_capital=100000,  # 10萬美元
        commission=0.001  # 0.1% 手續費
    )
    engine.add_strategy(strategy)
    print(f"   初始資金: ${engine.portfolio.initial_capital:,.2f}")
    print(f"   手續費率: {engine.commission:.1%}\n")
    
    # 4. 添加風險管理
    print("4. 添加風險管理...")
    risk_manager = RiskManager(
        max_position_size=0.3,    # 單一持倉最大30%
        max_daily_loss=0.05,      # 日損失限制5%
        max_drawdown=0.15,        # 最大回撤15%
        max_positions=3           # 最多3個持倉
    )
    engine.set_risk_manager(risk_manager)
    print("   風險管理規則已設置\n")
    
    # 5. 添加過濾器
    print("5. 添加信號過濾器...")
    filter_manager = FilterManager()
    
    # 添加成交量過濾器
    filter_manager.add_global_filter(
        CommonFilters.volume_filter(min_volume=200),
        name="volume_filter"
    )
    
    # 添加持倉限制過濾器
    filter_manager.add_global_filter(
        CommonFilters.position_limit_filter(max_positions=2),
        name="position_limit"
    )
    
    # 添加現金保留過濾器
    filter_manager.add_global_filter(
        CommonFilters.cash_filter(min_cash_ratio=0.1),
        name="cash_reserve"
    )
    
    engine.set_filter_manager(filter_manager)
    print("   過濾器已設置\n")
    
    # 6. 運行回測
    print("6. 運行回測...")
    print("   處理中...")
    
    result = engine.run(market_data, symbol="BTCUSDT")
    
    print("   回測完成!\n")
    
    # 7. 展示結果
    print("=== 回測結果 ===")
    print(result.summary())
    
    # 詳細統計
    print("\n=== 詳細統計 ===")
    metrics = result.metrics
    print(f"最終資產價值: ${result.portfolio.get_total_value():,.2f}")
    print(f"總交易次數: {len(result.trades)}")
    print(f"總手續費: ${metrics.get('total_commission', 0):.2f}")
    
    if len(result.trades) > 0:
        print(f"平均每筆交易: ${(result.trades['pnl'].sum() / len(result.trades)):.2f}")
        print(f"最大單筆盈利: ${result.trades['pnl'].max():.2f}")
        print(f"最大單筆虧損: ${result.trades['pnl'].min():.2f}")
    
    # 風險指標
    print(f"\n=== 風險指標 ===")
    risk_metrics = risk_manager.get_risk_metrics(result.portfolio)
    for key, value in risk_metrics.items():
        if isinstance(value, float):
            if 'ratio' in key or 'rate' in key or 'drawdown' in key:
                print(f"{key}: {value:.2%}")
            else:
                print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")
    
    # 過濾器統計
    print(f"\n=== 過濾器統計 ===")
    filter_stats = filter_manager.get_filter_stats()
    for key, value in filter_stats.items():
        if key == 'filter_reasons':
            if value:
                print("過濾原因:")
                for reason, count in value.items():
                    print(f"  {reason}: {count}")
        elif isinstance(value, float):
            if 'rate' in key:
                print(f"{key}: {value:.2%}")
            else:
                print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")
    
    print(f"\n=== 回測完成 ===")
    print("提示: 這是一個使用模擬數據的示例回測")
    print("實際使用時請替換為真實的市場數據")


if __name__ == "__main__":
    main()