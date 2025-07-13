#!/usr/bin/env python3
"""
Sage MCP 跨平台工具类
提供统一的跨平台命令解析、路径处理和编码处理
"""

import os
import sys
import platform
import shlex
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Union, Dict, Any
import logging
import locale

from exceptions import PlatformCompatibilityError, ValidationError

logger = logging.getLogger('SagePlatformUtils')


class PlatformInfo:
    """平台信息类"""
    
    def __init__(self):
        self.system = platform.system()
        self.is_windows = self.system == 'Windows'
        self.is_macos = self.system == 'Darwin'
        self.is_linux = self.system == 'Linux'
        self.is_posix = os.name == 'posix'
        
        # 详细信息
        self.version = platform.version()
        self.machine = platform.machine()
        self.python_version = sys.version
        
        # 编码信息
        self.encoding = locale.getpreferredencoding()
        self.filesystem_encoding = sys.getfilesystemencoding()
        
    def __str__(self):
        return f"{self.system} {self.version} ({self.machine})"
    
    def get_info_dict(self) -> Dict[str, Any]:
        """获取平台信息字典"""
        return {
            'system': self.system,
            'version': self.version,
            'machine': self.machine,
            'python_version': self.python_version,
            'encoding': self.encoding,
            'filesystem_encoding': self.filesystem_encoding,
            'is_windows': self.is_windows,
            'is_macos': self.is_macos,
            'is_linux': self.is_linux,
            'is_posix': self.is_posix
        }


class CommandParser:
    """跨平台命令解析器"""
    
    def __init__(self, platform_info: Optional[PlatformInfo] = None):
        self.platform_info = platform_info or PlatformInfo()
    
    def parse_command(self, command: Union[str, List[str]]) -> List[str]:
        """解析命令为参数列表"""
        if isinstance(command, list):
            return command
        
        if not isinstance(command, str):
            raise ValidationError("命令必须是字符串或列表", value=command)
        
        # Windows特殊处理
        if self.platform_info.is_windows:
            return self._parse_windows_command(command)
        else:
            return self._parse_posix_command(command)
    
    def _parse_windows_command(self, command: str) -> List[str]:
        """Windows命令解析"""
        # Windows不使用shlex，因为它的引号规则不同
        # 简单实现：处理双引号
        args = []
        current = []
        in_quotes = False
        escaped = False
        
        for char in command:
            if escaped:
                current.append(char)
                escaped = False
            elif char == '\\' and not in_quotes:
                escaped = True
            elif char == '"':
                in_quotes = not in_quotes
            elif char in ' \t' and not in_quotes:
                if current:
                    args.append(''.join(current))
                    current = []
            else:
                current.append(char)
        
        if current:
            args.append(''.join(current))
        
        return args
    
    def _parse_posix_command(self, command: str) -> List[str]:
        """POSIX命令解析"""
        try:
            return shlex.split(command)
        except ValueError as e:
            # 如果解析失败，回退到简单分割
            logger.warning(f"shlex解析失败，使用简单分割: {e}")
            return command.split()
    
    def join_command(self, args: List[str]) -> str:
        """将参数列表连接为命令字符串"""
        if self.platform_info.is_windows:
            # Windows引号处理
            quoted_args = []
            for arg in args:
                if ' ' in arg or '\t' in arg:
                    # 转义内部引号
                    escaped = arg.replace('"', '\\"')
                    quoted_args.append(f'"{escaped}"')
                else:
                    quoted_args.append(arg)
            return ' '.join(quoted_args)
        else:
            # POSIX使用shlex.quote
            return shlex.join(args)


class PathHandler:
    """跨平台路径处理器"""
    
    def __init__(self, platform_info: Optional[PlatformInfo] = None):
        self.platform_info = platform_info or PlatformInfo()
    
    def normalize_path(self, path: Union[str, Path]) -> Path:
        """规范化路径"""
        if isinstance(path, str):
            path = Path(path)
        
        # 展开用户目录和环境变量
        path = path.expanduser()
        
        # Windows特殊处理
        if self.platform_info.is_windows:
            # 处理UNC路径
            path_str = str(path)
            if path_str.startswith('\\\\'):
                return Path(path_str)
            
            # 处理短路径名
            try:
                import ctypes
                from ctypes import wintypes
                
                # 获取长路径名
                GetLongPathName = ctypes.windll.kernel32.GetLongPathNameW
                buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
                GetLongPathName(str(path), buffer, wintypes.MAX_PATH)
                if buffer.value:
                    path = Path(buffer.value)
            except:
                pass
        
        # 解析为绝对路径
        return path.resolve()
    
    def ensure_path_exists(self, path: Union[str, Path], 
                          create_parents: bool = True) -> Path:
        """确保路径存在"""
        path = self.normalize_path(path)
        
        if path.exists():
            return path
        
        if create_parents:
            path.parent.mkdir(parents=True, exist_ok=True)
        
        return path
    
    def get_executable_extensions(self) -> List[str]:
        """获取可执行文件扩展名"""
        if self.platform_info.is_windows:
            pathext = os.environ.get('PATHEXT', '.COM;.EXE;.BAT;.CMD')
            return [ext.lower() for ext in pathext.split(';')]
        else:
            return ['', '.sh', '.py']  # POSIX通常不需要扩展名
    
    def find_executable(self, name: str, 
                       search_paths: Optional[List[Union[str, Path]]] = None) -> Optional[Path]:
        """查找可执行文件"""
        # 使用系统PATH
        if search_paths is None:
            search_paths = os.environ.get('PATH', '').split(os.pathsep)
        
        extensions = self.get_executable_extensions()
        
        for search_path in search_paths:
            search_path = self.normalize_path(search_path)
            
            for ext in extensions:
                if self.platform_info.is_windows:
                    # Windows不区分大小写
                    candidate = search_path / f"{name}{ext}"
                else:
                    candidate = search_path / f"{name}{ext}"
                
                if candidate.exists() and os.access(str(candidate), os.X_OK):
                    return candidate
        
        return None


class EncodingHandler:
    """跨平台编码处理器"""
    
    def __init__(self, platform_info: Optional[PlatformInfo] = None):
        self.platform_info = platform_info or PlatformInfo()
        self.default_encoding = 'utf-8'
    
    def get_console_encoding(self) -> str:
        """获取控制台编码"""
        if self.platform_info.is_windows:
            # Windows控制台可能使用不同编码
            import ctypes
            kernel32 = ctypes.windll.kernel32
            cp = kernel32.GetConsoleCP()
            if cp:
                return f'cp{cp}'
        
        return sys.stdout.encoding or self.default_encoding
    
    def decode_output(self, data: bytes, errors: str = 'replace') -> str:
        """解码输出数据"""
        # 尝试多种编码
        encodings = [
            self.default_encoding,
            self.platform_info.encoding,
            self.platform_info.filesystem_encoding,
            'latin-1'  # 最后的回退
        ]
        
        for encoding in encodings:
            if encoding:
                try:
                    return data.decode(encoding, errors='strict')
                except UnicodeDecodeError:
                    continue
        
        # 使用错误处理策略
        return data.decode(self.default_encoding, errors=errors)
    
    def encode_input(self, text: str) -> bytes:
        """编码输入数据"""
        return text.encode(self.default_encoding, errors='replace')


class ProcessLauncher:
    """跨平台进程启动器"""
    
    def __init__(self, platform_info: Optional[PlatformInfo] = None):
        self.platform_info = platform_info or PlatformInfo()
        self.command_parser = CommandParser(platform_info)
        self.encoding_handler = EncodingHandler(platform_info)
    
    def prepare_environment(self, env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """准备进程环境"""
        # 复制当前环境
        process_env = os.environ.copy()
        
        # 设置编码
        process_env['PYTHONIOENCODING'] = 'utf-8'
        
        if self.platform_info.is_windows:
            # Windows特定环境变量
            process_env['PYTHONUTF8'] = '1'
        
        # 合并用户环境
        if env:
            process_env.update(env)
        
        return process_env
    
    def create_process(self, command: Union[str, List[str]], 
                      cwd: Optional[Union[str, Path]] = None,
                      env: Optional[Dict[str, str]] = None,
                      **kwargs) -> subprocess.Popen:
        """创建跨平台进程"""
        # 解析命令
        if isinstance(command, str):
            command = self.command_parser.parse_command(command)
        
        # 准备参数
        popen_kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'stdin': subprocess.PIPE,
            'env': self.prepare_environment(env),
            'universal_newlines': False,  # 使用二进制模式
        }
        
        if cwd:
            popen_kwargs['cwd'] = str(PathHandler().normalize_path(cwd))
        
        # Windows特定设置
        if self.platform_info.is_windows:
            # 隐藏窗口
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            popen_kwargs['startupinfo'] = startupinfo
            
            # 防止继承句柄
            popen_kwargs['close_fds'] = False
        else:
            popen_kwargs['close_fds'] = True
        
        # 合并用户参数
        popen_kwargs.update(kwargs)
        
        return subprocess.Popen(command, **popen_kwargs)


# 单例实例
_platform_info = None


def get_platform_info() -> PlatformInfo:
    """获取平台信息单例"""
    global _platform_info
    if _platform_info is None:
        _platform_info = PlatformInfo()
    return _platform_info


# 便捷函数
def parse_command(command: Union[str, List[str]]) -> List[str]:
    """便捷函数：解析命令"""
    return CommandParser().parse_command(command)


def normalize_path(path: Union[str, Path]) -> Path:
    """便捷函数：规范化路径"""
    return PathHandler().normalize_path(path)


def find_executable(name: str) -> Optional[Path]:
    """便捷函数：查找可执行文件"""
    return PathHandler().find_executable(name)


def create_process(command: Union[str, List[str]], **kwargs) -> subprocess.Popen:
    """便捷函数：创建进程"""
    return ProcessLauncher().create_process(command, **kwargs)