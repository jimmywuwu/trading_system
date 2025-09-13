import yaml
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging
from datetime import datetime


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        # 支持的配置文件格式
        self.supported_formats = {'.yaml', '.yml', '.json'}
        
        # 配置變更歷史
        self.config_history: list = []
        
        # 加載配置
        self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加載配置文件"""
        try:
            if not self.config_path.exists():
                self.logger.warning(f"配置文件不存在: {self.config_path}")
                self._create_default_config()
                return self.config
            
            # 根據文件擴展名選擇解析方法
            file_extension = self.config_path.suffix.lower()
            
            if file_extension in {'.yaml', '.yml'}:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
            elif file_extension == '.json':
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {file_extension}")
            
            self.logger.info(f"配置文件已加載: {self.config_path}")
            return self.config
            
        except Exception as e:
            self.logger.error(f"加載配置文件失敗: {e}")
            self.config = {}
            return self.config
    
    def _create_default_config(self) -> None:
        """創建默認配置"""
        default_config = {
            'system': {
                'name': 'TradingSystem',
                'version': '1.0.0',
                'debug': False,
                'log_level': 'INFO'
            },
            'trading': {
                'default_symbol': 'BTCUSDT',
                'default_interval': '1h',
                'initial_capital': 100000,
                'commission': 0.001,
                'slippage': 0.0001
            },
            'risk_management': {
                'max_position_size': 0.1,
                'max_daily_loss': 0.02,
                'max_drawdown': 0.1,
                'max_positions': 10,
                'leverage_limit': 1.0
            },
            'exchange': {
                'name': 'bybit',
                'testnet': True,
                'api_key': '',
                'api_secret': '',
                'rate_limit': 10
            },
            'data': {
                'cache_dir': './data',
                'update_interval': 60,
                'history_days': 365
            },
            'backtest': {
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'benchmark': 'BTCUSDT'
            }
        }
        
        self.config = default_config
        self.save()
        self.logger.info("已創建默認配置文件")
    
    def get(self, key: str, default: Any = None) -> Any:
        """獲取配置值
        
        Args:
            key: 配置鍵，支持點分割的嵌套鍵如 'trading.commission'
            default: 默認值
            
        Returns:
            配置值或默認值
        """
        try:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
                    
            return value
            
        except Exception as e:
            self.logger.error(f"獲取配置值失敗 {key}: {e}")
            return default
    
    def set(self, key: str, value: Any) -> None:
        """設置配置值
        
        Args:
            key: 配置鍵，支持點分割的嵌套鍵
            value: 配置值
        """
        try:
            # 記錄變更歷史
            old_value = self.get(key)
            self.config_history.append({
                'timestamp': datetime.now().isoformat(),
                'key': key,
                'old_value': old_value,
                'new_value': value
            })
            
            keys = key.split('.')
            config = self.config
            
            # 導航到最後一層
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 設置值
            config[keys[-1]] = value
            
            self.logger.info(f"配置已更新: {key} = {value}")
            
        except Exception as e:
            self.logger.error(f"設置配置值失敗 {key}: {e}")
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """批量更新配置
        
        Args:
            config_dict: 配置字典
        """
        try:
            def deep_update(base_dict: Dict, update_dict: Dict) -> Dict:
                """深度更新字典"""
                for key, value in update_dict.items():
                    if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                        deep_update(base_dict[key], value)
                    else:
                        base_dict[key] = value
                return base_dict
            
            # 記錄變更
            self.config_history.append({
                'timestamp': datetime.now().isoformat(),
                'action': 'bulk_update',
                'changes': config_dict
            })
            
            deep_update(self.config, config_dict)
            self.logger.info(f"配置批量更新完成: {len(config_dict)} 個項目")
            
        except Exception as e:
            self.logger.error(f"批量更新配置失敗: {e}")
    
    def delete(self, key: str) -> bool:
        """刪除配置項
        
        Args:
            key: 配置鍵
            
        Returns:
            是否成功刪除
        """
        try:
            old_value = self.get(key)
            if old_value is None:
                return False
            
            # 記錄變更歷史
            self.config_history.append({
                'timestamp': datetime.now().isoformat(),
                'key': key,
                'action': 'delete',
                'old_value': old_value
            })
            
            keys = key.split('.')
            config = self.config
            
            # 導航到父級
            for k in keys[:-1]:
                if k not in config:
                    return False
                config = config[k]
            
            # 刪除鍵
            if keys[-1] in config:
                del config[keys[-1]]
                self.logger.info(f"配置項已刪除: {key}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"刪除配置項失敗 {key}: {e}")
            return False
    
    def save(self, backup: bool = True) -> bool:
        """保存配置到文件
        
        Args:
            backup: 是否創建備份
            
        Returns:
            是否保存成功
        """
        try:
            # 創建父目錄
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 創建備份
            if backup and self.config_path.exists():
                backup_path = self.config_path.with_suffix(
                    f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}{self.config_path.suffix}'
                )
                import shutil
                shutil.copy2(self.config_path, backup_path)
                self.logger.info(f"配置備份已創建: {backup_path}")
            
            # 保存配置
            file_extension = self.config_path.suffix.lower()
            
            if file_extension in {'.yaml', '.yml'}:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self.config, f, default_flow_style=False, 
                             allow_unicode=True, indent=2)
            elif file_extension == '.json':
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"配置已保存: {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置失敗: {e}")
            return False
    
    def reload(self) -> bool:
        """重新加載配置文件
        
        Returns:
            是否重新加載成功
        """
        try:
            old_config = self.config.copy()
            self._load_config()
            
            # 記錄重新加載
            self.config_history.append({
                'timestamp': datetime.now().isoformat(),
                'action': 'reload',
                'old_config': old_config,
                'new_config': self.config
            })
            
            self.logger.info("配置已重新加載")
            return True
            
        except Exception as e:
            self.logger.error(f"重新加載配置失敗: {e}")
            return False
    
    def validate(self) -> tuple[bool, list]:
        """驗證配置
        
        Returns:
            (是否有效, 錯誤列表)
        """
        errors = []
        
        try:
            # 檢查必需的配置項
            required_keys = [
                'trading.initial_capital',
                'trading.commission',
                'risk_management.max_position_size',
                'exchange.name'
            ]
            
            for key in required_keys:
                if self.get(key) is None:
                    errors.append(f"缺少必需配置項: {key}")
            
            # 檢查數值範圍
            if self.get('trading.commission', 0) < 0:
                errors.append("交易手續費不能為負數")
            
            if self.get('trading.initial_capital', 0) <= 0:
                errors.append("初始資金必須大於0")
            
            if not (0 < self.get('risk_management.max_position_size', 0) <= 1):
                errors.append("最大持倉比例必須在0-1之間")
            
            # 檢查交易所配置
            exchange_name = self.get('exchange.name', '').lower()
            if exchange_name not in ['bybit', 'binance']:
                errors.append(f"不支持的交易所: {exchange_name}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"配置驗證異常: {e}")
            return False, errors
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """獲取配置節
        
        Args:
            section: 節名稱
            
        Returns:
            配置節字典
        """
        return self.get(section, {})
    
    def get_trading_config(self) -> Dict[str, Any]:
        """獲取交易配置"""
        return self.get_section('trading')
    
    def get_risk_config(self) -> Dict[str, Any]:
        """獲取風險管理配置"""
        return self.get_section('risk_management')
    
    def get_exchange_config(self) -> Dict[str, Any]:
        """獲取交易所配置"""
        return self.get_section('exchange')
    
    def get_backtest_config(self) -> Dict[str, Any]:
        """獲取回測配置"""
        return self.get_section('backtest')
    
    def export_config(self, export_path: str) -> bool:
        """導出配置到指定路徑
        
        Args:
            export_path: 導出路徑
            
        Returns:
            是否導出成功
        """
        try:
            export_path = Path(export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 添加導出時間戳
            export_config = {
                'exported_at': datetime.now().isoformat(),
                'source_file': str(self.config_path),
                'config': self.config
            }
            
            file_extension = export_path.suffix.lower()
            
            if file_extension in {'.yaml', '.yml'}:
                with open(export_path, 'w', encoding='utf-8') as f:
                    yaml.dump(export_config, f, default_flow_style=False, 
                             allow_unicode=True, indent=2)
            elif file_extension == '.json':
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(export_config, f, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"不支持的導出格式: {file_extension}")
            
            self.logger.info(f"配置已導出: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"導出配置失敗: {e}")
            return False
    
    def get_config_history(self, limit: int = 10) -> list:
        """獲取配置變更歷史
        
        Args:
            limit: 限制返回的記錄數量
            
        Returns:
            配置變更歷史列表
        """
        return self.config_history[-limit:] if self.config_history else []
    
    def clear_history(self) -> None:
        """清除配置變更歷史"""
        self.config_history.clear()
        self.logger.info("配置變更歷史已清除")
    
    def to_dict(self) -> Dict[str, Any]:
        """將配置轉換為字典"""
        return self.config.copy()
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"ConfigManager(path={self.config_path}, keys={len(self.config)})"
    
    def __repr__(self) -> str:
        """詳細字符串表示"""
        return self.__str__()


# 全局配置實例
config = ConfigManager()