"""
Sage 配置设置
集中管理所有配置项，支持环境变量和跨平台路径处理
"""

import os
import sys
from pathlib import Path

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 如果没有安装 python-dotenv，继续使用环境变量
    pass


def get_project_root():
    """智能检测项目根目录"""
    # 优先使用环境变量
    if os.getenv('SAGE_HOME'):
        return Path(os.getenv('SAGE_HOME')).resolve()
    
    # 其次使用当前文件位置推断
    current_file = Path(__file__).resolve()
    # config/settings.py -> 向上两级到项目根目录
    project_root = current_file.parent.parent
    
    # 验证是否为有效的项目根目录（检查标志性文件）
    if (project_root / 'sage_mcp_stdio_single.py').exists():
        return project_root
    
    # 最后使用工作目录
    return Path.cwd()


# ===== 核心路径配置 =====
SAGE_HOME = get_project_root()
DATA_DIR = SAGE_HOME / 'data'
LOGS_DIR = SAGE_HOME / 'logs'
HOOKS_DIR = SAGE_HOME / 'hooks'
SCRIPTS_DIR = SAGE_HOME / 'scripts'
DOCS_DIR = SAGE_HOME / 'docs'

# ===== 数据库配置 =====
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'sage_memory')
DB_USER = os.getenv('DB_USER', 'sage')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'sage123')

# ===== 端口配置 =====
MCP_PORT = int(os.getenv('MCP_PORT', '17800'))
WEB_PORT = int(os.getenv('WEB_PORT', '3000'))

# ===== API配置 =====
SILICONFLOW_API_URL = os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1')
SILICONFLOW_API_KEY = os.getenv('SILICONFLOW_API_KEY', '')

# ===== 日志配置 =====
LOG_LEVEL = os.getenv('SAGE_LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('SAGE_LOG_FILE', str(LOGS_DIR / 'sage.log'))

# ===== 会话配置 =====
DEFAULT_SESSION_ID = os.getenv('SAGE_DEFAULT_SESSION_ID', 'default')
SESSION_TIMEOUT = int(os.getenv('SAGE_SESSION_TIMEOUT', '86400'))

# ===== 性能配置 =====
MAX_RESULTS = int(os.getenv('SAGE_MAX_RESULTS', '100'))
CACHE_SIZE = int(os.getenv('SAGE_CACHE_SIZE', '500'))
CACHE_TTL = int(os.getenv('SAGE_CACHE_TTL', '300'))
MAX_CONCURRENT_OPS = int(os.getenv('SAGE_MAX_CONCURRENT_OPS', '5'))


def get_db_url():
    """获取数据库连接URL"""
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def ensure_directories():
    """确保必要的目录存在"""
    for directory in [DATA_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


# 在导入时自动创建必要目录
ensure_directories()

# 打印配置信息（仅在调试模式下）
if os.getenv('SAGE_DEBUG', 'false').lower() == 'true':
    print(f"[CONFIG] SAGE_HOME: {SAGE_HOME}")
    print(f"[CONFIG] Database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"[CONFIG] MCP Port: {MCP_PORT}")