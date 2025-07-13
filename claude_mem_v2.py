#!/usr/bin/env python3
"""
Sage MCP 轻量化记忆系统 - Claude CLI 注入器 V2
增强版：包含完整的自检系统
"""

import sys
import os
import subprocess
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
import requests

# 自检系统版本
SELF_CHECK_VERSION = "2.0"

# ANSI 颜色代码
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# 错误代码定义
class ErrorCodes:
    # 1xx: 环境错误
    PYTHON_VERSION = 101
    CLAUDE_NOT_FOUND = 102
    DOCKER_NOT_RUNNING = 103
    
    # 2xx: 配置错误
    ENV_FILE_MISSING = 201
    API_KEY_MISSING = 202
    CLAUDE_PATH_INVALID = 203
    
    # 3xx: 数据库错误
    DB_CONNECTION_FAILED = 301
    DB_TABLE_MISSING = 302
    PGVECTOR_NOT_INSTALLED = 303
    
    # 4xx: API错误
    API_CONNECTION_FAILED = 401
    API_KEY_INVALID = 402
    API_QUOTA_EXCEEDED = 403
    
    # 5xx: 文件系统错误
    MEMORY_SCRIPT_NOT_FOUND = 501
    PERMISSION_DENIED = 502
    DISK_SPACE_LOW = 503

class SelfCheck:
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.errors = []
        self.warnings = []
        self.start_time = time.time()
        
    def print_header(self):
        """打印自检头部"""
        print(f"\n{Colors.BOLD}=== Sage MCP 记忆系统自检 v{SELF_CHECK_VERSION} ==={Colors.RESET}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"系统: {sys.platform}")
        print("-" * 50)
        
    def print_check(self, status, message, detail=None):
        """打印检查结果"""
        if status == "pass":
            print(f"{Colors.GREEN}[✓]{Colors.RESET} {message}")
            self.checks_passed += 1
        elif status == "fail":
            print(f"{Colors.RED}[✗]{Colors.RESET} {message}")
            self.checks_failed += 1
            if detail:
                print(f"    {Colors.RED}└─ {detail}{Colors.RESET}")
        elif status == "warn":
            print(f"{Colors.YELLOW}[!]{Colors.RESET} {message}")
            if detail:
                print(f"    {Colors.YELLOW}└─ {detail}{Colors.RESET}")
            self.warnings.append(message)
        else:  # info
            print(f"{Colors.BLUE}[i]{Colors.RESET} {message}")
            
    def check_python_version(self):
        """检查 Python 版本"""
        self.print_check("info", "检查 Python 环境...")
        version = sys.version_info
        if version.major >= 3 and version.minor >= 7:
            self.print_check("pass", f"Python 版本: {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            self.print_check("fail", f"Python 版本过低: {version.major}.{version.minor}", 
                           "需要 Python 3.7 或更高版本")
            self.errors.append((ErrorCodes.PYTHON_VERSION, "Python 版本不符合要求"))
            return False
            
    def check_env_file(self):
        """检查环境变量文件"""
        self.print_check("info", "检查环境配置...")
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        
        if os.path.exists(env_path):
            load_dotenv()
            self.print_check("pass", f"环境文件: {env_path}")
            
            # 检查必需的环境变量
            api_key = os.getenv('SILICONFLOW_API_KEY')
            if api_key:
                self.print_check("pass", "API 密钥: 已配置")
            else:
                self.print_check("fail", "API 密钥: 未设置", 
                               "请在 .env 文件中设置 SILICONFLOW_API_KEY")
                self.errors.append((ErrorCodes.API_KEY_MISSING, "API 密钥未配置"))
                return False
                
            # 检查 Claude 路径
            claude_path = os.getenv('CLAUDE_CLI_PATH')
            if claude_path and os.path.exists(claude_path):
                self.print_check("pass", f"Claude 路径: {claude_path}")
            else:
                self.print_check("warn", f"Claude 路径未验证: {claude_path}", 
                               "将使用系统 PATH 查找")
            return True
        else:
            self.print_check("fail", "环境文件: 未找到", 
                           f"请创建 {env_path} 文件")
            self.errors.append((ErrorCodes.ENV_FILE_MISSING, "环境文件缺失"))
            return False
            
    def check_claude_cli(self):
        """检查 Claude CLI"""
        self.print_check("info", "检查 Claude CLI...")
        
        # 首先尝试环境变量中的路径
        claude_path = os.getenv('CLAUDE_CLI_PATH')
        if claude_path and os.path.exists(claude_path):
            self.print_check("pass", f"Claude CLI: {claude_path}")
            return True
            
        # 然后尝试 which 命令
        try:
            result = subprocess.run(['which', 'claude'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                claude_path = result.stdout.strip()
                self.print_check("pass", f"Claude CLI: {claude_path}")
                return True
        except:
            pass
            
        self.print_check("fail", "Claude CLI: 未找到", 
                       "请安装 Claude CLI 或设置 CLAUDE_CLI_PATH")
        self.errors.append((ErrorCodes.CLAUDE_NOT_FOUND, "Claude CLI 未安装"))
        return False
        
    def check_database(self):
        """检查数据库连接"""
        self.print_check("info", "检查数据库连接...")
        
        # 检查 Docker 是否运行
        try:
            result = subprocess.run(['docker', 'ps'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                self.print_check("fail", "Docker: 未运行", 
                               "请启动 Docker Desktop")
                self.errors.append((ErrorCodes.DOCKER_NOT_RUNNING, "Docker 未运行"))
                return False
                
            # 检查 PostgreSQL 容器
            if 'sage-pg-1' in result.stdout:
                self.print_check("pass", "PostgreSQL 容器: 运行中")
            else:
                self.print_check("warn", "PostgreSQL 容器: 未运行", 
                               "运行 docker-compose up -d 启动")
                return False
        except FileNotFoundError:
            self.print_check("fail", "Docker: 未安装", 
                           "请安装 Docker Desktop")
            return False
            
        # 尝试连接数据库
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'mem'),
                user=os.getenv('DB_USER', 'mem'),
                password=os.getenv('DB_PASSWORD', 'mem')
            )
            
            # 检查 pgvector 扩展
            with conn.cursor() as cur:
                cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
                if cur.fetchone():
                    self.print_check("pass", "pgvector 扩展: 已安装")
                else:
                    self.print_check("fail", "pgvector 扩展: 未安装")
                    self.errors.append((ErrorCodes.PGVECTOR_NOT_INSTALLED, "pgvector 扩展缺失"))
                    
                # 检查表是否存在
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'conversations'
                    )
                """)
                if cur.fetchone()[0]:
                    self.print_check("pass", "数据表: conversations 存在")
                else:
                    self.print_check("fail", "数据表: conversations 不存在")
                    self.errors.append((ErrorCodes.DB_TABLE_MISSING, "数据表缺失"))
                    
            conn.close()
            return True
            
        except psycopg2.OperationalError as e:
            self.print_check("fail", "数据库连接: 失败", str(e))
            self.errors.append((ErrorCodes.DB_CONNECTION_FAILED, "数据库连接失败"))
            return False
            
    def check_api_connection(self):
        """检查 API 连接"""
        self.print_check("info", "检查 SiliconFlow API...")
        
        api_key = os.getenv('SILICONFLOW_API_KEY')
        if not api_key:
            return False
            
        # 测试 API 连接
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 使用一个简单的测试请求
            response = requests.post(
                "https://api.siliconflow.cn/v1/embeddings",
                headers=headers,
                json={
                    "model": "Qwen/Qwen3-Embedding-8B",
                    "input": "test"
                },
                timeout=5
            )
            
            if response.status_code == 200:
                self.print_check("pass", "API 连接: 成功")
                return True
            elif response.status_code == 401:
                self.print_check("fail", "API 连接: 认证失败", 
                               "API 密钥无效")
                self.errors.append((ErrorCodes.API_KEY_INVALID, "API 密钥无效"))
                return False
            else:
                self.print_check("fail", f"API 连接: 错误 {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            self.print_check("warn", "API 连接: 超时", 
                           "网络可能较慢，但不影响基本功能")
            return True
        except Exception as e:
            self.print_check("fail", "API 连接: 失败", str(e))
            self.errors.append((ErrorCodes.API_CONNECTION_FAILED, "API 连接失败"))
            return False
            
    def check_disk_space(self):
        """检查磁盘空间"""
        self.print_check("info", "检查存储空间...")
        
        # 获取当前目录的磁盘使用情况
        stat = os.statvfs(os.path.dirname(__file__))
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        
        if free_gb > 1:
            self.print_check("pass", f"可用空间: {free_gb:.1f} GB")
            return True
        elif free_gb > 0.5:
            self.print_check("warn", f"可用空间: {free_gb:.1f} GB", 
                           "空间较少，建议清理")
            return True
        else:
            self.print_check("fail", f"可用空间: {free_gb:.1f} GB", 
                           "空间不足")
            self.errors.append((ErrorCodes.DISK_SPACE_LOW, "磁盘空间不足"))
            return False
            
    def print_summary(self):
        """打印自检摘要"""
        elapsed = time.time() - self.start_time
        print("-" * 50)
        
        if self.checks_failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ 自检完成 - 所有检查通过{Colors.RESET}")
            print(f"📊 统计: {self.checks_passed} 项通过, {len(self.warnings)} 个警告")
            print(f"⏱️  耗时: {elapsed:.2f} 秒")
            print(f"\n{Colors.GREEN}[成功] 记忆系统已就绪，开始进入 Claude...{Colors.RESET}\n")
            return True
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ 自检失败 - 发现问题{Colors.RESET}")
            print(f"📊 统计: {self.checks_passed} 项通过, {self.checks_failed} 项失败")
            
            if self.errors:
                print(f"\n{Colors.RED}错误详情:{Colors.RESET}")
                for code, desc in self.errors:
                    print(f"  [{code}] {desc}")
                    
            print(f"\n{Colors.YELLOW}建议:{Colors.RESET}")
            print("  1. 检查并修复上述错误")
            print("  2. 运行 ./install.sh 重新配置")
            print("  3. 查看文档: docs/USAGE_GUIDE.md")
            
            print(f"\n{Colors.RED}[失败] 降级到标准 Claude 模式{Colors.RESET}\n")
            return False

def run_self_check():
    """运行完整的自检流程"""
    checker = SelfCheck()
    checker.print_header()
    
    # 按重要性顺序执行检查
    checks = [
        checker.check_python_version,
        checker.check_env_file,
        checker.check_claude_cli,
        checker.check_database,
        checker.check_api_connection,
        checker.check_disk_space,
    ]
    
    for check in checks:
        check()
        time.sleep(0.1)  # 视觉效果
        
    return checker.print_summary()

# 原有的记忆系统代码
from memory import get_context, save_memory

def inject_memory_context(user_input):
    """主要的注入逻辑（保持原有功能）"""
    try:
        # 获取相关历史上下文
        context = get_context(user_input)
        
        # 构造增强的提示
        if context:
            enhanced_prompt = f"{context}\n\n当前查询：{user_input}"
        else:
            enhanced_prompt = user_input
            
        # 获取 Claude 路径
        claude_path = os.getenv('CLAUDE_CLI_PATH')
        if not claude_path:
            # 尝试从 PATH 中查找
            result = subprocess.run(['which', 'claude'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                claude_path = result.stdout.strip()
            else:
                raise FileNotFoundError("Claude CLI not found")
                
        # 调用原始 claude 命令
        cmd = [claude_path] + sys.argv[1:]
        
        # 替换用户输入为增强版本
        for i, arg in enumerate(cmd):
            if arg == user_input:
                cmd[i] = enhanced_prompt
                break
                
        # 执行命令并实时输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # 收集输出用于保存
        full_output = []
        
        # 实时输出并收集响应
        for line in process.stdout:
            print(line, end='')
            full_output.append(line)
            
        process.wait()
        
        # 保存完整对话到数据库
        claude_response = ''.join(full_output)
        save_memory(user_input, claude_response)
        
        # 打印保存状态
        print(f"\n{Colors.GREEN}[记忆系统] 对话已保存{Colors.RESET}")
        
        return process.returncode
        
    except Exception as e:
        print(f"\n{Colors.RED}[记忆系统] 错误: {e}{Colors.RESET}", file=sys.stderr)
        # 出错时直接调用原始命令
        claude_path = os.getenv('CLAUDE_CLI_PATH', 'claude')
        return subprocess.call([claude_path] + sys.argv[1:])

def main():
    """主入口：运行自检后执行记忆注入"""
    # 如果设置了快速模式，跳过自检
    if os.getenv('SAGE_SKIP_CHECK') == '1':
        print(f"{Colors.YELLOW}[记忆系统] 跳过自检（快速模式）{Colors.RESET}")
    else:
        # 运行自检
        if not run_self_check():
            # 自检失败，降级到原始 claude
            claude_path = os.getenv('CLAUDE_CLI_PATH', 'claude')
            return subprocess.call([claude_path] + sys.argv[1:])
    
    # 自检通过，继续原有逻辑
    if len(sys.argv) < 2:
        # 无参数时直接传递给原始 claude
        claude_path = os.getenv('CLAUDE_CLI_PATH', 'claude')
        return subprocess.call([claude_path])
        
    # 提取用户输入
    user_input = None
    for arg in reversed(sys.argv[1:]):
        if not arg.startswith('-'):
            user_input = arg
            break
            
    if user_input:
        return inject_memory_context(user_input)
    else:
        # 没有检测到查询内容，直接传递
        claude_path = os.getenv('CLAUDE_CLI_PATH', 'claude')
        return subprocess.call([claude_path] + sys.argv[1:])

if __name__ == "__main__":
    sys.exit(main())