#!/usr/bin/env python3
"""测试数据库连接的脚本"""

import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'mem',
    'user': 'mem',
    'password': 'mem'
}

def test_connection():
    """测试数据库连接"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✓ 数据库连接成功")
        
        with conn.cursor() as cur:
            # 检查 pgvector 扩展
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            if cur.fetchone():
                print("✓ pgvector 扩展已安装")
            else:
                print("✗ pgvector 扩展未安装")
                
            # 检查 conversations 表
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'conversations'
                );
            """)
            if cur.fetchone()[0]:
                print("✓ conversations 表已存在")
            else:
                print("✗ conversations 表不存在")
                
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return False

if __name__ == "__main__":
    test_connection()