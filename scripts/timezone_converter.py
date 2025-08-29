#!/usr/bin/env python3
"""
Sage MCP 时区转换工具
用于在应用层处理 UTC 到北京时间的转换
"""

import os
import asyncio
from datetime import datetime, timezone, timedelta
import asyncpg
from typing import List, Dict, Any

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

class TimezoneConverter:
    """时区转换器类"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        
    @staticmethod
    def utc_to_beijing(utc_time: datetime) -> datetime:
        """将 UTC 时间转换为北京时间"""
        if utc_time.tzinfo is None:
            # 如果没有时区信息，假设为 UTC
            utc_time = utc_time.replace(tzinfo=timezone.utc)
        return utc_time.astimezone(BEIJING_TZ)
    
    @staticmethod
    def beijing_to_utc(beijing_time: datetime) -> datetime:
        """将北京时间转换为 UTC"""
        if beijing_time.tzinfo is None:
            # 如果没有时区信息，假设为北京时间
            beijing_time = beijing_time.replace(tzinfo=BEIJING_TZ)
        return beijing_time.astimezone(timezone.utc)
    
    async def get_conversations_with_beijing_time(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取对话记录并转换为北京时间"""
        conn = await asyncpg.connect(self.db_url)
        try:
            query = """
                SELECT 
                    id,
                    user_query,
                    assistant_response,
                    created_at
                FROM conversations
                ORDER BY created_at DESC
                LIMIT $1
            """
            rows = await conn.fetch(query, limit)
            
            results = []
            for row in rows:
                result = dict(row)
                # 转换时间为北京时间
                result['beijing_time'] = self.utc_to_beijing(result['created_at'])
                result['beijing_time_str'] = result['beijing_time'].strftime('%Y-%m-%d %H:%M:%S %Z')
                results.append(result)
                
            return results
            
        finally:
            await conn.close()
    
    async def search_by_beijing_time_range(self, start_beijing: str, end_beijing: str) -> List[Dict[str, Any]]:
        """按北京时间范围搜索记录"""
        # 解析北京时间字符串
        start_dt = datetime.strptime(start_beijing, '%Y-%m-%d %H:%M:%S')
        start_dt = start_dt.replace(tzinfo=BEIJING_TZ)
        end_dt = datetime.strptime(end_beijing, '%Y-%m-%d %H:%M:%S')
        end_dt = end_dt.replace(tzinfo=BEIJING_TZ)
        
        # 转换为 UTC
        start_utc = self.beijing_to_utc(start_dt)
        end_utc = self.beijing_to_utc(end_dt)
        
        conn = await asyncpg.connect(self.db_url)
        try:
            query = """
                SELECT 
                    id,
                    user_query,
                    created_at
                FROM conversations
                WHERE created_at >= $1 AND created_at <= $2
                ORDER BY created_at DESC
            """
            rows = await conn.fetch(query, start_utc, end_utc)
            
            results = []
            for row in rows:
                result = dict(row)
                result['beijing_time'] = self.utc_to_beijing(result['created_at'])
                result['beijing_time_str'] = result['beijing_time'].strftime('%Y-%m-%d %H:%M:%S')
                results.append(result)
                
            return results
            
        finally:
            await conn.close()


async def main():
    """示例用法"""
    # 从环境变量获取数据库连接
    db_url = os.getenv('DATABASE_URL', 'postgresql://sage:sage123@localhost:5432/sage_memory')
    
    converter = TimezoneConverter(db_url)
    
    # 示例1：获取最近的对话并显示北京时间
    print("=== 最近的对话记录（北京时间）===")
    conversations = await converter.get_conversations_with_beijing_time(5)
    for conv in conversations:
        print(f"ID: {conv['id']}")
        print(f"UTC时间: {conv['created_at']}")
        print(f"北京时间: {conv['beijing_time_str']}")
        print(f"用户查询: {conv['user_query'][:50]}...")
        print("-" * 50)
    
    # 示例2：按北京时间范围搜索
    print("\n=== 按北京时间范围搜索 ===")
    # 搜索今天的记录
    today = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
    start_time = f"{today} 00:00:00"
    end_time = f"{today} 23:59:59"
    
    results = await converter.search_by_beijing_time_range(start_time, end_time)
    print(f"今天（{today}）的记录数: {len(results)}")
    
    # 示例3：时间转换演示
    print("\n=== 时间转换演示 ===")
    now_utc = datetime.now(timezone.utc)
    now_beijing = converter.utc_to_beijing(now_utc)
    print(f"当前 UTC 时间: {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"当前北京时间: {now_beijing.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # 反向转换
    back_to_utc = converter.beijing_to_utc(now_beijing)
    print(f"转回 UTC 时间: {back_to_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")


if __name__ == "__main__":
    asyncio.run(main())