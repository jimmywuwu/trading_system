# 交易系統 (Trading System)

一個模塊化、事件驅動的交易系統，支持策略回測和實盤交易。

## 主要特性

- **統一介面**: 回測和實盤使用相同的API
- **事件驅動**: 模擬真實市場的事件流
- **模塊化設計**: 各組件可獨立開發和測試
- **多層次風險管理**: 內建風險控制機制
- **靈活的過濾器系統**: 多層次信號過濾
- **可擴展**: 易於添加新交易所和策略

## 系統架構

```
src/
├── data/           # 數據層 - 市場數據提供者和數據管理
├── strategy/       # 策略層 - 交易策略和信號定義
├── backtest/       # 回測層 - 回測引擎和投資組合管理
├── execution/      # 執行層 - 訂單管理和執行
├── risk/          # 風險管理 - 風險控制和監控
├── exchange/      # 交易所連接器 - API接口實現
├── config/        # 配置管理 - 系統配置和參數
└── filters/       # 過濾器系統 - 信號過濾和篩選
```

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 運行示例

```bash
python example_usage.py
```

### 3. 基本使用

```python
from src import BaseStrategy, BacktestEngine, Signal, SignalType

# 創建策略
class MyStrategy(BaseStrategy):
    def on_bar(self, bar):
        # 策略邏輯
        if some_condition:
            return Signal(
                symbol="BTCUSDT",
                signal_type=SignalType.BUY,
                price=bar['close']
            )
        return None

# 設置回測
strategy = MyStrategy("MyStrategy")
engine = BacktestEngine(initial_capital=100000)
engine.add_strategy(strategy)

# 運行回測
result = engine.run(market_data)
print(result.summary())
```

## 核心組件

### 1. 數據層 (Data Layer)

- **MarketDataProvider**: 市場數據提供者抽象基類
- **DataManager**: 數據緩存和管理
- **BybitConnector**: Bybit交易所連接器

### 2. 策略層 (Strategy Layer)

- **BaseStrategy**: 策略基類
- **EnhancedBaseStrategy**: 支持內建過濾器的增強策略基類
- **Signal**: 交易信號數據結構

### 3. 回測引擎 (Backtest Engine)

- **BacktestEngine**: 主要回測引擎
- **Portfolio**: 投資組合管理
- **BacktestResult**: 回測結果和分析

### 4. 執行層 (Execution Layer)

- **OrderManager**: 訂單管理器
- **Order**: 訂單數據結構

### 5. 風險管理 (Risk Management)

- **RiskManager**: 多層次風險控制
  - 單一持倉大小限制
  - 日損失限制
  - 最大回撤控制
  - 槓桿限制

### 6. 過濾器系統 (Filter System)

- **FilterManager**: 過濾器管理器
- **CommonFilters**: 常用過濾器集合
  - 成交量過濾器
  - 時間過濾器
  - 價格範圍過濾器
  - 持倉限制過濾器

## 配置管理

系統使用YAML格式的配置文件，支持：

- 交易參數配置
- 風險管理參數
- 交易所API設置
- 回測參數設置

```yaml
trading:
  initial_capital: 100000
  commission: 0.001
  slippage: 0.0001

risk_management:
  max_position_size: 0.1
  max_daily_loss: 0.02
  max_drawdown: 0.1

exchange:
  name: bybit
  testnet: true
  api_key: "your_api_key"
  api_secret: "your_api_secret"
```

## 擴展開發

### 添加新策略

1. 繼承 `BaseStrategy` 或 `EnhancedBaseStrategy`
2. 實現 `on_bar()` 方法
3. 定義 `warmup_period()` 如需要暖身期

### 添加新交易所

1. 繼承 `MarketDataProvider`
2. 實現所有抽象方法
3. 添加特定的交易功能

### 添加新過濾器

```python
def custom_filter(signal, market_data, portfolio):
    # 自定義過濾邏輯
    return True  # 返回 True 表示通過過濾

# 添加到過濾器管理器
filter_manager.add_global_filter(custom_filter)
```

## 注意事項

1. **風險警告**: 這是一個開發框架，實盤交易有風險，請謹慎使用
2. **測試環境**: 建議先在測試網環境充分測試
3. **數據質量**: 確保使用高質量的歷史數據進行回測
4. **參數調優**: 避免過度擬合，注意樣本外驗證

## 許可證

本項目僅供學習和研究使用。

## 貢獻

歡迎提交 Issue 和 Pull Request！