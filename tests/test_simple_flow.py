#!/usr/bin/env python3
"""简单的流程测试"""

import sys
import os

# 清除递归保护
if 'SAGE_RECURSION_GUARD' in os.environ:
    del os.environ['SAGE_RECURSION_GUARD']

sys.path.insert(0, '/Volumes/1T HDD/Sage')

print("1. 导入模块...")
try:
    from sage_minimal import ImprovedCrossplatformClaude
    print("   ✓ 导入成功")
except Exception as e:
    print(f"   ✗ 导入失败: {e}")
    sys.exit(1)

print("\n2. 创建实例...")
try:
    app = ImprovedCrossplatformClaude()
    print("   ✓ 创建成功")
except Exception as e:
    print(f"   ✗ 创建失败: {e}")
    sys.exit(1)

print("\n3. 解析参数...")
try:
    # 模拟参数
    sys.argv = ['test', '测试消息']
    parsed = app.parse_arguments(sys.argv[1:])
    print(f"   ✓ 解析成功: {parsed}")
except Exception as e:
    print(f"   ✗ 解析失败: {e}")
    sys.exit(1)

print("\n4. 查找 Claude...")
try:
    claude_path = app.find_claude_executable()
    if claude_path:
        print(f"   ✓ 找到 Claude: {claude_path}")
    else:
        print("   ✗ 未找到 Claude")
        # 继续测试，看看会发生什么
except Exception as e:
    print(f"   ✗ 查找失败: {e}")

print("\n5. 测试记忆模块...")
try:
    provider = app.memory_provider
    if provider:
        print("   ✓ 记忆模块可用")
        # 测试保存
        provider.save_conversation("测试输入", "测试响应")
        print("   ✓ 保存测试成功")
    else:
        print("   ✗ 记忆模块不可用")
except Exception as e:
    print(f"   ✗ 记忆模块错误: {e}")

print("\n测试完成")