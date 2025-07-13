#!/usr/bin/env python3
"""
Sage MCP 配置适配器
统一配置接口，兼容新旧配置系统，确保向后兼容性
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger('SageConfigAdapter')


class ConfigAdapter:
    """统一配置接口，桥接claude_mem_v3的简单配置和config_manager的版本化配置"""
    
    def __init__(self, use_config_manager=True):
        self._use_config_manager = use_config_manager  # 允许禁用config_manager
        self._config_manager = None
        self._legacy_config = None
        self._legacy_config_file = Path.home() / '.sage-mcp' / 'config.json'
        self._migration_completed = False
        
    @property
    def config_manager(self):
        """延迟加载config_manager，避免循环依赖"""
        if not self._use_config_manager:
            return None
            
        if self._config_manager is None:
            try:
                from config_manager import get_config_manager
                self._config_manager = get_config_manager()
            except ImportError:
                logger.warning("config_manager 不可用，使用旧配置系统")
        return self._config_manager
    
    def _load_legacy_config(self) -> Dict[str, Any]:
        """加载旧的简单JSON配置"""
        default_config = {
            'claude_paths': [],
            'memory_enabled': True,
            'debug_mode': False,
            'show_memory_hints': True,
            'memory_hint_color': 'cyan',
            'retrieval_count': 3,
            'similarity_threshold': 0.7,
            'time_decay': True,
            'max_age_days': 30,
            'async_save': True
        }
        
        if self._legacy_config_file.exists():
            try:
                with open(self._legacy_config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"旧配置文件读取失败: {e}")
                
        self._legacy_config = default_config
        return self._legacy_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，优先从新系统获取，失败则降级到旧系统
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        # 尝试从新配置系统获取
        if self.config_manager:
            try:
                # 尝试不同的键格式
                for key_format in [key, f"memory.{key}", f"sage.{key}"]:
                    value = self._get_from_config_manager(key_format)
                    if value is not None:
                        return value
            except Exception as e:
                logger.debug(f"从config_manager获取配置失败: {e}")
        
        # 降级到旧配置系统
        if self._legacy_config is None:
            self._load_legacy_config()
        
        return self._legacy_config.get(key, default)
    
    def _get_from_config_manager(self, key: str) -> Any:
        """从config_manager获取配置值"""
        try:
            # 处理嵌套键
            parts = key.split('.')
            config = self.config_manager.config
            
            for part in parts:
                if hasattr(config, part):
                    config = getattr(config, part)
                elif isinstance(config, dict) and part in config:
                    config = config[part]
                else:
                    return None
                    
            return config
        except:
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值，同时更新新旧系统
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            是否成功
        """
        success = True
        
        # 更新新配置系统
        if self.config_manager:
            try:
                # 尝试直接设置属性（跳过不支持的嵌套键）
                if hasattr(self.config_manager.config, key):
                    setattr(self.config_manager.config, key, value)
                    self.config_manager.save_config()
                else:
                    # 如果是memory相关的键，暂时只保存到旧系统
                    logger.debug(f"键 {key} 不在新配置系统中，仅保存到旧系统")
            except Exception as e:
                logger.warning(f"更新config_manager失败: {e}")
        
        # 更新旧配置系统（作为主要存储）
        if self._legacy_config is None:
            self._load_legacy_config()
        
        self._legacy_config[key] = value
        
        # 保存旧配置
        try:
            self._legacy_config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._legacy_config_file, 'w', encoding='utf-8') as f:
                json.dump(self._legacy_config, f, indent=2, ensure_ascii=False)
            return True  # 只要旧配置保存成功就返回True
        except Exception as e:
            logger.error(f"保存旧配置失败: {e}")
            return False
    
    def migrate_legacy_config(self, backup: bool = True) -> bool:
        """
        将旧配置迁移到新系统
        
        Args:
            backup: 是否备份旧配置
            
        Returns:
            是否成功
        """
        if self._migration_completed:
            return True
        
        if not self.config_manager:
            logger.warning("config_manager 不可用，无法迁移配置")
            return False
        
        if not self._legacy_config_file.exists():
            self._migration_completed = True
            return True
        
        try:
            # 备份旧配置
            if backup:
                backup_file = self._legacy_config_file.with_suffix('.json.backup')
                backup_file.write_text(self._legacy_config_file.read_text())
                logger.info(f"旧配置已备份到: {backup_file}")
            
            # 加载旧配置
            if self._legacy_config is None:
                self._load_legacy_config()
            
            # 迁移到新系统
            from config_manager import set_config
            
            migration_map = {
                'memory_enabled': 'memory.enabled',
                'retrieval_count': 'memory.retrieval_count',
                'similarity_threshold': 'memory.similarity_threshold',
                'time_decay': 'memory.time_decay',
                'max_age_days': 'memory.max_age_days',
                'async_save': 'memory.async_save',
                'show_memory_hints': 'ui.show_memory_hints',
                'memory_hint_color': 'ui.memory_hint_color',
                'debug_mode': 'debug.enabled',
                'claude_paths': 'claude.paths'
            }
            
            for old_key, new_key in migration_map.items():
                if old_key in self._legacy_config:
                    set_config(new_key, self._legacy_config[old_key])
            
            # 保存新配置
            self.config_manager.save_config()
            
            # 标记迁移完成
            self._migration_completed = True
            logger.info("配置迁移成功完成")
            
            return True
            
        except Exception as e:
            logger.error(f"配置迁移失败: {e}")
            return False
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置（用于调试）"""
        config = {}
        
        # 从新系统获取
        if self.config_manager:
            try:
                from dataclasses import asdict
                config['config_manager'] = asdict(self.config_manager.config)
            except:
                pass
        
        # 从旧系统获取
        if self._legacy_config is None:
            self._load_legacy_config()
        config['legacy'] = self._legacy_config.copy()
        
        return config


# 全局实例
_adapter_instance = None


def get_config_adapter() -> ConfigAdapter:
    """获取配置适配器单例"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = ConfigAdapter()
        # 尝试自动迁移配置
        _adapter_instance.migrate_legacy_config()
    return _adapter_instance


def get_config(key: str, default: Any = None) -> Any:
    """便捷方法：获取配置值"""
    return get_config_adapter().get(key, default)


def set_config(key: str, value: Any) -> bool:
    """便捷方法：设置配置值"""
    return get_config_adapter().set(key, value)