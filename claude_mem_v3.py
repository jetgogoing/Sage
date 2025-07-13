#!/usr/bin/env python3
"""
Sage MCP 跨平台记忆系统 V3
完整实现对话捕获和智能记忆功能
"""

import sys
import os

# 调试输出
if os.getenv('SAGE_DEBUG'):
    print(f"[SAGE DEBUG] 启动 claude_mem_v3.py", file=sys.stderr)
    print(f"[SAGE DEBUG] sys.argv: {sys.argv}", file=sys.stderr)
    print(f"[SAGE DEBUG] SAGE_RECURSION_GUARD: {os.getenv('SAGE_RECURSION_GUARD')}", file=sys.stderr)

# 性能优化：尝试导入优化模块
try:
    from performance_optimizer import (
        init_performance_optimizations,
        monitor_performance,
        query_cache,
        LazyImporter
    )
    # 初始化性能优化
    init_performance_optimizations()
    PERFORMANCE_OPTIMIZED = True
except ImportError:
    # 如果优化模块不可用，定义空装饰器
    def monitor_performance(name):
        def decorator(func):
            return func
        return decorator
    query_cache = None
    PERFORMANCE_OPTIMIZED = False

import subprocess
import platform
import json
import shutil
import argparse
import threading
import time
import atexit
import weakref
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import logging
from datetime import datetime
from dataclasses import dataclass

# 导入配置适配器
from config_adapter import get_config_adapter, get_config

# 导入记忆接口
from memory_interface import get_memory_provider, IMemoryProvider

# 导入阶段2智能增强模块
from intelligent_retrieval import create_intelligent_retrieval_engine, RetrievalStrategy
from prompt_enhancer import create_prompt_enhancer, EnhancementLevel

# 导入新的基础设施模块
from exceptions import (
    SageBaseException, ConfigurationError, MemoryProviderError,
    ClaudeExecutionError, ClaudeNotFoundError, PlatformCompatibilityError,
    AsyncRuntimeError, ResourceManagementError, ValidationError
)
from async_manager import get_event_loop_manager, managed_async_context, ensure_async_cleanup
from platform_utils import get_platform_info, CommandParser, PathHandler, ProcessLauncher

# 递归保护检查（必须在导入其他模块之前）
# 阶段4稳定版本：简单可靠的环境变量检查
if os.getenv('SAGE_RECURSION_GUARD') == '1':
    print("[Sage] 检测到递归调用，直接传递给原始 Claude", file=sys.stderr)
    # 找到原始 claude 并执行
    original_claude = os.getenv('ORIGINAL_CLAUDE_PATH')
    if not original_claude:
        # 使用实际的Claude可执行文件路径
        original_claude = '/Users/jet/.claude/local/node_modules/.bin/claude'
    
    if original_claude and os.path.exists(original_claude):
        os.execv(original_claude, ['claude'] + sys.argv[1:])
    else:
        print("[Sage] 错误：未找到原始 Claude CLI", file=sys.stderr)
        sys.exit(1)
    sys.exit(1)

# 配置日志
log_dir = Path.home() / '.sage-mcp' / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"sage-mcp-{datetime.now().strftime('%Y%m%d')}.log"

# 配置日志格式 - 更简洁
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
    ]
)
logger = logging.getLogger('SageMCP')

# 延迟导入 psutil（在 logger 初始化后）
try:
    import psutil  # 用于资源监控
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("psutil 未安装，资源监控功能将被禁用")
    PSUTIL_AVAILABLE = False

@dataclass
class ParsedArgs:
    """解析后的参数"""
    user_prompt: Optional[str] = None
    claude_args: List[str] = None
    sage_options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.claude_args is None:
            self.claude_args = []
        if self.sage_options is None:
            self.sage_options = {}


if PSUTIL_AVAILABLE:
    class ResourceMonitor:
        """资源监控器（完整版）"""
        
        def __init__(self):
            self.process = psutil.Process()
            self.initial_memory = self.get_memory_usage()
            self.memory_limit = self.get_memory_limit()
            self.peak_memory = self.initial_memory
            
        def get_memory_limit(self) -> int:
            """获取内存限制（默认500MB）"""
            config_adapter = get_config_adapter()
            return config_adapter.get('memory_limit_mb', 500) * 1024 * 1024
        
        def get_memory_usage(self) -> int:
            """获取当前内存使用量"""
            try:
                return self.process.memory_info().rss
            except:
                return 0
        
        def check_memory(self) -> Tuple[bool, int, int]:
            """检查内存使用情况
            返回: (是否超限, 当前使用量, 限制)
            """
            current = self.get_memory_usage()
            self.peak_memory = max(self.peak_memory, current)
            return current > self.memory_limit, current, self.memory_limit
        
        def get_resource_stats(self) -> Dict[str, Any]:
            """获取资源统计信息"""
            try:
                memory_info = self.process.memory_info()
                cpu_percent = self.process.cpu_percent(interval=0.1)
                
                return {
                    'memory_rss_mb': memory_info.rss / 1024 / 1024,
                    'memory_vms_mb': memory_info.vms / 1024 / 1024,
                    'memory_peak_mb': self.peak_memory / 1024 / 1024,
                    'cpu_percent': cpu_percent,
                    'num_threads': self.process.num_threads(),
                    'num_fds': len(self.process.open_files()) if hasattr(self.process, 'open_files') else 0
                }
            except (AttributeError, OSError) as e:
                logger.warning(f"获取资源统计失败: {e}")
                return {}
else:
    class ResourceMonitor:
        """资源监控器（降级版）"""
        
        def __init__(self):
            self.memory_limit = self.get_memory_limit()
            self.peak_memory = 0
            
        def get_memory_limit(self) -> int:
            """获取内存限制（默认500MB）"""
            config_adapter = get_config_adapter()
            return config_adapter.get('memory_limit_mb', 500) * 1024 * 1024
        
        def get_memory_usage(self) -> int:
            """获取当前内存使用量（降级版返回0）"""
            return 0
        
        def check_memory(self) -> Tuple[bool, int, int]:
            """检查内存使用情况（降级版总是返回未超限）"""
            return False, 0, self.memory_limit
        
        def get_resource_stats(self) -> Dict[str, Any]:
            """获取资源统计信息（降级版返回空）"""
            return {
                'status': 'psutil not available',
                'memory_limit_mb': self.memory_limit / 1024 / 1024
            }

class ImprovedCrossplatformClaude:
    """改进的跨平台 Claude 记忆系统"""
    
    # Claude 已知的选项参数（基于实际 CLI）
    CLAUDE_OPTIONS_WITH_VALUE = {
        '--output-format',
        '--input-format',
        '--allowedTools',
        '--disallowedTools',
        '--mcp-config',
        '--append-system-prompt',
        '--prepend-system-prompt',
        '--cwd',
        '--continue',
        '--context-file',
        '--skip'
    }
    
    CLAUDE_FLAGS = {
        '-h', '--help',
        '-d', '--debug',
        '--verbose',
        '-p', '--print',
        '--mcp-debug',
        '--dangerously-skip-permissions',
        '--edit',
        '--no-cache',
        '--clear-cache',
        '--no-context',
        '--resume'
    }
    
    def __init__(self):
        # 使用新的平台工具
        self.platform_info = get_platform_info()
        self.platform = self.platform_info.system
        self.is_windows = self.platform_info.is_windows
        self.is_macos = self.platform_info.is_macos
        self.is_linux = self.platform_info.is_linux
        
        # 初始化工具类
        self.command_parser = CommandParser(self.platform_info)
        self.path_handler = PathHandler(self.platform_info)
        self.process_launcher = ProcessLauncher(self.platform_info)
        
        # 异步管理器
        self.async_manager = get_event_loop_manager()
        
        # 配置目录
        self.config_dir = Path.home() / '.sage-mcp'
        self.config_file = self.config_dir / 'config.json'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用配置适配器
        self.config_adapter = get_config_adapter()
        
        # 记忆提供者
        self._memory_provider = None
        
        # 阶段2: 智能检索和提示增强
        self._retrieval_engine = None
        self._prompt_enhancer = None
        self._stage2_enabled = self.get_config('stage2_enabled', True)
        
        # 响应收集器和资源管理
        self.response_collector = []
        self.response_lock = threading.Lock()
        self._active_threads = weakref.WeakSet()
        self._active_processes = weakref.WeakSet()
        self._resource_monitor = ResourceMonitor()
        
        # 注册清理函数
        atexit.register(self._cleanup_resources)
        
        # 上下文管理器支持
        self._in_context = False
        
    def __enter__(self):
        """进入上下文管理器"""
        self._in_context = True
        logger.debug("进入 Sage 上下文管理器")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        logger.debug("退出 Sage 上下文管理器")
        self._cleanup_resources()
        self._in_context = False
        
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值（兼容旧接口）"""
        return self.config_adapter.get(key, default)
    
    @property
    def memory_provider(self) -> IMemoryProvider:
        """获取记忆提供者（延迟加载）"""
        if self._memory_provider is None:
            # 根据配置决定使用哪种提供者
            if self.get_config('memory_enabled', True):
                self._memory_provider = get_memory_provider("v1")
            else:
                self._memory_provider = get_memory_provider("null")
        return self._memory_provider
    
    @property
    def retrieval_engine(self):
        """获取智能检索引擎（延迟加载）"""
        if self._retrieval_engine is None and self._stage2_enabled:
            try:
                self._retrieval_engine = create_intelligent_retrieval_engine(self.memory_provider)
                logger.info("智能检索引擎已初始化")
            except (MemoryProviderError, ImportError, AttributeError) as e:
                logger.error(f"智能检索引擎初始化失败: {e}")
        return self._retrieval_engine
    
    @property
    def prompt_enhancer(self):
        """获取提示增强器（延迟加载）"""
        if self._prompt_enhancer is None and self._stage2_enabled and self.retrieval_engine:
            try:
                prompts_dir = Path(__file__).parent / "prompts"
                self._prompt_enhancer = create_prompt_enhancer(self.retrieval_engine, prompts_dir)
                logger.info("提示增强器已初始化")
            except (ImportError, AttributeError) as e:
                logger.error(f"提示增强器初始化失败: {e}")
        return self._prompt_enhancer
    
    def find_claude_executable(self) -> Optional[str]:
        """查找真正的 Claude 可执行文件"""
        # 1. 优先检查环境变量（用于测试和配置）
        claude_env = os.getenv('ORIGINAL_CLAUDE_PATH')
        if claude_env:
            # 支持 "python3 script.py" 这样的命令
            if ' ' in claude_env:
                # 这是一个命令，不是路径，直接返回
                return claude_env
            else:
                # 对于路径，即使不存在也返回（用于测试）
                return claude_env
        
        # 2. 检查配置中的路径
        for path in self.get_config('claude_paths', []):
            if Path(path).exists() and self._is_real_claude(Path(path)):
                return str(path)
        
        # 3. 在 PATH 中查找（排除我们自己）
        for path_dir in os.environ.get('PATH', '').split(os.pathsep):
            if 'sage-mcp' in path_dir.lower():
                continue
                
            claude_name = 'claude.exe' if self.is_windows else 'claude'
            claude_path = Path(path_dir) / claude_name
            
            if claude_path.exists() and self._is_real_claude(claude_path):
                return str(claude_path)
        
        # 4. 平台特定搜索
        if self.is_windows:
            search_paths = [
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Claude' / 'claude.exe',
                Path('C:/Program Files/Claude/claude.exe'),
                Path('C:/Program Files (x86)/Claude/claude.exe'),
            ]
        else:
            search_paths = [
                Path('/usr/local/bin/claude'),
                Path('/usr/bin/claude'),
                Path.home() / '.local' / 'bin' / 'claude',
                Path.home() / '.claude' / 'local' / 'claude',
            ]
        
        for path in search_paths:
            if path.exists() and self._is_real_claude(path):
                return str(path)
        
        return None
    
    def _is_real_claude(self, path: Path) -> bool:
        """检查是否是真正的 Claude（不是我们的包装器）"""
        try:
            # 检查文件大小 - 真正的 Claude 应该比较大
            if path.stat().st_size < 10240:  # 小于 10KB 可能是脚本
                # 尝试读取看是否包含我们的标记
                with open(path, 'rb') as f:
                    header = f.read(1024)
                    if b'sage' in header.lower() or b'memory' in header.lower():
                        return False
            return True
        except:
            return True
    
    def parse_arguments_improved(self, args: List[str]) -> ParsedArgs:
        """改进的参数解析"""
        result = ParsedArgs()
        
        # 先用 argparse 处理我们自己的选项
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('--no-memory', action='store_true', help='禁用记忆功能')
        parser.add_argument('--clear-memory', action='store_true', help='清除所有记忆')
        parser.add_argument('--memory-stats', action='store_true', help='显示记忆统计')
        # 注意：--verbose 是 Claude 的选项，不是 Sage 的
        
        # 解析已知参数
        sage_args, remaining = parser.parse_known_args(args)
        
        # 更新 sage 选项
        result.sage_options = {
            'no_memory': sage_args.no_memory,
            'clear_memory': sage_args.clear_memory,
            'memory_stats': sage_args.memory_stats
        }
        
        # 处理特殊命令
        if sage_args.clear_memory:
            self._handle_clear_memory()
            sys.exit(0)
        
        if sage_args.memory_stats:
            self._handle_memory_stats()
            sys.exit(0)
        
        # 解析剩余的 Claude 参数
        i = 0
        while i < len(remaining):
            arg = remaining[i]
            
            if arg in self.CLAUDE_OPTIONS_WITH_VALUE:
                # 需要值的选项
                result.claude_args.append(arg)
                if i + 1 < len(remaining):
                    result.claude_args.append(remaining[i + 1])
                    i += 2
                else:
                    i += 1
            elif arg in self.CLAUDE_FLAGS or arg.startswith('-'):
                # 标志或未知选项
                result.claude_args.append(arg)
                i += 1
            else:
                # 第一个非选项参数是提示
                if result.user_prompt is None:
                    result.user_prompt = arg
                else:
                    # 后续的非选项参数
                    result.claude_args.append(arg)
                i += 1
        
        return result
    
    def execute_with_capture(self, claude_path: str, parsed_args: ParsedArgs) -> Tuple[int, str]:
        """执行 Claude 并捕获完整响应"""
        # 构建命令 - 使用新的命令解析器
        if ' ' in claude_path:
            # 如果路径包含空格，说明是一个命令（如 "python3 script.py"）
            command = self.command_parser.parse_command(claude_path) + parsed_args.claude_args
        else:
            command = [claude_path] + parsed_args.claude_args
        
        # 检查是否使用 -p 模式
        use_print_mode = False
        input_text = None
        
        if parsed_args.user_prompt:
            if '-p' in command or '--print' in command:
                # 已经有 -p 参数，通过 stdin 传递输入
                use_print_mode = True
                input_text = parsed_args.user_prompt
            else:
                # 没有 -p 参数，自动添加并通过 stdin 传递
                command.insert(1, '-p')
                use_print_mode = True
                input_text = parsed_args.user_prompt
        
        logger.info(f"执行命令: {' '.join(command[:3])}...")
        
        # 创建进程 - 使用新的进程启动器
        try:
            # 如果使用 print 模式，使用 communicate 方法
            if use_print_mode and input_text:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=self.process_launcher.prepare_environment({
                        'PYTHONIOENCODING': 'utf-8',
                        # 'SAGE_RECURSION_GUARD': '1'  # 已废弃，使用命令行参数
                    })
                )
                
                stdout, stderr = process.communicate(input=input_text + '\n', timeout=60)
                
                # 显示输出
                if stdout:
                    sys.stdout.write(stdout)
                    sys.stdout.flush()
                if stderr:
                    sys.stderr.write(stderr)
                    sys.stderr.flush()
                
                return process.returncode, stdout
            
            else:
                # 非 print 模式，使用原来的线程方式
                process = self.process_launcher.create_process(
                    command,
                    env={
                        'PYTHONIOENCODING': 'utf-8',
                        # 'SAGE_RECURSION_GUARD': '1'  # 已废弃，使用命令行参数
                    }
                )
                
                # 使用线程分别处理 stdout 和 stderr
                stdout_thread = threading.Thread(
                    target=self._capture_stream,
                    args=(process.stdout, False),
                    name="SageStdoutCapture"
                )
                stderr_thread = threading.Thread(
                    target=self._capture_stream,
                    args=(process.stderr, True),
                    name="SageStderrCapture"
                )
                
                # 跟踪线程和进程
                self._active_threads.add(stdout_thread)
                self._active_threads.add(stderr_thread)
                self._active_processes.add(process)
                
                stdout_thread.start()
                stderr_thread.start()
                
                # 等待进程完成
                return_code = process.wait()
                
                # 等待线程完成
                stdout_thread.join(timeout=5)
                stderr_thread.join(timeout=5)
                
                # 获取完整响应
                with self.response_lock:
                    full_response = ''.join(self.response_collector)
                
                return return_code, full_response
            
        except FileNotFoundError as e:
            raise ClaudeNotFoundError(searched_paths=[claude_path])
        except OSError as e:
            raise ClaudeExecutionError(
                f"启动 Claude 失败: {e}",
                command=' '.join(command[:3]) + '...',
                error=str(e)
            )
            print(error_msg, file=sys.stderr)
            return 1, ""
        except (subprocess.SubprocessError, RuntimeError) as e:
            error_msg = f"执行 Claude 时发生错误: {e}"
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            return 1, ""
    
    def _safe_subprocess_call(self, command: List[str]) -> int:
        """安全地调用子进程，设置递归保护（阶段4稳定版本）"""
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # 为Claude调用设置递归保护（仅为子进程临时设置）
        # 这是正确的实现：环境变量仅在子进程生命周期内存在
        if any('claude' in str(cmd) for cmd in command):
            env['SAGE_RECURSION_GUARD'] = '1'
        
        return subprocess.call(command, env=env)
    
    def _capture_stream(self, stream, is_stderr: bool):
        """捕获输出流"""
        try:
            for line in iter(stream.readline, ''):
                if not line:
                    break
                
                # 检查内存使用
                exceeded, current, limit = self._resource_monitor.check_memory()
                if exceeded:
                    logger.warning(f"内存使用超限: {current/1024/1024:.1f}MB / {limit/1024/1024:.1f}MB")
                
                # 实时显示
                if is_stderr:
                    sys.stderr.write(line)
                    sys.stderr.flush()
                else:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                
                # 保存输出（只保存 stdout）
                if not is_stderr:
                    with self.response_lock:
                        self.response_collector.append(line)
        except (IOError, OSError) as e:
            logger.error(f"捕获流时出错: {e}")
        finally:
            try:
                stream.close()
            except:
                pass
    
    def _handle_clear_memory(self):
        """处理清除记忆命令"""
        try:
            # 确认操作
            response = input("确定要清除所有记忆吗？(yes/no): ")
            if response.lower() == 'yes':
                count = self.memory_provider.clear_all_memories()
                print(f"✅ 已清除 {count} 条记忆")
            else:
                print("❌ 操作已取消")
        except (MemoryProviderError, IOError) as e:
            print(f"❌ 清除记忆失败: {e}")
    
    def _handle_memory_stats(self):
        """处理记忆统计命令"""
        try:
            stats = self.memory_provider.get_memory_stats()
            print("\n🧠 Sage 记忆系统统计")
            print("=" * 40)
            print(f"总记忆数: {stats.get('total', 0)}")
            print(f"今日新增: {stats.get('today', 0)}")
            print(f"本周活跃: {stats.get('this_week', 0)}")
            print(f"存储大小: {stats.get('size_mb', 0):.2f} MB")
            print("=" * 40)
        except (MemoryProviderError, AttributeError) as e:
            print(f"❌ 获取统计失败: {e}")
    
    def print_memory_hint(self, message: str, contexts_found: int = 0):
        """打印记忆系统提示"""
        if not self.get_config('show_memory_hints', True):
            return
        
        # 颜色映射
        colors = {
            'cyan': '\033[96m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'red': '\033[91m'
        }
        
        color = colors.get(self.get_config('memory_hint_color', 'cyan'), '\033[96m')
        reset = '\033[0m'
        
        # 构建消息
        if contexts_found > 0:
            icon = "🔍"
            msg = f"{icon} 找到 {contexts_found} 条相关记忆"
        else:
            icon = "💭"
            msg = f"{icon} {message}"
        
        # 输出到 stderr
        print(f"{color}[Sage] {msg}{reset}", file=sys.stderr)
    
    def run_with_memory(self, parsed_args: ParsedArgs) -> int:
        """带记忆功能运行（支持同步调用异步增强）"""
        try:
            # 使用新的事件循环管理器
            return self.async_manager.run_coroutine(
                self._run_with_memory_async(parsed_args)
            )
        except AsyncRuntimeError as e:
            logger.error(f"异步运行时错误: {e}")
            # 降级到同步模式
            return self._run_with_memory_sync(parsed_args)
        except Exception as e:
            logger.error(f"异步运行失败: {e}")
            # 降级到同步模式
            return self._run_with_memory_sync(parsed_args)
    
    async def _run_with_memory_async(self, parsed_args: ParsedArgs) -> int:
        """异步记忆运行（阶段2）"""
        # 查找 Claude
        claude_path = self.find_claude_executable()
        if not claude_path:
            print("❌ 错误：未找到 Claude CLI", file=sys.stderr)
            print("请访问 https://claude.ai 安装", file=sys.stderr)
            return 1
        
        logger.info(f"找到 Claude: {claude_path}")
        
        # 如果没有用户输入，直接传递
        if not parsed_args.user_prompt:
            if ' ' in claude_path:
                command = self.command_parser.parse_command(claude_path) + parsed_args.claude_args
            else:
                command = [claude_path] + parsed_args.claude_args
            return self._safe_subprocess_call(command)
        
        # 检查记忆模块可用性
        try:
            # 测试记忆提供者是否可用
            _ = self.memory_provider
        except (MemoryProviderError, ImportError, AttributeError) as e:
            logger.error(f"记忆模块不可用: {e}")
            self.print_memory_hint("记忆模块不可用，使用标准模式")
            if ' ' in claude_path:
                command = self.command_parser.parse_command(claude_path) + parsed_args.claude_args + [parsed_args.user_prompt]
            else:
                command = [claude_path] + parsed_args.claude_args + [parsed_args.user_prompt]
            return self._safe_subprocess_call(command)
        
        # 检查是否禁用记忆
        if parsed_args.sage_options.get('no_memory') or not self.get_config('memory_enabled', True):
            self.print_memory_hint("记忆功能已禁用")
            if ' ' in claude_path:
                command = self.command_parser.parse_command(claude_path) + parsed_args.claude_args + [parsed_args.user_prompt]
            else:
                command = [claude_path] + parsed_args.claude_args + [parsed_args.user_prompt]
            return self._safe_subprocess_call(command)
        
        # 获取增强的提示（阶段2智能增强）
        try:
            if self._stage2_enabled and self.prompt_enhancer:
                # 使用阶段2智能增强
                enhancement_context = await self._perform_intelligent_enhancement(
                    parsed_args.user_prompt
                )
                enhanced_prompt = enhancement_context.enhanced_prompt
                
                # 显示增强信息
                if enhancement_context.fragments_used:
                    self.print_memory_hint(
                        f"智能增强 (置信度: {enhancement_context.confidence_score:.2f})",
                        contexts_found=len(enhancement_context.fragments_used)
                    )
                else:
                    self.print_memory_hint("智能分析 - 无需增强")
                    
            else:
                # 降级到阶段1简单增强
                context = self.memory_provider.get_context(parsed_args.user_prompt)
                
                if context:
                    enhanced_prompt = f"{context}\n\n当前查询：{parsed_args.user_prompt}"
                    self.print_memory_hint("使用记忆增强", contexts_found=1)
                else:
                    enhanced_prompt = parsed_args.user_prompt
                    self.print_memory_hint("未找到相关记忆")
            
            # 修改参数以使用增强提示
            parsed_args_copy = ParsedArgs(
                user_prompt=enhanced_prompt,
                claude_args=parsed_args.claude_args[:],
                sage_options=parsed_args.sage_options.copy()
            )
            
        except (MemoryProviderError, RetrievalError, AttributeError) as e:
            logger.error(f"获取上下文失败: {e}")
            enhanced_prompt = parsed_args.user_prompt
            parsed_args_copy = parsed_args
        
        # 执行并捕获响应
        return_code, response = self.execute_with_capture(claude_path, parsed_args_copy)
        
        # 异步保存对话（如果成功）
        if return_code == 0 and response.strip():
            if self.get_config('async_save', True):
                # 异步保存
                save_thread = threading.Thread(
                    target=self._async_save_conversation,
                    args=(parsed_args.user_prompt, response),
                    daemon=True,
                    name="SageAsyncSave"
                )
                self._active_threads.add(save_thread)
                save_thread.start()
            else:
                # 同步保存
                try:
                    self.memory_provider.save_conversation(parsed_args.user_prompt, response)
                    logger.info("对话已保存")
                except (MemoryProviderError, IOError) as e:
                    logger.error(f"保存对话失败: {e}")
        
        return return_code
    
    @monitor_performance("intelligent_enhancement")
    async def _perform_intelligent_enhancement(self, user_prompt: str):
        """执行智能提示增强（阶段2）"""
        # 尝试使用缓存
        if query_cache and hasattr(query_cache, 'get'):
            cache_key = query_cache._make_key("enhance", user_prompt)
            cached_result = query_cache.get(cache_key)
            if cached_result:
                logger.debug("使用缓存的增强结果")
                return cached_result
        
        try:
            # 获取会话历史（简化版）
            session_history = []
            
            # 执行智能增强
            enhancement_context = await self.prompt_enhancer.enhance_prompt(
                original_prompt=user_prompt,
                enhancement_level=EnhancementLevel.ADAPTIVE,
                session_history=session_history
            )
            
            # 缓存结果
            if query_cache and hasattr(query_cache, 'set'):
                query_cache.set(cache_key, enhancement_context)
            
            return enhancement_context
            
        except (EnhancementError, RetrievalError, AttributeError) as e:
            logger.error(f"智能增强失败: {e}")
            # 返回基础增强上下文
            from prompt_enhancer import EnhancementContext
            return EnhancementContext(
                original_prompt=user_prompt,
                enhanced_prompt=user_prompt,
                fragments_used=[],
                enhancement_reasoning="增强失败，使用原始提示",
                metadata={},
                confidence_score=0.0
            )
    
    def _run_with_memory_sync(self, parsed_args: ParsedArgs) -> int:
        """同步记忆运行（阶段1兼容）"""
        # 查找 Claude
        claude_path = self.find_claude_executable()
        if not claude_path:
            print("❌ 错误：未找到 Claude CLI", file=sys.stderr)
            print("请访问 https://claude.ai 安装", file=sys.stderr)
            return 1
        
        logger.info(f"找到 Claude: {claude_path}")
        
        # 如果没有用户输入，直接传递
        if not parsed_args.user_prompt:
            if ' ' in claude_path:
                command = self.command_parser.parse_command(claude_path) + parsed_args.claude_args
            else:
                command = [claude_path] + parsed_args.claude_args
            return self._safe_subprocess_call(command)
        
        # 检查记忆模块可用性
        try:
            # 测试记忆提供者是否可用
            _ = self.memory_provider
        except (MemoryProviderError, ImportError, AttributeError) as e:
            logger.error(f"记忆模块不可用: {e}")
            self.print_memory_hint("记忆模块不可用，使用标准模式")
            if ' ' in claude_path:
                command = self.command_parser.parse_command(claude_path) + parsed_args.claude_args + [parsed_args.user_prompt]
            else:
                command = [claude_path] + parsed_args.claude_args + [parsed_args.user_prompt]
            return self._safe_subprocess_call(command)
        
        # 检查是否禁用记忆
        if parsed_args.sage_options.get('no_memory') or not self.get_config('memory_enabled', True):
            self.print_memory_hint("记忆功能已禁用")
            if ' ' in claude_path:
                command = self.command_parser.parse_command(claude_path) + parsed_args.claude_args + [parsed_args.user_prompt]
            else:
                command = [claude_path] + parsed_args.claude_args + [parsed_args.user_prompt]
            return self._safe_subprocess_call(command)
        
        # 获取增强的提示（阶段1简单模式）
        try:
            context = self.memory_provider.get_context(parsed_args.user_prompt)
            
            if context:
                enhanced_prompt = f"{context}\n\n当前查询：{parsed_args.user_prompt}"
                self.print_memory_hint("使用记忆增强", contexts_found=1)
            else:
                enhanced_prompt = parsed_args.user_prompt
                self.print_memory_hint("未找到相关记忆")
            
            # 修改参数以使用增强提示
            parsed_args_copy = ParsedArgs(
                user_prompt=enhanced_prompt,
                claude_args=parsed_args.claude_args[:],
                sage_options=parsed_args.sage_options.copy()
            )
            
        except (MemoryProviderError, RetrievalError, AttributeError) as e:
            logger.error(f"获取上下文失败: {e}")
            enhanced_prompt = parsed_args.user_prompt
            parsed_args_copy = parsed_args
        
        # 执行并捕获响应
        return_code, response = self.execute_with_capture(claude_path, parsed_args_copy)
        
        # 异步保存对话（如果成功）
        if return_code == 0 and response.strip():
            if self.get_config('async_save', True):
                # 异步保存
                save_thread = threading.Thread(
                    target=self._async_save_conversation,
                    args=(parsed_args.user_prompt, response),
                    daemon=True,
                    name="SageAsyncSave"
                )
                self._active_threads.add(save_thread)
                save_thread.start()
            else:
                # 同步保存
                try:
                    self.memory_provider.save_conversation(parsed_args.user_prompt, response)
                    logger.info("对话已保存")
                except (MemoryProviderError, IOError) as e:
                    logger.error(f"保存对话失败: {e}")
        
        return return_code
    
    def _async_save_conversation(self, prompt: str, response: str):
        """异步保存对话"""
        try:
            self.memory_provider.save_conversation(prompt, response)
            logger.info("对话已异步保存")
        except (MemoryProviderError, IOError) as e:
            logger.error(f"异步保存失败: {e}")
    
    def _cleanup_resources(self):
        """清理所有资源"""
        logger.info("开始清理资源")
        
        # 1. 清理响应收集器
        with self.response_lock:
            self.response_collector.clear()
        
        # 2. 终止活动线程
        for thread in list(self._active_threads):
            if thread.is_alive():
                logger.debug(f"等待线程 {thread.name} 结束")
                thread.join(timeout=2.0)
                if thread.is_alive():
                    logger.warning(f"线程 {thread.name} 未能在2秒内结束")
        
        # 3. 终止活动进程
        for process in list(self._active_processes):
            try:
                if process.poll() is None:  # 进程仍在运行
                    logger.debug(f"终止进程 PID={process.pid}")
                    process.terminate()
                    process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                logger.warning(f"进程 PID={process.pid} 未能正常终止，强制结束")
                try:
                    process.kill()
                except:
                    pass
            except (subprocess.SubprocessError, OSError) as e:
                logger.error(f"清理进程时出错: {e}")
        
        # 4. 清理异步事件循环
        try:
            self.async_manager.cleanup()
        except (AsyncRuntimeError, AttributeError) as e:
            logger.error(f"清理异步管理器时出错: {e}")
        
        # 5. 清理记忆提供者资源
        if self._memory_provider:
            try:
                # 如果记忆提供者有cleanup方法，调用它
                if hasattr(self._memory_provider, 'cleanup'):
                    self._memory_provider.cleanup()
            except (MemoryProviderError, AttributeError) as e:
                logger.error(f"清理记忆提供者时出错: {e}")
        
        # 6. 记录资源使用统计
        try:
            stats = self._resource_monitor.get_resource_stats()
            logger.info(f"资源使用统计: {stats}")
        except (AttributeError, OSError) as e:
            logger.error(f"获取资源统计时出错: {e}")
        
        logger.info("资源清理完成")
    
    @monitor_performance("main_run")
    def run(self, args: List[str]) -> int:
        """主运行函数"""
        try:
            # 解析参数
            parsed_args = self.parse_arguments_improved(args)
            
            # 根据配置决定是否使用记忆
            if self.get_config('memory_enabled', True) and not parsed_args.sage_options.get('no_memory'):
                return self.run_with_memory(parsed_args)
            else:
                # 直接运行
                claude_path = self.find_claude_executable()
                if not claude_path:
                    print("❌ 错误：未找到 Claude CLI", file=sys.stderr)
                    return 1
                
                if ' ' in claude_path:
                    command = self.command_parser.parse_command(claude_path) + parsed_args.claude_args
                else:
                    command = [claude_path] + parsed_args.claude_args
                
                if parsed_args.user_prompt:
                    command.append(parsed_args.user_prompt)
                
                return self._safe_subprocess_call(command)
                
        except KeyboardInterrupt:
            print("\n操作已取消", file=sys.stderr)
            return 130
        except SageBaseException as e:
            # 处理我们自定义的异常
            logger.error(f"Sage错误: {e}")
            print(f"❌ {e}", file=sys.stderr)
            return 1
        except Exception as e:
            # 处理未预期的错误
            logger.exception("未预期的错误")
            print(f"❌ 错误：{e}", file=sys.stderr)
            return 1

def main():
    """主入口"""
    # 递归保护已经在文件开头检查过了，这里不需要再设置
    # 否则会导致每次运行都被认为是递归调用
    
    app = ImprovedCrossplatformClaude()
    return app.run(sys.argv[1:])

if __name__ == "__main__":
    sys.exit(main())