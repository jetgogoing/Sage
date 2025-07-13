#!/usr/bin/env python3
"""
测试阶段1实现：完整对话捕获和参数透传
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_test(test_name, command, expected_in_output=None):
    """运行单个测试"""
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"命令: {' '.join(command)}")
    print(f"{'='*60}")
    
    try:
        # 设置环境变量避免递归
        env = os.environ.copy()
        # 删除递归保护变量，让测试正常运行
        if 'SAGE_RECURSION_GUARD' in env:
            del env['SAGE_RECURSION_GUARD']
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=env
        )
        
        print(f"返回码: {result.returncode}")
        print(f"标准输出:\n{result.stdout}")
        print(f"标准错误:\n{result.stderr}")
        
        # 检查预期输出
        if expected_in_output:
            if expected_in_output in result.stdout or expected_in_output in result.stderr:
                print(f"✅ 测试通过: 找到预期输出 '{expected_in_output}'")
                return True
            else:
                print(f"❌ 测试失败: 未找到预期输出 '{expected_in_output}'")
                return False
        
        # 仅检查返回码
        if result.returncode == 0:
            print("✅ 测试通过")
            return True
        else:
            print("❌ 测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_argument_parsing():
    """测试参数解析功能"""
    print("\n" + "="*80)
    print("测试集 1: 参数解析")
    print("="*80)
    
    tests = [
        # 基础测试
        ("帮助信息", ["python3", "claude_mem_v3.py", "--help"], None),
        
        # Sage 特有参数
        ("记忆统计", ["python3", "claude_mem_v3.py", "--memory-stats"], "记忆系统统计"),
        
        # Claude 参数透传
        ("模型参数", ["python3", "claude_mem_v3.py", "测试", "--model", "claude-3"], None),
        ("温度参数", ["python3", "claude_mem_v3.py", "测试", "--temperature", "0.7"], None),
        
        # 复杂参数组合
        ("多参数", ["python3", "claude_mem_v3.py", "测试查询", "--model", "claude-3", "--temperature", "0.5", "--max-tokens", "100"], None),
        
        # 无记忆模式
        ("禁用记忆", ["python3", "claude_mem_v3.py", "--no-memory", "测试"], None),
    ]
    
    results = []
    for test_name, command, expected in tests:
        results.append(run_test(test_name, command, expected))
    
    return results

def test_response_capture():
    """测试响应捕获功能"""
    print("\n" + "="*80)
    print("测试集 2: 响应捕获")
    print("="*80)
    
    # 创建一个模拟的 Claude 脚本
    mock_claude = """#!/usr/bin/env python3
import sys
import time

# 模拟流式输出
print("Claude 响应开始...")
sys.stdout.flush()
time.sleep(0.1)

print("这是第一行输出")
sys.stdout.flush()
time.sleep(0.1)

print("这是第二行输出")
sys.stdout.flush()
time.sleep(0.1)

# 输出参数信息
print(f"收到参数: {sys.argv[1:]}")

# 模拟错误输出
print("警告: 这是一个警告信息", file=sys.stderr)
"""
    
    # 创建临时的模拟 Claude
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(mock_claude)
        mock_claude_path = f.name
    
    os.chmod(mock_claude_path, 0o755)
    
    # 设置环境变量指向模拟 Claude
    os.environ['ORIGINAL_CLAUDE_PATH'] = f"python3 {mock_claude_path}"
    
    try:
        result = run_test(
            "流式输出捕获",
            ["python3", "claude_mem_v3.py", "测试流式输出"],
            "Claude 响应开始"
        )
        
        # 清理
        os.unlink(mock_claude_path)
        
        return [result]
        
    except Exception as e:
        print(f"测试异常: {e}")
        if os.path.exists(mock_claude_path):
            os.unlink(mock_claude_path)
        return [False]

def test_memory_functions():
    """测试记忆功能"""
    print("\n" + "="*80)
    print("测试集 3: 记忆功能")
    print("="*80)
    
    # 导入记忆模块
    try:
        from memory import save_conversation_turn, get_memory_stats, search_memory
        
        # 测试保存对话
        print("\n测试: 保存对话轮次")
        try:
            save_conversation_turn(
                "测试用户输入",
                "测试 Claude 响应"
            )
            print("✅ 保存对话成功")
            save_result = True
        except Exception as e:
            print(f"❌ 保存对话失败: {e}")
            save_result = False
        
        # 测试获取统计
        print("\n测试: 获取记忆统计")
        try:
            stats = get_memory_stats()
            print(f"记忆统计: {stats}")
            print("✅ 获取统计成功")
            stats_result = True
        except Exception as e:
            print(f"❌ 获取统计失败: {e}")
            stats_result = False
        
        # 测试搜索
        print("\n测试: 搜索记忆")
        try:
            results = search_memory("测试", n=3)
            print(f"搜索结果数: {len(results)}")
            print("✅ 搜索记忆成功")
            search_result = True
        except Exception as e:
            print(f"❌ 搜索记忆失败: {e}")
            search_result = False
        
        return [save_result, stats_result, search_result]
        
    except ImportError as e:
        print(f"❌ 导入记忆模块失败: {e}")
        return [False, False, False]

def main():
    """运行所有测试"""
    print("🧪 Sage MCP V3 阶段1测试")
    print("="*80)
    
    all_results = []
    
    # 运行测试集
    all_results.extend(test_argument_parsing())
    all_results.extend(test_response_capture())
    all_results.extend(test_memory_functions())
    
    # 汇总结果
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    
    passed = sum(1 for r in all_results if r)
    failed = len(all_results) - passed
    
    print(f"总测试数: {len(all_results)}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"成功率: {passed/len(all_results)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 所有测试通过！阶段1实现完成。")
    else:
        print("\n⚠️  部分测试失败，请检查实现。")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())