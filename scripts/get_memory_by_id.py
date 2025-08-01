#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据ID获取完整的记忆记录
"""
import asyncio
import sys
import os
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage_core.config.manager import ConfigManager
from sage_core.database.connection import DatabaseConnection


async def get_memory_by_id(memory_id: str):
    """根据ID获取完整的记忆记录"""
    # 初始化配置管理器
    config_manager = ConfigManager()
    db_config = config_manager.get_database_config()
    
    # 创建数据库连接
    db = DatabaseConnection(db_config)
    
    try:
        # 查询指定ID的记忆记录
        query = """
        SELECT id, session_id, user_input, assistant_response, metadata, created_at, updated_at
        FROM memories 
        WHERE id = $1
        """
        
        row = await db.fetchrow(query, memory_id)
        
        if row:
            print(f"记忆ID: {row['id']}")
            print(f"会话ID: {row['session_id']}")
            print(f"创建时间: {row['created_at']}")
            print(f"更新时间: {row['updated_at']}")
            print(f"元数据: {json.dumps(row['metadata'], ensure_ascii=False, indent=2)}")
            print("\n" + "="*80)
            print("用户输入:")
            print("-"*80)
            print(row['user_input'])
            print("\n" + "="*80)
            print("助手回复:")
            print("-"*80)
            print(row['assistant_response'])
        else:
            print(f"未找到ID为 {memory_id} 的记忆记录")
            
    except Exception as e:
        print(f"查询失败：{e}")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使用方法: python get_memory_by_id.py <memory_id>")
        sys.exit(1)
    
    memory_id = sys.argv[1]
    asyncio.run(get_memory_by_id(memory_id))