#!/usr/bin/env python3
"""测试 save_memory 写入功能（使用模拟向量）"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import memory
import numpy as np

# 模拟向量化函数，避免 API 调用
def mock_embed_text(text):
    """返回随机向量用于测试"""
    return np.random.rand(4096).tolist()

# 替换原始函数
memory.embed_text = mock_embed_text

from memory import save_memory, get_db_connection, SESSION_ID

def test_save_memory_mock():
    """测试保存对话功能（使用模拟向量）"""
    print("=== 测试 save_memory 写入功能（模拟模式）===")
    
    # 测试数据
    test_query = "测试查询"
    test_response = "测试响应"
    
    try:
        # 保存对话
        save_memory(test_query, test_response)
        print("✓ 对话保存调用成功")
        
        # 验证数据
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT role, content, 
                       embedding IS NOT NULL as has_embedding,
                       turn_id
                FROM conversations 
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT 2
            """, (SESSION_ID,))
            
            results = cur.fetchall()
            
            if len(results) >= 2:
                print("✓ 成功写入两条记录")
                for role, content, has_emb, turn in results:
                    print(f"  - {role}: {content}, 向量: {'有' if has_emb else '无'}, 轮次: {turn}")
            else:
                print(f"✗ 只找到 {len(results)} 条记录")
                
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_save_memory_mock()