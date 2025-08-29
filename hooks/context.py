#!/usr/bin/env python3
"""
Hook Execution Context Module
Sage项目统一的Hook执行上下文管理模块

作用：
1. 提供项目根目录的自动发现和路径管理
2. 统一配置文件解析和环境变量管理
3. 平台自动检测和兼容性处理
4. 为所有hook脚本提供一致的执行环境

设计原则：
- 单一职责：路径管理集中化，避免重复逻辑
- 依赖倒置：Hook脚本不负责环境检测，依赖抽象接口
- 高可测试性：支持Mock对象，完全隔离文件系统依赖
- 配置分层：支持默认值 → 配置文件 → 环境变量的优先级覆盖
"""

import os
import sys
import platform
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

# 加载环境变量文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 如果没有安装python-dotenv包，静默处理
    pass


@dataclass
class DatabaseConfig:
    """数据库配置数据类"""
    host: str
    port: int
    database: str
    user: str
    password: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password
        }


@dataclass
class EmbeddingConfig:
    """嵌入模型配置数据类"""
    model: str
    device: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "model": self.model,
            "device": self.device
        }


class HookExecutionContext:
    """
    Hook执行上下文管理器
    
    提供统一的项目环境管理、配置解析和路径处理功能。
    所有hook脚本应该通过此上下文获取环境信息，而不是直接处理路径和配置。
    """
    
    def __init__(self, script_path: Optional[Union[str, Path]] = None):
        """
        初始化执行上下文
        
        Args:
            script_path: 调用脚本的路径，用于自动计算项目根目录
                        如果不提供，将使用调用栈自动检测
        """
        self._project_root: Optional[Path] = None
        self._hooks_dir: Optional[Path] = None
        self._logs_dir: Optional[Path] = None
        self._config_dir: Optional[Path] = None
        self._scripts_dir: Optional[Path] = None
        
        # 平台信息缓存
        self._platform_info: Optional[Dict[str, str]] = None
        
        # 配置缓存
        self._db_config: Optional[DatabaseConfig] = None
        self._embedding_config: Optional[EmbeddingConfig] = None
        self._sage_config: Optional[Dict[str, Any]] = None
        
        # 如果提供了脚本路径，使用它来计算项目根目录
        if script_path:
            self._calculate_project_root_from_path(Path(script_path))
    
    def _calculate_project_root_from_path(self, script_path: Path) -> None:
        """
        从给定的脚本路径计算项目根目录
        
        Args:
            script_path: 脚本文件路径
        """
        # 标准化脚本路径：hooks/scripts/xxx.py -> 项目根目录
        script_path = script_path.resolve()
        
        # 检查是否在标准的hooks/scripts结构中
        if script_path.parent.name == "scripts" and script_path.parent.parent.name == "hooks":
            self._project_root = script_path.parent.parent.parent
        else:
            # 如果不在标准结构中，向上查找包含sage_core的目录
            current = script_path.parent
            while current != current.parent:  # 避免到达根目录
                if (current / "sage_core").exists():
                    self._project_root = current
                    break
                current = current.parent
            
            # 如果仍未找到，使用脚本路径的上三级目录作为默认值
            if self._project_root is None:
                self._project_root = script_path.parent.parent.parent
    
    @property
    def project_root(self) -> Path:
        """获取项目根目录路径"""
        if self._project_root is None:
            # 懒加载：通过调用栈自动检测项目根目录
            import inspect
            frame = inspect.currentframe()
            try:
                # 获取调用者的文件路径
                caller_frame = frame.f_back
                if caller_frame and caller_frame.f_code.co_filename:
                    caller_path = Path(caller_frame.f_code.co_filename)
                    self._calculate_project_root_from_path(caller_path)
                
                # 如果仍然无法确定，使用当前工作目录作为后备
                if self._project_root is None:
                    self._project_root = Path.cwd()
            finally:
                del frame
        
        return self._project_root
    
    @property
    def hooks_dir(self) -> Path:
        """获取hooks目录路径"""
        if self._hooks_dir is None:
            self._hooks_dir = self.project_root / "hooks"
        return self._hooks_dir
    
    @property
    def logs_dir(self) -> Path:
        """获取logs目录路径"""
        if self._logs_dir is None:
            self._logs_dir = self.project_root / "logs" / "Hooks"
            self._logs_dir.mkdir(parents=True, exist_ok=True)
        return self._logs_dir
    
    @property
    def config_dir(self) -> Path:
        """获取配置目录路径"""
        if self._config_dir is None:
            self._config_dir = self.hooks_dir / "configs"
        return self._config_dir
    
    @property
    def scripts_dir(self) -> Path:
        """获取scripts目录路径"""
        if self._scripts_dir is None:
            self._scripts_dir = self.hooks_dir / "scripts"
        return self._scripts_dir
    
    def get_platform_info(self) -> Dict[str, str]:
        """获取平台信息"""
        if self._platform_info is None:
            self._platform_info = {
                "system": platform.system(),  # Windows, Darwin, Linux
                "platform": platform.platform(),
                "architecture": platform.architecture()[0],
                "python_version": platform.python_version(),
                "os_name": os.name  # nt, posix
            }
        return self._platform_info
    
    def is_windows(self) -> bool:
        """检查是否为Windows平台"""
        return self.get_platform_info()["system"] == "Windows"
    
    def is_macos(self) -> bool:
        """检查是否为macOS平台"""
        return self.get_platform_info()["system"] == "Darwin"
    
    def is_linux(self) -> bool:
        """检查是否为Linux平台"""
        return self.get_platform_info()["system"] == "Linux"
    
    def setup_python_path(self) -> None:
        """
        设置Python模块搜索路径，确保可以导入sage_core
        
        这个方法替代了原来在各个脚本中重复的sys.path.insert逻辑
        """
        project_root_str = str(self.project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
    
    def get_db_config(self) -> DatabaseConfig:
        """
        获取数据库配置
        
        优先级：环境变量 > 配置文件 > 默认值
        """
        if self._db_config is None:
            # 默认配置
            defaults = {
                "host": "localhost",
                "port": 5432,
                "database": "sage_memory",
                "user": "sage",
                "password": "sage123"
            }
            
            # 尝试从配置文件加载
            config_from_file = self._load_config_from_file()
            db_config_file = config_from_file.get("database", {})
            
            # 合并配置：默认值 < 配置文件 < 环境变量
            final_config = defaults.copy()
            final_config.update(db_config_file)
            
            # 环境变量覆盖
            final_config.update({
                "host": os.getenv("DB_HOST", final_config["host"]),
                "port": int(os.getenv("DB_PORT", str(final_config["port"]))),
                "database": os.getenv("DB_NAME", final_config["database"]),
                "user": os.getenv("DB_USER", final_config["user"]),
                "password": os.getenv("DB_PASSWORD", final_config["password"])
            })
            
            self._db_config = DatabaseConfig(**final_config)
        
        return self._db_config
    
    def get_embedding_config(self) -> EmbeddingConfig:
        """
        获取嵌入模型配置
        
        优先级：环境变量 > 配置文件 > 默认值
        """
        if self._embedding_config is None:
            # 默认配置
            defaults = {
                "model": "Qwen/Qwen3-Embedding-8B",
                "device": "cpu"
            }
            
            # 尝试从配置文件加载
            config_from_file = self._load_config_from_file()
            embedding_config_file = config_from_file.get("embedding", {})
            
            # 合并配置：默认值 < 配置文件 < 环境变量
            final_config = defaults.copy()
            final_config.update(embedding_config_file)
            
            # 环境变量覆盖
            final_config.update({
                "model": os.getenv("EMBEDDING_MODEL", final_config["model"]),
                "device": os.getenv("EMBEDDING_DEVICE", final_config["device"])
            })
            
            self._embedding_config = EmbeddingConfig(**final_config)
        
        return self._embedding_config
    
    def get_sage_config(self) -> Dict[str, Any]:
        """
        获取完整的Sage配置字典
        
        返回适用于sage_core初始化的配置格式
        """
        if self._sage_config is None:
            db_config = self.get_db_config()
            embedding_config = self.get_embedding_config()
            
            self._sage_config = {
                "database": db_config.to_dict(),
                "embedding": embedding_config.to_dict()
            }
        
        return self._sage_config
    
    def _load_config_from_file(self) -> Dict[str, Any]:
        """
        从配置文件加载配置
        
        查找顺序：
        1. hooks/configs/sage_config.json
        2. hooks/configs/sage_hooks.json
        3. 项目根目录下的sage_config.json
        """
        config_files = [
            self.config_dir / "sage_config.json",
            self.config_dir / "sage_hooks.json",
            self.project_root / "sage_config.json"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    # 配置文件损坏时继续尝试下一个
                    logging.warning(f"Failed to load config from {config_file}: {e}")
                    continue
        
        # 如果没有找到配置文件，返回空字典
        return {}
    
    def setup_logging(self, logger_name: str, log_filename: str) -> logging.Logger:
        """
        设置标准化的日志配置
        
        Args:
            logger_name: 日志记录器名称
            log_filename: 日志文件名
            
        Returns:
            配置好的日志记录器
        """
        log_file_path = self.logs_dir / log_filename
        
        # 创建日志记录器
        logger = logging.getLogger(logger_name)
        
        # 避免重复添加处理器
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            # 文件处理器
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 控制台处理器（输出到stderr，不影响stdout）
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(logging.INFO)
            
            # 格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def get_backup_dir(self) -> Path:
        """获取备份目录路径"""
        backup_dir = self.logs_dir / "backup"
        backup_dir.mkdir(exist_ok=True)
        return backup_dir
    
    def validate_environment(self) -> Dict[str, bool]:
        """
        验证执行环境的完整性
        
        Returns:
            验证结果字典，包含各项检查的通过状态
        """
        results = {}
        
        # 检查项目根目录
        results["project_root_exists"] = self.project_root.exists()
        
        # 检查sage_core目录
        sage_core_path = self.project_root / "sage_core"
        results["sage_core_exists"] = sage_core_path.exists()
        
        # 检查hooks目录结构
        results["hooks_dir_exists"] = self.hooks_dir.exists()
        results["scripts_dir_exists"] = self.scripts_dir.exists()
        results["logs_dir_writable"] = os.access(self.logs_dir, os.W_OK)
        
        # 检查Python路径设置
        results["python_path_configured"] = str(self.project_root) in sys.path
        
        # 检查配置可访问性
        try:
            db_config = self.get_db_config()
            results["db_config_valid"] = bool(db_config.host and db_config.database)
        except Exception:
            results["db_config_valid"] = False
        
        try:
            embedding_config = self.get_embedding_config()
            results["embedding_config_valid"] = bool(embedding_config.model)
        except Exception:
            results["embedding_config_valid"] = False
        
        # Phase 4.2 增强验证: 检查SiliconFlow API环境
        results["siliconflow_api_key_exists"] = bool(os.getenv('SILICONFLOW_API_KEY'))
        
        # Phase 4.2 增强验证: 检查Memory Fusion模板文件
        memory_fusion_template_path = self.project_root / "prompts" / "memory_fusion_prompt_programming.txt"
        results["memory_fusion_template_exists"] = memory_fusion_template_path.exists()
        
        # Phase 4.2 增强验证: 检查网络连接到SiliconFlow API
        results["siliconflow_api_accessible"] = self._check_network_connectivity()
        
        # Phase 4.2 增强验证: 检查SAGE_MAX_RESULTS环境变量有效性
        sage_max_results = os.getenv('SAGE_MAX_RESULTS', '10')
        try:
            max_results_value = int(sage_max_results)
            results["sage_max_results_valid"] = 1 <= max_results_value <= 100
        except ValueError:
            results["sage_max_results_valid"] = False
        
        return results
    
    def _check_network_connectivity(self) -> bool:
        """
        检查到SiliconFlow API的网络连接性
        
        Returns:
            网络连接是否可用
        """
        import socket
        
        try:
            # 尝试连接到SiliconFlow API主机
            # 使用socket进行快速连接测试，避免完整HTTP请求的开销
            host = "api.siliconflow.cn"
            port = 443  # HTTPS端口
            
            # 设置较短的超时时间
            socket.setdefaulttimeout(3)
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                result = sock.connect_ex((host, port))
                return result == 0  # 0表示连接成功
                
        except Exception:
            return False
        finally:
            # 重置默认超时
            socket.setdefaulttimeout(None)
    
    def ensure_script_permissions(self, auto_fix: bool = True) -> Dict[str, Any]:
        """
        确保hook脚本具有正确的执行权限
        
        Args:
            auto_fix: 是否自动修复权限问题
            
        Returns:
            权限检查和修复结果
        """
        import stat
        
        results = {
            "platform": self.get_platform_info()["system"],
            "scripts_checked": 0,
            "scripts_fixed": 0,
            "scripts_failed": 0,
            "details": []
        }
        
        scripts_dir = self.scripts_dir
        if not scripts_dir.exists():
            return results
        
        # 识别需要执行权限的脚本
        for script_file in scripts_dir.glob("*.py"):
            if self._should_script_be_executable(script_file):
                results["scripts_checked"] += 1
                
                if self.is_windows():
                    # Windows下通过文件关联执行，无需特殊权限
                    results["details"].append({
                        "script": script_file.name,
                        "status": "ok",
                        "message": "Windows platform - execution via file association"
                    })
                else:
                    # Unix系统检查和修复执行权限
                    try:
                        file_stat = script_file.stat()
                        has_exec = bool(file_stat.st_mode & stat.S_IEXEC)
                        
                        if has_exec:
                            results["details"].append({
                                "script": script_file.name,
                                "status": "ok",
                                "message": "Already has execute permission"
                            })
                        else:
                            if auto_fix:
                                try:
                                    script_file.chmod(0o755)
                                    results["scripts_fixed"] += 1
                                    results["details"].append({
                                        "script": script_file.name,
                                        "status": "fixed",
                                        "message": "Execute permission added"
                                    })
                                except OSError as e:
                                    results["scripts_failed"] += 1
                                    results["details"].append({
                                        "script": script_file.name,
                                        "status": "failed",
                                        "message": f"Failed to fix permission: {e}"
                                    })
                            else:
                                results["details"].append({
                                    "script": script_file.name,
                                    "status": "needs_fix",
                                    "message": "Missing execute permission"
                                })
                    except OSError as e:
                        results["scripts_failed"] += 1
                        results["details"].append({
                            "script": script_file.name,
                            "status": "error",
                            "message": f"Cannot check permission: {e}"
                        })
        
        return results
    
    def _should_script_be_executable(self, script_file: Path) -> bool:
        """判断脚本是否应该具有执行权限"""
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                content = f.read(1024)  # 只读前1024字符以提高性能
            
            # 检查条件
            has_shebang = content.startswith('#!/')
            has_main = 'if __name__ == "__main__":' in content
            is_hook_script = script_file.name.startswith('sage_')
            
            return has_shebang or has_main or is_hook_script
            
        except Exception:
            return False
    
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """
        获取完整的诊断信息，用于问题排查
        
        Returns:
            包含环境信息、配置状态、验证结果的诊断数据
        """
        diagnostic_info = {
            "platform_info": self.get_platform_info(),
            "paths": {
                "project_root": str(self.project_root),
                "hooks_dir": str(self.hooks_dir),
                "logs_dir": str(self.logs_dir),
                "config_dir": str(self.config_dir),
                "scripts_dir": str(self.scripts_dir)
            },
            "configs": {
                "database": self.get_db_config().to_dict(),
                "embedding": self.get_embedding_config().to_dict()
            },
            "environment_validation": self.validate_environment(),
            "python_path": sys.path[:5]  # 显示前5个路径
        }
        
        # 添加权限检查信息
        try:
            permission_info = self.ensure_script_permissions(auto_fix=False)
            diagnostic_info["script_permissions"] = permission_info
        except Exception as e:
            diagnostic_info["script_permissions"] = {
                "error": f"Permission check failed: {e}"
            }
        
        return diagnostic_info


# 便利函数：创建上下文实例
def create_hook_context(script_path: Optional[Union[str, Path]] = None, 
                       auto_fix_permissions: bool = True) -> HookExecutionContext:
    """
    便利函数：创建Hook执行上下文实例
    
    Args:
        script_path: 调用脚本的路径（可选）
        auto_fix_permissions: 是否自动检查和修复脚本权限（默认True）
        
    Returns:
        配置好的HookExecutionContext实例
    """
    context = HookExecutionContext(script_path)
    
    # 自动设置Python路径
    context.setup_python_path()
    
    # 自动权限管理（一劳永逸解决方案）
    if auto_fix_permissions:
        try:
            permission_results = context.ensure_script_permissions(auto_fix=True)
            # 如果修复了权限，记录到日志（但不打印以避免干扰脚本输出）
            if permission_results["scripts_fixed"] > 0:
                import logging
                logger = logging.getLogger("HookExecutionContext")
                logger.info(f"自动修复了 {permission_results['scripts_fixed']} 个脚本的权限")
        except Exception:
            # 权限修复失败时静默处理，不影响主要功能
            pass
    
    return context


# 模块级便利函数
def get_project_root(script_path: Optional[Union[str, Path]] = None) -> Path:
    """快速获取项目根目录"""
    return create_hook_context(script_path).project_root


def setup_sage_environment(script_path: Optional[Union[str, Path]] = None) -> HookExecutionContext:
    """快速设置Sage执行环境"""
    context = create_hook_context(script_path)
    return context


if __name__ == "__main__":
    # 测试和诊断模式
    context = create_hook_context()
    
    print("=== Sage Hook Execution Context 诊断信息 ===")
    import pprint
    pprint.pprint(context.get_diagnostic_info())
    
    print("\n=== 环境验证结果 ===")
    validation = context.validate_environment()
    for check, passed in validation.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check}: {status}")