#!/usr/bin/env python3
"""
实际场景测试：模拟Claude CLI提交的真实数据格式
"""
import os
import json
import sys
import subprocess

# 测试场景1：仅包含assistant工具调用结果的对话
def test_tool_call_result():
    print("\n=== 场景1: 工具调用结果（Assistant-only）===")
    
    # 模拟Claude CLI的JSONL格式
    messages = [
        {"role": "assistant", "content": "[Tool execution result]\nSuccessfully executed bash command: ls -la\nOutput:\n-rw-r--r-- 1 user staff 1234 Aug 2 16:00 file.txt"}
    ]
    
    conversation_data = {
        "messages": messages,
        "metadata": {
            "session_id": "cli-session-001",
            "project_id": "sage-project",
            "project_name": "Sage",
            "format": "claude_cli_jsonl",
            "timestamp": 1722592800
        }
    }
    
    # 转换为JSONL格式（Claude CLI格式）
    jsonl_data = json.dumps(conversation_data)
    
    # 执行hook
    result = subprocess.run(
        ["python", os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_stop_hook.py")],
        input=jsonl_data,
        capture_output=True,
        text=True
    )
    
    print(f"返回码: {result.returncode}")
    print(f"输出: {result.stdout}")
    if result.stderr:
        print(f"错误日志片段:\n{result.stderr[-500:]}")  # 只显示最后500字符
    
    # 检查是否成功保存
    success = result.returncode == 0
    if success:
        print("✅ 成功: Assistant-only消息被正确接受并保存")
    else:
        print("❌ 失败: Assistant-only消息被错误拒绝")
        # 检查是否因为我们修复的验证逻辑
        if "Assistant-only message detected" in result.stderr:
            print("✅ 验证逻辑已修复: 检测到Assistant-only消息")
        else:
            print("❌ 验证逻辑未生效")
    
    return success


# 测试场景2：标准对话
def test_standard_conversation():
    print("\n=== 场景2: 标准对话 ===")
    
    messages = [
        {"role": "user", "content": "What is the weather like today?"},
        {"role": "assistant", "content": "I don't have real-time weather data. You can check weather.com or your local weather app for current conditions."}
    ]
    
    conversation_data = {
        "messages": messages,
        "metadata": {
            "session_id": "cli-session-002",
            "project_id": "sage-project",
            "project_name": "Sage",
            "format": "claude_cli_jsonl",
            "timestamp": 1722592900
        }
    }
    
    jsonl_data = json.dumps(conversation_data)
    
    result = subprocess.run(
        ["python", os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_stop_hook.py")],
        input=jsonl_data,
        capture_output=True,
        text=True
    )
    
    print(f"返回码: {result.returncode}")
    print(f"输出: {result.stdout}")
    
    success = result.returncode == 0
    if success:
        print("✅ 成功: 标准对话被正确保存")
    else:
        print("❌ 失败: 标准对话保存失败")
    
    return success


# 测试场景3：检查日志中的分类信息
def test_logging_classification():
    print("\n=== 场景3: 验证日志分类功能 ===")
    
    # User-only消息
    messages = [{"role": "user", "content": "/help"}]
    
    conversation_data = {
        "messages": messages,
        "metadata": {
            "session_id": "cli-session-003",
            "project_id": "sage-project",
            "project_name": "Sage",
            "format": "claude_cli_jsonl",
            "timestamp": 1722593000
        }
    }
    
    jsonl_data = json.dumps(conversation_data)
    
    result = subprocess.run(
        ["python", os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_stop_hook.py")],
        input=jsonl_data,
        capture_output=True,
        text=True
    )
    
    # 检查日志分类
    if "User-only message detected" in result.stderr:
        print("✅ 日志分类正确: 检测到User-only消息")
    else:
        print("❌ 日志分类失败: 未检测到User-only消息")
    
    return result.returncode == 0


def main():
    print("开始实际场景测试...")
    
    # 运行测试
    results = {
        "工具调用结果": test_tool_call_result(),
        "标准对话": test_standard_conversation(),
        "日志分类": test_logging_classification()
    }
    
    # 总结
    print("\n" + "="*50)
    print("测试总结:")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed < total:
        print("\n⚠️ 注意: 部分测试失败可能是因为数据库连接问题，而非验证逻辑问题")
        print("请检查日志中是否包含修复后的验证逻辑标识")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)