"""
Sage 配置模块
提供统一的配置管理，解决硬编码问题
"""

from .settings import *

__all__ = [
    'SAGE_HOME',
    'DATA_DIR', 
    'LOGS_DIR',
    'HOOKS_DIR',
    'DB_HOST',
    'DB_PORT',
    'DB_NAME',
    'DB_USER',
    'DB_PASSWORD',
    'MCP_PORT',
    'WEB_PORT',
    'SILICONFLOW_API_URL',
    'get_db_url',
    'ensure_directories'
]