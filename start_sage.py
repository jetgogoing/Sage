#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sage MCP 跨平台启动器
支持 Windows / macOS / Linux 统一启动体验
"""

import os
import sys
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """动态获取项目根目录"""
    return Path(__file__).parent


def load_env_file() -> bool:
    """安全地加载.env文件中的环境变量"""
    env_file = get_project_root() / '.env'
    
    if not env_file.exists():
        print(f"警告: .env文件不存在于 {env_file}")
        print("请从.env.example复制并配置必要的环境变量")
        return False
    
    # 使用python-dotenv安全解析，如果不可用则降级
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
        return True
    except ImportError:
        print("警告: python-dotenv未安装，使用安全的备用解析器")
        # 安全的.env文件解析 - 仅允许已知变量
        allowed_vars = {
            'SAGE_LOG_DIR', 'SAGE_MAX_RESULTS', 'SAGE_SIMILARITY_THRESHOLD',
            'SILICONFLOW_API_KEY', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 
            'DB_NAME', 'DB_USER', 'EMBEDDING_MODEL', 'EMBEDDING_DEVICE'
        }
        
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' not in line:
                        continue
                    
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    # 仅设置已知安全的环境变量
                    if key in allowed_vars:
                        os.environ[key] = value
                    else:
                        print(f"警告: 跳过未知环境变量 {key} (行 {line_num})")
            return True
        except Exception as e:
            print(f"加载.env文件失败: {e}")
            return False


def check_docker() -> bool:
    """检查Docker是否可用"""
    try:
        result = subprocess.run(['docker', 'info'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_database() -> bool:
    """启动PostgreSQL数据库容器"""
    project_root = get_project_root()
    compose_file = project_root / 'docker-compose-db.yml'
    
    if not compose_file.exists():
        print(f"错误: Docker Compose文件不存在: {compose_file}")
        return False
    
    print("检查Docker环境...")
    if not check_docker():
        print("错误: Docker未运行，请先启动Docker Desktop")
        return False
    
    # 检查容器是否已存在
    try:
        result = subprocess.run(['docker', 'ps', '-a', '--filter', 'name=sage-db'], 
                              capture_output=True, text=True)
        
        if 'sage-db' not in result.stdout:
            print("创建PostgreSQL容器...")
            subprocess.run(['docker-compose', '-f', str(compose_file), 'up', '-d'], 
                          cwd=project_root, check=True)
            time.sleep(5)
        else:
            # 检查容器是否运行中
            result = subprocess.run(['docker', 'ps', '--filter', 'name=sage-db'], 
                                  capture_output=True, text=True)
            if 'sage-db' not in result.stdout:
                print("启动现有PostgreSQL容器...")
                subprocess.run(['docker', 'start', 'sage-db'], check=True)
                time.sleep(3)
        
        # 等待数据库就绪
        print("等待PostgreSQL就绪...")
        for i in range(30):
            result = subprocess.run(['docker', 'exec', 'sage-db', 
                                   'pg_isready', '-U', 'sage', '-d', 'sage_memory'], 
                                  capture_output=True)
            if result.returncode == 0:
                print("PostgreSQL已就绪!")
                return True
            time.sleep(1)
        
        print("警告: PostgreSQL在30秒内未就绪")
        return False
        
    except subprocess.CalledProcessError as e:
        print(f"启动数据库失败: {e}")
        return False


def setup_environment():
    """设置运行环境"""
    project_root = get_project_root()
    
    # 设置环境变量
    os.environ['SAGE_LOG_DIR'] = str(project_root / 'logs')
    os.environ['PYTHONPATH'] = str(project_root)
    
    # 创建日志目录
    logs_dir = Path(os.environ['SAGE_LOG_DIR'])
    logs_dir.mkdir(exist_ok=True)
    
    # 加载.env文件
    load_env_file()


def start_sage_service():
    """启动Sage MCP服务"""
    project_root = get_project_root()
    sage_script = project_root / 'sage_mcp_stdio_single.py'
    
    if not sage_script.exists():
        print(f"错误: Sage MCP脚本不存在: {sage_script}")
        return False
    
    # 获取Python解释器
    python_exe = sys.executable
    
    print("启动Sage MCP Server...")
    print(f"Python解释器: {python_exe}")
    print(f"脚本路径: {sage_script}")
    print(f"平台: {platform.system()}")
    
    try:
        # 使用exec替换当前进程，保持stdio连接
        os.execv(python_exe, [python_exe, str(sage_script)])
    except OSError as e:
        print(f"启动Sage服务失败 - OS错误: {e}")
        print(f"检查Python解释器路径: {python_exe}")
        print(f"检查脚本文件权限: {sage_script}")
        return False
    except Exception as e:
        print(f"启动Sage服务失败 - 未知错误: {e}")
        print("建议检查:")
        print("1. Python解释器是否有效")
        print("2. 脚本文件是否存在且可执行")
        print("3. 系统资源是否充足")
        return False


def validate_configuration():
    """验证关键配置"""
    required_vars = ['DB_PASSWORD']
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"错误: 缺少必需的环境变量: {missing}")
        print("请检查.env文件配置")
        return False
    
    return True


def main():
    """主启动流程"""
    print("=" * 60)
    print("Sage MCP 跨平台启动器")
    print(f"平台: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print("=" * 60)
    
    # 设置环境
    setup_environment()
    
    # 验证配置
    if not validate_configuration():
        sys.exit(1)
    
    # 启动数据库
    if not start_database():
        print("警告: 数据库启动失败，某些功能可能受限")
    
    # 启动Sage服务
    start_sage_service()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断，服务停止")
        sys.exit(0)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)