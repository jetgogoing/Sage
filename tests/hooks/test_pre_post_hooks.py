#!/usr/bin/env python3
"""
测试PreToolUse和PostToolUse Hooks的功能
模拟工具调用生命周期，验证数据捕获和关联
"""

import json
import sys
import time
import subprocess
from pathlib import Path

# 添加hooks脚本路径
sys.path.append('/Users/jet/Sage/hooks/scripts')

from sage_pre_tool_capture import SagePreToolCapture
from sage_post_tool_capture import SagePostToolCapture

def test_pre_post_hooks():
    """测试Pre/Post hooks的完整流程"""
    print("=== 测试PreToolUse和PostToolUse Hooks ===\n")
    
    # 测试数据
    session_id = f"test_session_{int(time.time())}"
    tool_name = "Read"
    
    # 模拟PreToolUse输入
    pre_input = {
        "sessionId": session_id,
        "toolName": tool_name,
        "toolInput": {
            "file_path": "/Users/test/example.txt"
        },
        "user": "test_user",
        "environment": {
            "cwd": "/Users/test/project"
        }
    }
    
    print("1. 测试PreToolUse Hook...")
    pre_capturer = SagePreToolCapture()
    pre_result = pre_capturer.process_hook(pre_input)
    print(f"   结果: {pre_result}")
    
    if pre_result.get('status') != 'captured':
        print("   ❌ PreToolUse失败")
        return False
    
    call_id = pre_result.get('call_id')
    print(f"   ✅ 成功捕获，call_id: {call_id}")
    
    # 模拟工具执行时间
    time.sleep(0.1)
    
    # 模拟PostToolUse输入
    post_input = {
        "sessionId": session_id,
        "toolName": tool_name,
        "toolOutput": {
            "content": "File content here...",
            "lines": 100
        },
        "executionTimeMs": 150,
        "isError": False,
        "errorMessage": ""
    }
    
    print("\n2. 测试PostToolUse Hook...")
    post_capturer = SagePostToolCapture()
    post_result = post_capturer.process_hook(post_input)
    print(f"   结果: {post_result}")
    
    if post_result.get('status') != 'processed':
        print("   ❌ PostToolUse失败")
        return False
    
    print("   ✅ 成功处理")
    
    # 验证完整记录
    print("\n3. 验证完整记录...")
    temp_dir = Path.home() / '.sage_hooks_temp'
    complete_file = temp_dir / f"complete_{call_id}.json"
    
    if complete_file.exists():
        with open(complete_file, 'r') as f:
            complete_data = json.load(f)
        
        print("   ✅ 找到完整记录")
        print(f"   - Call ID: {complete_data.get('call_id')}")
        print(f"   - Pre数据: {'有' if complete_data.get('pre_call') else '无'}")
        print(f"   - Post数据: {'有' if complete_data.get('post_call') else '无'}")
        
        # 清理测试文件
        complete_file.unlink()
        return True
    else:
        print("   ❌ 未找到完整记录")
        return False

def test_zen_tool_handling():
    """测试ZEN工具的特殊处理"""
    print("\n=== 测试ZEN工具处理 ===\n")
    
    session_id = f"test_zen_{int(time.time())}"
    tool_name = "mcp__zen__debug"
    
    # PreToolUse
    pre_input = {
        "sessionId": session_id,
        "toolName": tool_name,
        "toolInput": {
            "step": "Testing ZEN tool",
            "model": "openai/o3"
        }
    }
    
    pre_capturer = SagePreToolCapture()
    pre_result = pre_capturer.process_hook(pre_input)
    call_id = pre_result.get('call_id')
    
    # PostToolUse with ZEN output
    post_input = {
        "sessionId": session_id,
        "toolName": tool_name,
        "toolOutput": {
            "status": "complete",
            "content": "Deep analysis results...",
            "metadata": {
                "model_used": "openai/o3",
                "provider": "openrouter"
            },
            "confidence": "high",
            "findings": "Test findings from ZEN analysis"
        },
        "executionTimeMs": 2500,
        "isError": False
    }
    
    post_capturer = SagePostToolCapture()
    post_result = post_capturer.process_hook(post_input)
    
    # 验证ZEN分析提取
    temp_dir = Path.home() / '.sage_hooks_temp'
    complete_file = temp_dir / f"complete_{call_id}.json"
    
    if complete_file.exists():
        with open(complete_file, 'r') as f:
            complete_data = json.load(f)
        
        zen_analysis = complete_data.get('post_call', {}).get('zen_analysis', {})
        if zen_analysis.get('is_zen_tool'):
            print("   ✅ ZEN工具识别成功")
            print(f"   - Model: {zen_analysis.get('model_used')}")
            print(f"   - Confidence: {zen_analysis.get('confidence')}")
            print(f"   - Findings: {zen_analysis.get('findings_summary')}")
            
            # 清理
            complete_file.unlink()
            return True
    
    print("   ❌ ZEN工具处理失败")
    return False

def test_performance():
    """测试hooks性能影响"""
    print("\n=== 测试性能影响 ===\n")
    
    # 测试单次执行时间
    times = []
    
    for i in range(10):
        start = time.time()
        
        # 模拟hook调用
        pre_input = {
            "sessionId": f"perf_test_{i}",
            "toolName": "TestTool",
            "toolInput": {"test": i}
        }
        
        pre_capturer = SagePreToolCapture()
        pre_capturer.process_hook(pre_input)
        
        elapsed = (time.time() - start) * 1000  # 转换为毫秒
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    max_time = max(times)
    
    print(f"   平均执行时间: {avg_time:.2f}ms")
    print(f"   最大执行时间: {max_time:.2f}ms")
    print(f"   {'✅' if max_time < 50 else '❌'} 性能要求: < 50ms")
    
    return max_time < 50

if __name__ == "__main__":
    print("开始测试PreToolUse和PostToolUse Hooks\n")
    
    # 运行测试
    test1 = test_pre_post_hooks()
    test2 = test_zen_tool_handling()
    test3 = test_performance()
    
    # 总结
    print("\n=== 测试总结 ===")
    print(f"基础功能测试: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"ZEN工具处理: {'✅ 通过' if test2 else '❌ 失败'}")
    print(f"性能测试: {'✅ 通过' if test3 else '❌ 失败'}")
    
    all_passed = test1 and test2 and test3
    print(f"\n总体结果: {'✅ 全部通过' if all_passed else '❌ 有失败项'}")
    
    sys.exit(0 if all_passed else 1)