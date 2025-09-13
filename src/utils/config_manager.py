"""配置管理器"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        load_dotenv()  # 加載 .env 文件
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._apply_env_overrides()
    
    def _load_config(self) -> Dict[str, Any]:
        """加載配置文件"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _apply_env_overrides(self) -> None:
        """應用環境變量覆蓋"""
        # Bybit API 配置
        if 'bybit' not in self.config:
            self.config['bybit'] = {}
            
        self.config['bybit']['api_key'] = os.getenv('BYBIT_API_KEY', 
                                                   self.config['bybit'].get('api_key', ''))
        self.config['bybit']['api_secret'] = os.getenv('BYBIT_API_SECRET', 
                                                       self.config['bybit'].get('api_secret', ''))
        
        # 其他環境變量
        if os.getenv('DEBUG') == 'true':
            if 'logging' not in self.config:
                self.config['logging'] = {}
            self.config['logging']['level'] = 'DEBUG'
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        獲取配置值
        
        Args:
            key: 配置鍵，支持點分隔（如 'bybit.api_key'）
            default: 默認值
            
        Returns:
            配置值或默認值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        設置配置值
        
        Args:
            key: 配置鍵，支持點分隔
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
    
    def save(self) -> None:
        """保存配置到文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
    
    def get_bybit_config(self) -> Dict[str, Any]:
        """獲取 Bybit 配置"""
        return self.get('bybit', {})
    
    def get_backtest_config(self) -> Dict[str, Any]:
        """獲取回測配置"""
        return self.get('backtest', {})
    
    def get_risk_config(self) -> Dict[str, Any]:
        """獲取風險管理配置"""
        return self.get('risk_management', {})
    
    def get_data_config(self) -> Dict[str, Any]:
        """獲取數據配置"""
        return self.get('data', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """獲取日誌配置"""
        return self.get('logging', {})