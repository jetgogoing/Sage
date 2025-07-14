#!/usr/bin/env python3
"""
简单测试脚本 - 逐步验证各个功能
"""

import os
import sys
import subprocess
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试导入"""
    print("1. 测试模块导入...")
    try:
        import memory
        print("✅ memory 模块导入成功")
    except Exception as e:
        print(f"❌ memory 模块导入失败: {e}")
        return False
    
    try:
        import sage_minimal
        print("✅ sage_minimal 模块导入成功")
    except Exception as e:
        print(f"❌ sage_minimal 模块导入失败: {e}")
        return False
    
    return True

def test_memory_functions():
    """测试记忆功能"""
    print("\n2. 测试记忆功能...")
    try:
        from memory import save_conversation_turn, get_memory_stats
        
        # 测试保存
        save_conversation_turn("测试问题", "测试回答")
        print("✅ 保存对话成功")
        
        # 测试统计
        stats = get_memory_stats()
        print(f"✅ 获取统计成功: {stats}")
        
        return True
    except Exception as e:
        print(f"❌ 记忆功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_argument_parsing():
    """测试参数解析"""
    print("\n3. 测试参数解析...")
    try:
        from sage_minimal import ImprovedCrossplatformClaude, ParsedArgs
        
        app = ImprovedCrossplatformClaude()
        
        # 测试简单参数
        result = app.parse_arguments_improved(["测试查询"])
        print(f"✅ 简单参数: user_prompt='{result.user_prompt}'")
        
        # 测试复杂参数
        result = app.parse_arguments_improved(["--model", "claude-3", "测试", "--temperature", "0.5"])
        print(f"✅ 复杂参数: user_prompt='{result.user_prompt}', claude_args={result.claude_args}")
        
        # 测试 Sage 选项
        result = app.parse_arguments_improved(["--no-memory", "测试"])
        print(f"✅ Sage选项: no_memory={result.sage_options.get('no_memory')}")
        
        return True
    except Exception as e:
        print(f"❌ 参数解析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_find_claude():
    """测试查找 Claude"""
    print("\n4. 测试查找 Claude...")
    try:
        from sage_minimal import ImprovedCrossplatformClaude
        
        app = ImprovedCrossplatformClaude()
        claude_path = app.find_claude_executable()
        
        if claude_path:
            print(f"✅ 找到 Claude: {claude_path}")
            return True
        else:
            print("⚠️  未找到 Claude CLI（这在测试环境中是正常的）")
            return True  # 在测试环境中，找不到也算通过
    except Exception as e:
        print(f"❌ 查找 Claude 失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("🧪 Sage MCP V3 简单测试")
    print("="*50)
    
    # 清理环境变量
    if 'SAGE_RECURSION_GUARD' in os.environ:
        del os.environ['SAGE_RECURSION_GUARD']
    
    tests = [
        test_imports,
        test_memory_functions,
        test_argument_parsing,
        test_find_claude
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append(False)
    
    # 汇总
    print("\n" + "="*50)
    print("测试结果汇总")
    print("="*50)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"总测试数: {total}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {total - passed}")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️  部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())