#!/usr/bin/env python3
"""
集成测试：验证修复后的sage_stop_hook.py在实际环境中的表现
"""
import json
import os
import sys
import subprocess
import time

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


def test_assistant_only_message():
    """测试assistant-only消息（工具调用结果）"""
    print("\n=== 测试1: Assistant-only消息（工具调用结果）===")
    
    test_data = {
        "messages": [
            {"role": "assistant", "content": "Tool execution completed: Database query returned 42 records"}
        ],
        "session_id": "test-session-001",
        "project_name": "test-project",
        "format": "claude_cli_jsonl",
        "format": "claude_cli_jsonl"
    }
    
    # 创建测试文件
    test_file = "/tmp/test_assistant_only.json"
    with open(test_file, 'w') as f:
        json.dump(test_data, f)
    
    # 执行hook（通过stdin传递数据）
    with open(test_file, 'r') as f:
        test_json = f.read()
    
    result = subprocess.run([
        "python", os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_stop_hook.py")
    ], input=test_json, capture_output=True, text=True)
    
    print(f"Exit code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")
    
    # 清理
    os.remove(test_file)
    
    return result.returncode == 0


def test_user_only_message():
    """测试user-only消息"""
    print("\n=== 测试2: User-only消息 ===")
    
    test_data = {
        "messages": [
            {"role": "user", "content": "/help"}
        ],
        "session_id": "test-session-002",
        "project_name": "test-project",
        "format": "claude_cli_jsonl"
    }
    
    test_file = "/tmp/test_user_only.json"
    with open(test_file, 'w') as f:
        json.dump(test_data, f)
    
    result = subprocess.run([
        "python", os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_stop_hook.py"), test_file
    ], capture_output=True, text=True)
    
    print(f"Exit code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")
    
    os.remove(test_file)
    
    return result.returncode == 0


def test_standard_conversation():
    """测试标准对话"""
    print("\n=== 测试3: 标准对话 ===")
    
    test_data = {
        "messages": [
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "The capital of France is Paris."}
        ],
        "session_id": "test-session-003",
        "project_name": "test-project",
        "format": "claude_cli_jsonl"
    }
    
    test_file = "/tmp/test_standard.json"
    with open(test_file, 'w') as f:
        json.dump(test_data, f)
    
    result = subprocess.run([
        "python", os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_stop_hook.py"), test_file
    ], capture_output=True, text=True)
    
    print(f"Exit code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")
    
    os.remove(test_file)
    
    return result.returncode == 0


def test_empty_messages():
    """测试空消息（应该被拒绝）"""
    print("\n=== 测试4: 空消息（应该被拒绝）===")
    
    test_data = {
        "messages": [],
        "session_id": "test-session-004",
        "project_name": "test-project",
        "format": "claude_cli_jsonl"
    }
    
    test_file = "/tmp/test_empty.json"
    with open(test_file, 'w') as f:
        json.dump(test_data, f)
    
    result = subprocess.run([
        "python", os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_stop_hook.py"), test_file
    ], capture_output=True, text=True)
    
    print(f"Exit code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")
    
    os.remove(test_file)
    
    # 这个应该失败
    return result.returncode != 0


def main():
    """运行所有集成测试"""
    print("开始运行集成测试...")
    
    tests = [
        ("Assistant-only消息", test_assistant_only_message),
        ("User-only消息", test_user_only_message),
        ("标准对话", test_standard_conversation),
        ("空消息拒绝", test_empty_messages)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"测试 {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 打印总结
    print("\n=== 测试总结 ===")
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed_count}/{total_count} 通过")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)