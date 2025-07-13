#!/usr/bin/env python3
"""
Sage MCP 统一配置管理系统
支持跨平台配置管理、验证、迁移和备份
"""

import os
import sys
import json
import shutil
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict, field
import logging
from enum import Enum

# 配置版本
CONFIG_VERSION = "2.0"

# 配置键枚举
class ConfigKey(Enum):
    """配置键定义"""
    CLAUDE_PATHS = "claude_paths"
    MEMORY_ENABLED = "memory_enabled"
    DEBUG_MODE = "debug_mode"
    SILENT_MODE = "silent_mode"
    API_KEY = "api_key"
    DB_CONFIG = "db_config"
    PLATFORM = "platform"
    SAGE_HOME = "sage_home"
    VERSION = "version"
    INSTALL_DATE = "install_date"
    LOG_LEVEL = "log_level"
    MAX_CONTEXT_LENGTH = "max_context_length"
    EMBEDDINGS_MODEL = "embeddings_model"
    TEMPERATURE = "temperature"
    # 记忆系统配置
    RETRIEVAL_COUNT = "retrieval_count"
    SIMILARITY_THRESHOLD = "similarity_threshold"
    TIME_DECAY = "time_decay"
    MAX_AGE_DAYS = "max_age_days"
    MAX_CONTEXT_TOKENS = "max_context_tokens"
    ASYNC_SAVE = "async_save"
    CACHE_TTL = "cache_ttl"
    # 用户体验配置
    PROMPT_TEMPLATE = "prompt_template"
    SHOW_MEMORY_HINTS = "show_memory_hints"
    MEMORY_HINT_COLOR = "memory_hint_color"
    VERBOSE_MODE = "verbose_mode"

@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 5432
    database: str = "mem"
    user: str = "mem"
    password: str = "mem"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseConfig':
        """从字典创建实例"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

@dataclass
class SageConfig:
    """Sage MCP 主配置"""
    # 基础配置
    claude_paths: List[str] = field(default_factory=list)
    memory_enabled: bool = True
    debug_mode: bool = False
    silent_mode: bool = False
    
    # API 配置
    api_key: Optional[str] = None
    embeddings_model: str = "Qwen/Qwen3-Embedding-8B"
    temperature: float = 0.7
    
    # 数据库配置
    db_config: DatabaseConfig = field(default_factory=DatabaseConfig)
    
    # 系统配置
    platform: str = field(default_factory=lambda: platform.system().lower())
    sage_home: Optional[str] = None
    version: str = CONFIG_VERSION
    install_date: Optional[str] = None
    
    # 运行时配置
    log_level: str = "INFO"
    max_context_length: int = 4000
    
    # 记忆系统配置
    retrieval_count: int = 3
    similarity_threshold: float = 0.7
    time_decay: bool = True
    max_age_days: int = 30
    max_context_tokens: int = 2000
    async_save: bool = True
    cache_ttl: int = 300
    
    # 提示模板
    prompt_template: str = field(default_factory=lambda: """基于我们之前的对话历史，请回答以下问题。

相关历史对话：
{context}

当前问题：{query}

请结合历史上下文（如果相关）来回答。如果历史信息不相关，可以忽略。""")
    
    # 用户体验
    show_memory_hints: bool = True
    memory_hint_color: str = "cyan"
    verbose_mode: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SageConfig':
        """从字典创建配置"""
        # 处理数据库配置
        if 'db_config' in data and isinstance(data['db_config'], dict):
            data['db_config'] = DatabaseConfig.from_dict(data['db_config'])
        
        # 过滤有效字段
        valid_fields = cls.__annotations__.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 确保数据库配置是字典
        if isinstance(data.get('db_config'), DatabaseConfig):
            data['db_config'] = data['db_config'].to_dict()
        return data

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """初始化配置管理器"""
        # 确定配置目录
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = self._get_default_config_dir()
        
        # 确保目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置文件路径
        self.config_file = self.config_dir / 'config.json'
        self.backup_dir = self.config_dir / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
        # 设置日志
        self._setup_logging()
        
        # 加载或创建配置
        self.config = self.load_config()
    
    def _get_default_config_dir(self) -> Path:
        """获取默认配置目录"""
        # 优先使用环境变量
        if env_dir := os.environ.get('SAGE_CONFIG_DIR'):
            return Path(env_dir)
        
        # 平台特定的默认位置
        home = Path.home()
        
        if platform.system() == 'Windows':
            # Windows: %APPDATA%\sage-mcp
            app_data = os.environ.get('APPDATA', str(home / 'AppData' / 'Roaming'))
            return Path(app_data) / 'sage-mcp'
        elif platform.system() == 'Darwin':
            # macOS: ~/Library/Application Support/sage-mcp
            return home / 'Library' / 'Application Support' / 'sage-mcp'
        else:
            # Linux 和其他: ~/.config/sage-mcp
            xdg_config = os.environ.get('XDG_CONFIG_HOME', str(home / '.config'))
            return Path(xdg_config) / 'sage-mcp'
    
    def _setup_logging(self):
        """设置日志系统"""
        log_dir = self.config_dir / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f'config_{datetime.now().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('ConfigManager')
    
    def load_config(self) -> SageConfig:
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 加载环境变量覆盖
                self._apply_env_overrides(data)
                
                config = SageConfig.from_dict(data)
                self.logger.info(f"配置已加载: {self.config_file}")
                
                # 检查版本并迁移
                if config.version != CONFIG_VERSION:
                    config = self._migrate_config(config)
                
                return config
                
            except Exception as e:
                self.logger.error(f"配置加载失败: {e}")
                self.backup_corrupted_config()
        
        # 创建默认配置
        return self.create_default_config()
    
    def save_config(self, backup: bool = True) -> bool:
        """保存配置"""
        try:
            # 备份当前配置
            if backup and self.config_file.exists():
                self.backup_config()
            
            # 保存新配置
            config_data = self.config.to_dict()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            
            self.logger.info("配置已保存")
            return True
            
        except Exception as e:
            self.logger.error(f"配置保存失败: {e}")
            return False
    
    def create_default_config(self) -> SageConfig:
        """创建默认配置"""
        self.logger.info("创建默认配置")
        
        config_dict = {
            'sage_home': str(Path(__file__).parent),
            'install_date': datetime.now().isoformat()
        }
        
        # 应用环境变量覆盖
        self._apply_env_overrides(config_dict)
        
        config = SageConfig.from_dict(config_dict)
        
        # 尝试自动检测 Claude
        claude_paths = self._auto_detect_claude()
        if claude_paths:
            config.claude_paths = claude_paths
        
        # 从环境变量加载敏感信息（如果还没有）
        if not config.api_key and (api_key := os.environ.get('SILICONFLOW_API_KEY')):
            config.api_key = api_key
        
        # 保存默认配置
        self.config = config
        self.save_config(backup=False)
        
        return config
    
    def _auto_detect_claude(self) -> List[str]:
        """自动检测 Claude 路径"""
        paths = []
        
        if platform.system() == 'Windows':
            search_paths = [
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Claude' / 'claude.exe',
                Path(os.environ.get('PROGRAMFILES', '')) / 'Claude' / 'claude.exe',
            ]
        else:
            search_paths = [
                Path('/usr/local/bin/claude'),
                Path('/usr/bin/claude'),
                Path.home() / '.local' / 'bin' / 'claude',
                Path.home() / '.claude' / 'local' / 'claude',
            ]
        
        for path in search_paths:
            if path.exists() and path.is_file():
                paths.append(str(path))
        
        # 检查 PATH
        import shutil
        if claude_in_path := shutil.which('claude' if platform.system() != 'Windows' else 'claude.exe'):
            if claude_in_path not in paths:
                paths.append(claude_in_path)
        
        return paths
    
    def _apply_env_overrides(self, data: Dict[str, Any]):
        """应用环境变量覆盖"""
        # 环境变量映射
        env_mapping = {
            'SAGE_MEMORY_ENABLED': ('memory_enabled', lambda x: x.lower() == 'true'),
            'SAGE_DEBUG_MODE': ('debug_mode', lambda x: x.lower() == 'true'),
            'SAGE_SILENT_MODE': ('silent_mode', lambda x: x.lower() == 'true'),
            'SILICONFLOW_API_KEY': ('api_key', str),
            'SAGE_LOG_LEVEL': ('log_level', str),
            'SAGE_MAX_CONTEXT': ('max_context_length', int),
            # 记忆系统配置
            'SAGE_RETRIEVAL_COUNT': ('retrieval_count', int),
            'SAGE_SIMILARITY_THRESHOLD': ('similarity_threshold', float),
            'SAGE_TIME_DECAY': ('time_decay', lambda x: x.lower() == 'true'),
            'SAGE_MAX_AGE_DAYS': ('max_age_days', int),
            'SAGE_MAX_CONTEXT_TOKENS': ('max_context_tokens', int),
            'SAGE_ASYNC_SAVE': ('async_save', lambda x: x.lower() == 'true'),
            'SAGE_CACHE_TTL': ('cache_ttl', int),
            # 用户体验配置
            'SAGE_SHOW_MEMORY_HINTS': ('show_memory_hints', lambda x: x.lower() == 'true'),
            'SAGE_MEMORY_HINT_COLOR': ('memory_hint_color', str),
            'SAGE_VERBOSE_MODE': ('verbose_mode', lambda x: x.lower() == 'true'),
        }
        
        # 应用数据库环境变量
        self._apply_database_env_overrides(data)
        
        for env_key, (config_key, converter) in env_mapping.items():
            if env_value := os.environ.get(env_key):
                try:
                    data[config_key] = converter(env_value)
                    self.logger.debug(f"环境变量覆盖: {env_key} -> {config_key}")
                except Exception as e:
                    self.logger.warning(f"环境变量转换失败 {env_key}: {e}")
    
    def _apply_database_env_overrides(self, data: Dict[str, Any]):
        """应用数据库相关的环境变量覆盖"""
        # 确保有 db_config 数据
        if 'db_config' not in data:
            data['db_config'] = {}
        
        # 数据库环境变量映射
        db_env_mapping = {
            'DB_HOST': 'host',
            'DB_PORT': 'port',
            'DB_NAME': 'database',
            'DB_USER': 'user',
            'DB_PASSWORD': 'password',
        }
        
        for env_key, db_key in db_env_mapping.items():
            if env_value := os.environ.get(env_key):
                try:
                    if db_key == 'port':
                        data['db_config'][db_key] = int(env_value)
                    else:
                        data['db_config'][db_key] = env_value
                    self.logger.debug(f"数据库环境变量覆盖: {env_key} -> db_config.{db_key}")
                except Exception as e:
                    self.logger.warning(f"数据库环境变量转换失败 {env_key}: {e}")
    
    def _detect_container_environment(self) -> bool:
        """检测是否在容器环境中运行"""
        container_indicators = [
            os.path.exists('/.dockerenv'),
            os.environ.get('CONTAINER_MODE', '').lower() == 'true',
            os.environ.get('KUBERNETES_SERVICE_HOST') is not None,
            'docker' in (os.environ.get('PATH', '') + os.environ.get('HOME', '')).lower()
        ]
        return any(container_indicators)
    
    def _migrate_config(self, old_config: SageConfig) -> SageConfig:
        """迁移旧版本配置"""
        self.logger.info(f"迁移配置: {old_config.version} -> {CONFIG_VERSION}")
        
        # 备份旧配置
        self.backup_config(suffix='_pre_migration')
        
        # 根据版本进行迁移
        # 这里可以添加具体的迁移逻辑
        new_config = old_config
        new_config.version = CONFIG_VERSION
        
        # 保存迁移后的配置
        self.config = new_config
        self.save_config(backup=False)
        
        return new_config
    
    def backup_config(self, suffix: str = ''):
        """备份配置"""
        if not self.config_file.exists():
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'config_{timestamp}{suffix}.json'
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(self.config_file, backup_path)
        self.logger.info(f"配置已备份: {backup_path}")
        
        # 清理旧备份（保留最近10个）
        self._cleanup_old_backups()
    
    def backup_corrupted_config(self):
        """备份损坏的配置"""
        if not self.config_file.exists():
            return
        
        corrupted_dir = self.backup_dir / 'corrupted'
        corrupted_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = corrupted_dir / f'config_corrupted_{timestamp}.json'
        
        shutil.move(str(self.config_file), str(backup_path))
        self.logger.warning(f"损坏的配置已移动到: {backup_path}")
    
    def _cleanup_old_backups(self, keep_count: int = 10):
        """清理旧备份"""
        backups = sorted(self.backup_dir.glob('config_*.json'), key=lambda p: p.stat().st_mtime)
        
        if len(backups) > keep_count:
            for backup in backups[:-keep_count]:
                backup.unlink()
                self.logger.debug(f"删除旧备份: {backup}")
    
    def get(self, key: Union[str, ConfigKey], default: Any = None) -> Any:
        """获取配置值"""
        if isinstance(key, ConfigKey):
            key = key.value
        
        # 支持嵌套键（如 "db_config.host"）
        if '.' in key:
            parts = key.split('.')
            value = self.config.to_dict()
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            
            return value
        
        # 直接获取
        return getattr(self.config, key, default)
    
    def set(self, key: Union[str, ConfigKey], value: Any) -> bool:
        """设置配置值"""
        if isinstance(key, ConfigKey):
            key = key.value
        
        try:
            # 支持嵌套键
            if '.' in key:
                parts = key.split('.')
                if parts[0] == 'db_config' and len(parts) == 2:
                    setattr(self.config.db_config, parts[1], value)
                else:
                    self.logger.error(f"不支持的嵌套键: {key}")
                    return False
            else:
                # 直接设置
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                else:
                    self.logger.error(f"未知的配置键: {key}")
                    return False
            
            # 保存配置
            return self.save_config()
            
        except Exception as e:
            self.logger.error(f"设置配置失败 {key}: {e}")
            return False
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        warnings = []
        
        # 检测容器环境
        is_container = self._detect_container_environment()
        
        # 验证 Claude 路径 (在容器环境中可选)
        if not is_container:
            if not self.config.claude_paths:
                errors.append("未配置 Claude 路径")
            else:
                valid_paths = []
                for path in self.config.claude_paths:
                    if Path(path).exists():
                        valid_paths.append(path)
                
                if not valid_paths:
                    errors.append("所有 Claude 路径都无效")
                else:
                    self.config.claude_paths = valid_paths
        
        # 验证 API 密钥
        if self.config.memory_enabled and not self.config.api_key:
            errors.append("启用记忆功能但未配置 API 密钥 (SILICONFLOW_API_KEY)")
        
        # 验证数据库配置
        if self.config.memory_enabled:
            db_errors = self._validate_database_config()
            errors.extend(db_errors)
        
        # 验证容器特定配置
        if is_container:
            container_errors = self._validate_container_config()
            errors.extend(container_errors)
        
        # 记录警告
        for warning in warnings:
            self.logger.warning(warning)
        
        return errors
    
    def _validate_database_config(self) -> List[str]:
        """验证数据库配置"""
        errors = []
        db_config = self.config.db_config
        
        if not db_config.host:
            errors.append("数据库主机未配置 (DB_HOST)")
        
        if not db_config.database:
            errors.append("数据库名称未配置 (DB_NAME)")
        
        if not db_config.user:
            errors.append("数据库用户未配置 (DB_USER)")
        
        if not db_config.password:
            errors.append("数据库密码未配置 (DB_PASSWORD)")
        
        if not (1 <= db_config.port <= 65535):
            errors.append(f"数据库端口无效: {db_config.port} (DB_PORT)")
        
        return errors
    
    def _validate_container_config(self) -> List[str]:
        """验证容器环境特定配置"""
        errors = []
        
        # 检查必需的环境变量
        required_env_vars = [
            'SILICONFLOW_API_KEY',
            'DB_HOST',
            'DB_NAME',
            'DB_USER',
            'DB_PASSWORD'
        ]
        
        for env_var in required_env_vars:
            if not os.environ.get(env_var):
                errors.append(f"容器环境缺少必需的环境变量: {env_var}")
        
        # 检查网络配置
        mcp_host = os.environ.get('MCP_SERVER_HOST', '0.0.0.0')
        if mcp_host not in ['0.0.0.0', '::']:
            errors.append(f"容器环境建议使用 MCP_SERVER_HOST=0.0.0.0，当前: {mcp_host}")
        
        return errors
    
    def export_config(self, path: Path) -> bool:
        """导出配置（不含敏感信息）"""
        try:
            export_data = self.config.to_dict()
            
            # 移除敏感信息
            sensitive_keys = ['api_key', 'password']
            
            for key in sensitive_keys:
                if key in export_data:
                    export_data[key] = '<REDACTED>'
                
                if 'db_config' in export_data and key in export_data['db_config']:
                    export_data['db_config'][key] = '<REDACTED>'
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)
            
            self.logger.info(f"配置已导出: {path}")
            return True
            
        except Exception as e:
            self.logger.error(f"配置导出失败: {e}")
            return False
    
    def import_config(self, path: Path, merge: bool = False) -> bool:
        """导入配置"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if merge:
                # 合并配置
                current_data = self.config.to_dict()
                current_data.update(import_data)
                self.config = SageConfig.from_dict(current_data)
            else:
                # 替换配置
                self.config = SageConfig.from_dict(import_data)
            
            return self.save_config()
            
        except Exception as e:
            self.logger.error(f"配置导入失败: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        self.logger.warning("重置为默认配置")
        
        # 备份当前配置
        self.backup_config(suffix='_before_reset')
        
        # 创建新的默认配置
        self.config = self.create_default_config()
        
        return True

# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
    
    return _config_manager

# 便捷函数
def get_config(key: Union[str, ConfigKey], default: Any = None) -> Any:
    """获取配置值"""
    return get_config_manager().get(key, default)

def set_config(key: Union[str, ConfigKey], value: Any) -> bool:
    """设置配置值"""
    return get_config_manager().set(key, value)

def validate_config() -> List[str]:
    """验证配置"""
    return get_config_manager().validate()

# CLI 接口
def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sage MCP 配置管理')
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 显示配置
    subparsers.add_parser('show', help='显示当前配置')
    
    # 获取配置
    get_parser = subparsers.add_parser('get', help='获取配置值')
    get_parser.add_argument('key', help='配置键')
    
    # 设置配置
    set_parser = subparsers.add_parser('set', help='设置配置值')
    set_parser.add_argument('key', help='配置键')
    set_parser.add_argument('value', help='配置值')
    
    # 验证配置
    subparsers.add_parser('validate', help='验证配置')
    
    # 导出配置
    export_parser = subparsers.add_parser('export', help='导出配置')
    export_parser.add_argument('path', help='导出路径')
    
    # 导入配置
    import_parser = subparsers.add_parser('import', help='导入配置')
    import_parser.add_argument('path', help='导入路径')
    import_parser.add_argument('--merge', action='store_true', help='合并配置')
    
    # 重置配置
    subparsers.add_parser('reset', help='重置为默认配置')
    
    args = parser.parse_args()
    
    manager = get_config_manager()
    
    if args.command == 'show':
        print(json.dumps(manager.config.to_dict(), indent=4, ensure_ascii=False))
    
    elif args.command == 'get':
        value = manager.get(args.key)
        print(f"{args.key}: {value}")
    
    elif args.command == 'set':
        # 尝试解析值
        try:
            value = json.loads(args.value)
        except:
            value = args.value
        
        if manager.set(args.key, value):
            print(f"已设置 {args.key} = {value}")
        else:
            print("设置失败")
            sys.exit(1)
    
    elif args.command == 'validate':
        errors = manager.validate()
        if errors:
            print("配置验证失败:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("配置验证通过")
    
    elif args.command == 'export':
        if manager.export_config(Path(args.path)):
            print(f"配置已导出到: {args.path}")
        else:
            print("导出失败")
            sys.exit(1)
    
    elif args.command == 'import':
        if manager.import_config(Path(args.path), merge=args.merge):
            print(f"配置已导入")
        else:
            print("导入失败")
            sys.exit(1)
    
    elif args.command == 'reset':
        response = input("确定要重置配置吗？(y/N): ")
        if response.lower() == 'y':
            if manager.reset_to_default():
                print("配置已重置")
            else:
                print("重置失败")
                sys.exit(1)
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()