#!/usr/bin/env python3
"""快速测试脚本"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== Sage MCP 快速测试 ===\n")

# 测试导入
try:
    import claude_mem
    import memory
    print("✓ 模块导入成功")
except Exception as e:
    print(f"✗ 模块导入失败: {e}")
    sys.exit(1)

# 测试配置
from memory import SILICONFLOW_API_KEY
from claude_mem import CLAUDE_CLI_PATH
print(f"✓ API Key 已设置: {'是' if SILICONFLOW_API_KEY else '否'}")
print(f"✓ Claude CLI 路径: {CLAUDE_CLI_PATH}")

# 测试数据库
try:
    from memory import get_db_connection
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM conversations")
        count = cur.fetchone()[0]
        print(f"✓ 数据库连接成功，当前记录数: {count}")
    conn.close()
except Exception as e:
    print(f"✗ 数据库测试失败: {e}")

print("\n系统就绪！")
print("设置别名后即可使用: alias claude='python /home/jetgogoing/Sage/claude_mem.py'")