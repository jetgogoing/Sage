#!/usr/bin/env python3
"""测试 sage_memory.py 注入器的基本功能"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_import():
    """测试模块导入"""
    try:
        import sage_memory
        print("✓ sage_memory.py 模块导入成功")
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        return False

def test_cli_path():
    """测试 Claude CLI 路径"""
    from sage_memory import CLAUDE_CLI_PATH
    if os.path.exists(CLAUDE_CLI_PATH):
        print(f"✓ Claude CLI 路径存在: {CLAUDE_CLI_PATH}")
        return True
    else:
        print(f"✗ Claude CLI 路径不存在: {CLAUDE_CLI_PATH}")
        return False

if __name__ == "__main__":
    print("=== 测试 sage_memory.py 注入器 ===")
    test_import()
    test_cli_path()
    print("\n注意：完整功能测试需要先实现 memory.py 模块")