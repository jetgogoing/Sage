#!/usr/bin/env python3
"""
配置管理模块
用于管理 Sage Hooks 的配置参数和环境变量

功能：
1. 配置文件的读取和写入
2. 环境变量的管理
3. 默认配置的提供
4. 配置验证和校正
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

try:
    from security_utils import path_validator, SecurityError
except ImportError:
    # 如果 security_utils 不可用，创建一个简单的占位符
    class SecurityError(Exception):
        pass
    
    class _DummyPathValidator:
        def validate_path(self, path, must_exist=False):
            return Path(path)
    
    path_validator = _DummyPathValidator()


class ConfigManager:
    """Sage Hooks 配置管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "sage_mcp": {
            "server_url": "localhost:3000",
            "timeout": 30,
            "retry_count": 3,
            "retry_delay": 1.0
        },
        "enhancer": {
            "enabled": True,
            "timeout": 45,
            "max_context_turns": 3,
            "cache_enabled": True,
            "cache_ttl": 300
        },
        "archiver": {
            "enabled": True,
            "timeout": 30,
            "backup_enabled": True,
            "backup_retention_days": 30
        },
        "logging": {
            "level": "INFO",
            "file_enabled": True,
            "console_enabled": True,
            "max_file_size": "10MB",
            "backup_count": 5
        },
        "security": {
            "sanitize_logs": True,
            "encrypt_backups": False,
            "max_prompt_length": 10000,
            "max_response_length": 50000
        }
    }
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为 os.getenv('SAGE_HOME', '.')/hooks/configs
        """
        try:
            # 使用安全验证器验证配置目录路径
            config_dir_str = config_dir or os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "configs")
            self.config_dir = path_validator.validate_path(config_dir_str)
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except (SecurityError, AttributeError):
            # 如果验证失败或 security_utils 不可用，使用默认路径
            self.config_dir = Path(config_dir or os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "configs"))
            self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.config_dir / "sage_hooks.json"
        self.env_file = self.config_dir / ".env"
        
        self._config = {}
        self._load_config()
        
        self.logger = logging.getLogger("config_manager")
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                
                # 合并默认配置和文件配置
                self._config = self._deep_merge(self.DEFAULT_CONFIG.copy(), file_config)
            else:
                # 使用默认配置并创建配置文件
                self._config = self.DEFAULT_CONFIG.copy()
                self._save_config()
            
            # 加载环境变量覆盖
            self._load_env_overrides()
            
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self._config = self.DEFAULT_CONFIG.copy()
    
    def _load_env_overrides(self) -> None:
        """加载环境变量覆盖配置"""
        env_mappings = {
            'SAGE_MCP_SERVER_URL': ('sage_mcp', 'server_url'),
            'SAGE_MCP_TIMEOUT': ('sage_mcp', 'timeout'),
            'SAGE_ENHANCER_ENABLED': ('enhancer', 'enabled'),
            'SAGE_ENHANCER_TIMEOUT': ('enhancer', 'timeout'),
            'SAGE_ARCHIVER_ENABLED': ('archiver', 'enabled'),
            'SAGE_ARCHIVER_TIMEOUT': ('archiver', 'timeout'),
            'SAGE_LOG_LEVEL': ('logging', 'level'),
            'SAGE_BACKUP_ENABLED': ('archiver', 'backup_enabled'),
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # 类型转换
                if key in ['timeout', 'retry_count', 'max_context_turns', 'cache_ttl', 'backup_retention_days']:
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                elif key in ['retry_delay']:
                    try:
                        value = float(value)
                    except ValueError:
                        continue
                elif key in ['enabled', 'cache_enabled', 'backup_enabled', 'file_enabled', 'console_enabled', 'sanitize_logs', 'encrypt_backups']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                
                if section not in self._config:
                    self._config[section] = {}
                self._config[section][key] = value
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def _save_config(self) -> None:
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            section: 配置节名
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            return self._config.get(section, {}).get(key, default)
        except Exception:
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取整个配置节
        
        Args:
            section: 配置节名
            
        Returns:
            配置节字典
        """
        return self._config.get(section, {}).copy()
    
    def set(self, section: str, key: str, value: Any, save: bool = True) -> None:
        """
        设置配置值
        
        Args:
            section: 配置节名
            key: 配置键名
            value: 配置值
            save: 是否立即保存到文件
        """
        if section not in self._config:
            self._config[section] = {}
        
        self._config[section][key] = value
        
        if save:
            self._save_config()
    
    def update_section(self, section: str, values: Dict[str, Any], save: bool = True) -> None:
        """
        更新整个配置节
        
        Args:
            section: 配置节名
            values: 新的配置值字典
            save: 是否立即保存到文件
        """
        if section not in self._config:
            self._config[section] = {}
        
        self._config[section].update(values)
        
        if save:
            self._save_config()
    
    def validate_config(self) -> bool:
        """
        验证配置的有效性
        
        Returns:
            配置是否有效
        """
        try:
            # 检查必要的配置节
            required_sections = ['sage_mcp', 'enhancer', 'archiver', 'logging']
            for section in required_sections:
                if section not in self._config:
                    self.logger.error(f"Missing required config section: {section}")
                    return False
            
            # 检查超时值的合理性
            sage_timeout = self.get('sage_mcp', 'timeout', 30)
            enhancer_timeout = self.get('enhancer', 'timeout', 45)
            archiver_timeout = self.get('archiver', 'timeout', 30)
            
            if not (1 <= sage_timeout <= 60):
                self.logger.error(f"Invalid sage_mcp timeout: {sage_timeout}")
                return False
            
            if not (1 <= enhancer_timeout <= 60):
                self.logger.error(f"Invalid enhancer timeout: {enhancer_timeout}")
                return False
            
            if not (1 <= archiver_timeout <= 60):
                self.logger.error(f"Invalid archiver timeout: {archiver_timeout}")
                return False
            
            # 检查日志级别
            log_level = self.get('logging', 'level', 'INFO')
            if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                self.logger.error(f"Invalid log level: {log_level}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating config: {e}")
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            完整的配置字典
        """
        return self._config.copy()
    
    def reset_to_defaults(self, save: bool = True) -> None:
        """
        重置为默认配置
        
        Args:
            save: 是否立即保存到文件
        """
        self._config = self.DEFAULT_CONFIG.copy()
        if save:
            self._save_config()
    
    def export_config(self, file_path: Union[str, Path]) -> bool:
        """
        导出配置到指定文件
        
        Args:
            file_path: 目标文件路径
            
        Returns:
            是否成功导出
        """
        try:
            # 验证输出文件路径
            try:
                validated_path = path_validator.validate_path(str(file_path))
                export_path = str(validated_path)
            except (SecurityError, AttributeError):
                export_path = str(file_path)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Error exporting config to {file_path}: {e}")
            return False
    
    def import_config(self, file_path: Union[str, Path], save: bool = True) -> bool:
        """
        从指定文件导入配置
        
        Args:
            file_path: 源文件路径
            save: 是否立即保存到主配置文件
            
        Returns:
            是否成功导入
        """
        try:
            # 验证输入文件路径
            try:
                validated_path = path_validator.validate_path(str(file_path), must_exist=True)
                import_path = str(validated_path)
            except (SecurityError, AttributeError):
                import_path = str(file_path)
            
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 验证导入的配置
            temp_config = self._config
            self._config = self._deep_merge(self.DEFAULT_CONFIG.copy(), imported_config)
            
            if not self.validate_config():
                self._config = temp_config
                self.logger.error("Imported config is invalid, reverting changes")
                return False
            
            if save:
                self._save_config()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error importing config from {file_path}: {e}")
            return False


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config(section: str, key: str, default: Any = None) -> Any:
    """获取配置值的便捷函数"""
    return config_manager.get(section, key, default)


def get_section(section: str) -> Dict[str, Any]:
    """获取配置节的便捷函数"""
    return config_manager.get_section(section)


if __name__ == "__main__":
    # 测试配置管理器
    cm = ConfigManager()
    
    print("=== 配置管理器测试 ===")
    print(f"Sage MCP 服务器 URL: {cm.get('sage_mcp', 'server_url')}")
    print(f"增强器启用状态: {cm.get('enhancer', 'enabled')}")
    print(f"日志级别: {cm.get('logging', 'level')}")
    
    print(f"\n配置验证结果: {cm.validate_config()}")
    
    # 导出配置示例
    export_path = Path("/tmp/sage_hooks_config_export.json")
    if cm.export_config(export_path):
        print(f"配置已导出到: {export_path}")
    
    print("=== 测试完成 ===")