#!/usr/bin/env python3
"""
Sage MCP 跨平台记忆系统
支持 Windows、macOS、Linux
"""

import sys
import os
import subprocess
import platform
import json
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
import logging
from datetime import datetime

# 配置日志
log_dir = Path.home() / '.sage-mcp' / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"sage-mcp-{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CrossPlatformClaude:
    """跨平台的 Claude 记忆系统"""
    
    def __init__(self):
        self.platform = platform.system()
        self.is_windows = self.platform == 'Windows'
        self.is_macos = self.platform == 'Darwin'
        self.is_linux = self.platform == 'Linux'
        
        # 使用 pathlib 处理路径，自动适配不同平台
        self.config_dir = Path.home() / '.sage-mcp'
        self.config_file = self.config_dir / 'config.json'
        self.recursion_guard_file = self.config_dir / '.recursion_guard'
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self.config = self.load_config()
        
    def load_config(self) -> dict:
        """加载配置文件"""
        default_config = {
            'claude_paths': [],  # 可能的 Claude 路径列表
            'memory_enabled': True,
            'debug_mode': False,
            'api_key': os.getenv('SILICONFLOW_API_KEY'),
            'db_config': {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'mem'),
                'user': os.getenv('DB_USER', 'mem'),
                'password': os.getenv('DB_PASSWORD', 'mem')
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"配置文件读取失败: {e}")
                
        return default_config
        
    def find_claude_executable(self) -> Optional[str]:
        """跨平台查找 Claude 可执行文件"""
        # 1. 检查配置中的路径
        for path in self.config.get('claude_paths', []):
            if Path(path).exists():
                return str(path)
                
        # 2. 检查环境变量
        claude_env = os.getenv('CLAUDE_CLI_PATH')
        if claude_env and Path(claude_env).exists():
            return claude_env
            
        # 3. 平台特定的搜索
        if self.is_windows:
            # Windows 特定搜索
            possible_paths = [
                Path.home() / 'AppData' / 'Local' / 'Claude' / 'claude.exe',
                Path('C:/Program Files/Claude/claude.exe'),
                Path('C:/Program Files (x86)/Claude/claude.exe'),
            ]
            
            # 检查 PATH 中的 claude.exe
            claude_in_path = shutil.which('claude.exe')
            if claude_in_path:
                return claude_in_path
                
        else:
            # Unix-like 系统
            possible_paths = [
                Path('/usr/local/bin/claude'),
                Path('/usr/bin/claude'),
                Path.home() / '.local' / 'bin' / 'claude',
                Path.home() / '.claude' / 'local' / 'claude',
            ]
            
            # 检查 PATH
            claude_in_path = shutil.which('claude')
            if claude_in_path:
                return claude_in_path
                
        # 4. 检查预定义路径
        for path in possible_paths:
            if path.exists():
                return str(path)
                
        return None
        
    def check_recursion_guard(self) -> bool:
        """检查递归保护"""
        if self.recursion_guard_file.exists():
            # 如果保护文件存在，说明可能在递归中
            logger.warning("检测到可能的递归调用")
            return False
            
        # 创建保护文件
        self.recursion_guard_file.touch()
        return True
        
    def clear_recursion_guard(self):
        """清除递归保护"""
        if self.recursion_guard_file.exists():
            self.recursion_guard_file.unlink()
            
    def parse_claude_arguments(self, args: List[str]) -> Tuple[List[str], Optional[str]]:
        """智能解析 Claude 命令行参数"""
        claude_args = []
        user_input = None
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            # 处理带参数的选项
            if arg in ['-m', '--model', '-t', '--temperature', '-o', '--output']:
                claude_args.extend([arg, args[i+1]] if i+1 < len(args) else [arg])
                i += 2
                continue
                
            # 处理标志选项
            if arg.startswith('-'):
                claude_args.append(arg)
                i += 1
                continue
                
            # 第一个非选项参数通常是用户输入
            if user_input is None:
                user_input = arg
            else:
                claude_args.append(arg)
                
            i += 1
            
        return claude_args, user_input
        
    def execute_with_memory(self, claude_path: str, args: List[str]) -> int:
        """执行带记忆功能的 Claude"""
        try:
            # 解析参数
            claude_args, user_input = self.parse_claude_arguments(args)
            
            if not user_input:
                # 没有用户输入，直接传递
                return subprocess.call([claude_path] + args)
                
            # 导入记忆模块
            try:
                from memory import get_context, save_memory
            except ImportError as e:
                logger.error(f"记忆模块导入失败: {e}")
                return self.execute_without_memory(claude_path, args)
                
            # 获取上下文
            context = get_context(user_input)
            
            # 构造增强提示
            if context:
                enhanced_prompt = f"{context}\n\n当前查询：{user_input}"
            else:
                enhanced_prompt = user_input
                
            # 构建完整命令
            full_command = [claude_path] + claude_args
            
            # 替换用户输入
            for i, arg in enumerate(full_command):
                if arg == user_input:
                    full_command[i] = enhanced_prompt
                    break
            else:
                # 如果没找到，添加到末尾
                full_command.append(enhanced_prompt)
                
            # 执行命令
            logger.info(f"执行命令: {' '.join(full_command[:2])}...")
            
            if self.is_windows:
                # Windows 特殊处理
                process = subprocess.Popen(
                    full_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            else:
                process = subprocess.Popen(
                    full_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
            # 收集输出
            full_output = []
            for line in process.stdout:
                print(line, end='')
                full_output.append(line)
                
            process.wait()
            
            # 保存记忆
            claude_response = ''.join(full_output)
            save_memory(user_input, claude_response)
            
            return process.returncode
            
        except Exception as e:
            logger.error(f"记忆系统执行失败: {e}")
            return self.execute_without_memory(claude_path, args)
            
    def execute_without_memory(self, claude_path: str, args: List[str]) -> int:
        """不带记忆功能执行 Claude"""
        logger.info("降级到标准 Claude 模式")
        return subprocess.call([claude_path] + args)
        
    def run(self, args: List[str]) -> int:
        """主运行函数"""
        # 检查递归保护
        if not self.check_recursion_guard():
            logger.error("检测到递归调用，退出")
            return 1
            
        try:
            # 查找 Claude 可执行文件
            claude_path = self.find_claude_executable()
            
            if not claude_path:
                logger.error("未找到 Claude CLI，请安装后重试")
                print("错误：未找到 Claude CLI")
                print("请访问 https://claude.ai/cli 安装")
                return 1
                
            logger.info(f"找到 Claude: {claude_path}")
            
            # 根据配置决定是否使用记忆功能
            if self.config.get('memory_enabled', True):
                return self.execute_with_memory(claude_path, args)
            else:
                return self.execute_without_memory(claude_path, args)
                
        finally:
            # 清理递归保护
            self.clear_recursion_guard()

def main():
    """主入口"""
    try:
        app = CrossPlatformClaude()
        return app.run(sys.argv[1:])
    except KeyboardInterrupt:
        print("\n操作已取消")
        return 130
    except Exception as e:
        logger.exception("未预期的错误")
        print(f"错误：{e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())