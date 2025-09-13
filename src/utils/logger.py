"""日誌系統設置"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any


def setup_logger(
    name: str = "trading_system",
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    設置日誌系統
    
    Args:
        name: 日誌器名稱
        level: 日誌級別
        log_file: 日誌文件路径
        log_format: 日誌格式
        
    Returns:
        配置好的日誌器
    """
    logger = logging.getLogger(name)
    
    # 避免重複添加處理器
    if logger.handlers:
        return logger
        
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 默認格式
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    formatter = logging.Formatter(log_format)
    
    # 控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件處理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用 RotatingFileHandler 避免日誌文件過大
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "trading_system") -> logging.Logger:
    """獲取日誌器"""
    return logging.getLogger(name)