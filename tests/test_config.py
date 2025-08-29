#!/usr/bin/env python3
"""
测试配置系统是否正常工作
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import *

def test_config():
    """测试配置加载"""
    print("🔍 Sage 配置测试")
    print("=" * 60)
    
    # 测试路径配置
    print("\n📁 路径配置:")
    print(f"  SAGE_HOME: {SAGE_HOME}")
    print(f"  DATA_DIR: {DATA_DIR}")
    print(f"  LOGS_DIR: {LOGS_DIR}")
    print(f"  HOOKS_DIR: {HOOKS_DIR}")
    print(f"  项目根目录存在: {SAGE_HOME.exists()}")
    
    # 测试数据库配置
    print("\n🗄️ 数据库配置:")
    print(f"  DB_HOST: {DB_HOST}")
    print(f"  DB_PORT: {DB_PORT}")
    print(f"  DB_NAME: {DB_NAME}")
    print(f"  DB_USER: {DB_USER}")
    print(f"  DB_PASSWORD: {'*' * len(DB_PASSWORD) if DB_PASSWORD else '(未设置)'}")
    print(f"  数据库URL: {get_db_url()}")
    
    # 测试端口配置
    print("\n🔌 端口配置:")
    print(f"  MCP_PORT: {MCP_PORT}")
    print(f"  WEB_PORT: {WEB_PORT}")
    
    # 测试API配置
    print("\n🌐 API配置:")
    print(f"  SILICONFLOW_API_URL: {SILICONFLOW_API_URL}")
    print(f"  SILICONFLOW_API_KEY: {'已设置' if SILICONFLOW_API_KEY else '未设置'}")
    
    # 测试环境变量覆盖
    print("\n🔧 环境变量覆盖测试:")
    original_port = os.environ.get('DB_PORT')
    os.environ['DB_PORT'] = '5433'
    # 重新导入设置
    import importlib
    import config.settings
    importlib.reload(config.settings)
    print(f"  设置 DB_PORT=5433 后: {config.settings.DB_PORT}")
    # 恢复原值
    if original_port:
        os.environ['DB_PORT'] = original_port
    else:
        del os.environ['DB_PORT']
    
    # 检查.env文件
    print("\n📄 .env 文件状态:")
    env_file = SAGE_HOME / '.env'
    env_example = SAGE_HOME / '.env.example'
    print(f"  .env 文件存在: {env_file.exists()}")
    print(f"  .env.example 文件存在: {env_example.exists()}")
    
    if not env_file.exists() and env_example.exists():
        print("  ⚠️ 建议：从 .env.example 复制并创建 .env 文件")
    
    # 测试跨平台兼容性
    print("\n🖥️ 平台信息:")
    import platform
    print(f"  操作系统: {platform.system()}")
    print(f"  Python版本: {sys.version}")
    print(f"  路径分隔符: {os.sep}")
    
    print("\n✅ 配置测试完成！")

if __name__ == '__main__':
    test_config()