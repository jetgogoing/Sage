#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Manager - 统一配置管理
从 config_manager.py 提取并优化
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        # 优先级：环境变量 > 用户目录 > 项目目录
        if env_path := os.getenv('SAGE_CONFIG_PATH'):
            return env_path
        
        home_config = Path.home() / '.sage' / 'config.json'
        if home_config.exists():
            return str(home_config)
        
        project_config = Path(__file__).parent.parent.parent / 'config.json'
        return str(project_config)
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"配置已加载：{self.config_path}")
            else:
                logger.warning(f"配置文件不存在：{self.config_path}")
                self._create_default_config()
        except Exception as e:
            logger.error(f"加载配置失败：{e}")
            self._create_default_config()
    
    def _create_default_config(self) -> None:
        """创建默认配置"""
        self.config = {
            "database": {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", "5432")),
                "database": os.getenv("DB_NAME", "sage_memory"),
                "user": os.getenv("DB_USER", "sage"),
                "password": os.getenv("DB_PASSWORD", "sage123")
            },
            "embedding": {
                "model": os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
                "dimension": 4096,
                "device": "cuda" if os.getenv("USE_CUDA", "false").lower() == "true" else "cpu"
            },
            "memory": {
                "default_limit": 10,
                "max_limit": 100,
                "similarity_threshold": 0.7
            },
            "server": {
                "host": "0.0.0.0",
                "port": 17800,
                "log_level": "INFO"
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 默认值
            
        Returns:
            配置值
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
        """设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
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
        try:
            config_path = Path(self.config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已保存：{self.config_path}")
        except Exception as e:
            logger.error(f"保存配置失败：{e}")
    
    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self.get('database', {})
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """获取嵌入模型配置"""
        return self.get('embedding', {})
    
    def get_memory_config(self) -> Dict[str, Any]:
        """获取记忆系统配置"""
        return self.get('memory', {})