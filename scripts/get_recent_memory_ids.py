#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取最近5个记忆的ID
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage_core.config.manager import ConfigManager
from sage_core.database.connection import DatabaseConnection


async def get_recent_memory_ids():
    """获取最近5个记忆的ID"""
    # 初始化配置管理器
    config_manager = ConfigManager()
    db_config = config_manager.get_database_config()
    
    # 创建数据库连接
    db = DatabaseConnection(db_config)
    
    try:
        # 查询最近5个记忆的ID
        query = """
        SELECT id, created_at, LEFT(user_input, 50) as user_input_preview
        FROM memories 
        ORDER BY created_at DESC 
        LIMIT 5
        """
        
        rows = await db.fetch(query)
        
        print("最近5个记忆的ID:")
        print("-" * 80)
        for row in rows:
            print(f"ID: {row['id']}")
            print(f"时间: {row['created_at']}")
            print(f"用户输入预览: {row['user_input_preview']}...")
            print("-" * 80)
            
    except Exception as e:
        print(f"查询失败：{e}")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(get_recent_memory_ids())