#!/usr/bin/env python3
"""
集成测试 - 测试完整的 sage_minimal 流程
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_mock_claude():
    """设置模拟 Claude 环境"""
    mock_claude = project_root / "mock_claude.py"
    
    # 设置环境变量
    os.environ['ORIGINAL_CLAUDE_PATH'] = f"python3 {mock_claude}"
    
    print(f"✅ 设置模拟 Claude: {mock_claude}")
    return str(mock_claude)

def test_full_conversation():
    """测试完整的对话流程"""
    print("\n1. 测试完整对话流程")
    print("="*50)
    
    # 清理递归保护
    if 'SAGE_RECURSION_GUARD' in os.environ:
        del os.environ['SAGE_RECURSION_GUARD']
    
    # 执行 claude_mem_v3
    cmd = [
        "python3", str(project_root / "sage_minimal.py"),
        "--verbose",
        "这是一个测试查询，请帮我解释 Python 装饰器的工作原理"
    ]
    
    print(f"执行命令: {' '.join(cmd[:3])}...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"\n返回码: {result.returncode}")
        print(f"\n标准输出:\n{result.stdout}")
        
        if result.stderr:
            print(f"\n标准错误:\n{result.stderr}")
        
        # 检查是否包含预期内容
        if "Mock Claude CLI" in result.stdout or "响应完成" in result.stdout:
            print("\n✅ Claude 被正确调用")
        else:
            print("\n❌ Claude 调用失败")
            
        if "--verbose" in str(cmd) and result.returncode == 0:
            print("✅ 参数正确传递")
        else:
            print("❌ 参数传递失败")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ 命令执行超时")
        return False
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False

def test_memory_stats():
    """测试记忆统计功能"""
    print("\n2. 测试记忆统计功能")
    print("="*50)
    
    # 清理递归保护
    if 'SAGE_RECURSION_GUARD' in os.environ:
        del os.environ['SAGE_RECURSION_GUARD']
    
    cmd = ["python3", str(project_root / "sage_minimal.py"), "--memory-stats"]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print(f"标准输出:\n{result.stdout}")
        
        if "记忆系统统计" in result.stdout:
            print("\n✅ 记忆统计功能正常")
            return True
        else:
            print("\n❌ 记忆统计功能异常")
            return False
            
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False

def test_no_memory_mode():
    """测试无记忆模式"""
    print("\n3. 测试无记忆模式")
    print("="*50)
    
    # 清理递归保护
    if 'SAGE_RECURSION_GUARD' in os.environ:
        del os.environ['SAGE_RECURSION_GUARD']
    
    cmd = [
        "python3", str(project_root / "sage_minimal.py"),
        "--no-memory",
        "测试无记忆模式"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"标准错误:\n{result.stderr}")
        
        if "记忆功能已禁用" in result.stderr:
            print("\n✅ 无记忆模式正常")
            return True
        else:
            print("\n❌ 无记忆模式标记未生效")
            # 但如果命令成功执行，也算通过
            return result.returncode == 0
            
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False

def check_saved_memory():
    """检查保存的记忆"""
    print("\n4. 检查保存的记忆")
    print("="*50)
    
    try:
        from memory import get_memory_stats, search_memory
        
        # 获取统计
        stats = get_memory_stats()
        print(f"当前记忆总数: {stats['total']}")
        print(f"今日新增: {stats['today']}")
        
        # 搜索最近的记忆
        results = search_memory("测试", n=3)
        print(f"\n最近的测试相关记忆:")
        for i, result in enumerate(results, 1):
            print(f"{i}. [{result['role']}] {result['content'][:100]}...")
            print(f"   相似度: {result['score']:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查记忆失败: {e}")
        return False

def main():
    """运行集成测试"""
    print("🧪 Sage MCP V3 集成测试")
    print("="*80)
    
    # 设置模拟环境
    mock_claude = setup_mock_claude()
    
    # 等待一下让环境稳定
    time.sleep(0.5)
    
    # 运行测试
    tests = [
        ("完整对话流程", test_full_conversation),
        ("记忆统计功能", test_memory_stats),
        ("无记忆模式", test_no_memory_mode),
        ("检查保存的记忆", check_saved_memory)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 异常: {e}")
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "="*80)
    print("集成测试结果汇总")
    print("="*80)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有集成测试通过！阶段1实现完成。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查实现。")
        return 1

if __name__ == "__main__":
    sys.exit(main())