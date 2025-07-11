#!/usr/bin/env python3
"""测试 save_memory 写入功能"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory import save_memory, get_db_connection, SESSION_ID

def test_save_memory():
    """测试保存对话功能"""
    print("=== 测试 save_memory 写入功能 ===")
    
    # 测试数据
    test_query = "Python 中如何对列表进行排序？"
    test_response = """在 Python 中，有几种方法对列表进行排序：

1. 使用 list.sort() 方法（原地排序）：
```python
numbers = [3, 1, 4, 1, 5, 9]
numbers.sort()  # 升序
numbers.sort(reverse=True)  # 降序
```

2. 使用 sorted() 函数（返回新列表）：
```python
numbers = [3, 1, 4, 1, 5, 9]
sorted_numbers = sorted(numbers)  # 升序
sorted_desc = sorted(numbers, reverse=True)  # 降序
```"""
    
    print(f"测试查询: {test_query}")
    print(f"测试响应: {test_response[:50]}...")
    
    try:
        # 保存对话
        save_memory(test_query, test_response)
        print("✓ 对话保存成功")
        
        # 验证数据是否写入
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM conversations 
                WHERE session_id = %s
            """, (SESSION_ID,))
            count = cur.fetchone()[0]
            print(f"✓ 当前会话记录数: {count}")
            
            # 查看最近的记录
            cur.execute("""
                SELECT role, content, 
                       LENGTH(embedding::text) as embedding_size,
                       created_at
                FROM conversations 
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT 2
            """, (SESSION_ID,))
            
            print("\n最近保存的记录:")
            for row in cur.fetchall():
                role, content, emb_size, created = row
                print(f"  - {role}: {content[:50]}...")
                print(f"    向量大小: {emb_size}, 时间: {created}")
                
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

def test_multiple_turns():
    """测试多轮对话保存"""
    print("\n=== 测试多轮对话 ===")
    
    conversations = [
        ("什么是递归？", "递归是一种编程技术，函数直接或间接调用自身..."),
        ("能给个例子吗？", "当然，这是计算阶乘的递归示例...")
    ]
    
    try:
        for query, response in conversations:
            save_memory(query, response)
            
        print("✓ 多轮对话保存成功")
        
        # 检查轮次递增
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT turn_id 
                FROM conversations 
                WHERE session_id = %s
                ORDER BY turn_id
            """, (SESSION_ID,))
            
            turns = [row[0] for row in cur.fetchall()]
            print(f"✓ 对话轮次: {turns}")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

if __name__ == "__main__":
    test_save_memory()
    test_multiple_turns()