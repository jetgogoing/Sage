#!/usr/bin/env python3
"""
测试用户消息解析器修复
验证字符串和数组格式的content都能正确处理
"""

import sys
import os
from pathlib import Path

# 添加hooks路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'hooks' / 'scripts'))

from sage_stop_hook import SageStopHook

def test_string_content():
    """测试字符串格式的content"""
    hook = SageStopHook()
    
    # 模拟字符串格式的用户消息
    entry = {
        'type': 'user',
        'message': {
            'role': 'user',
            'content': '这是一条测试用户消息'
        },
        'timestamp': '2025-08-02T01:00:00.000Z',
        'uuid': 'test-uuid'
    }
    
    result = hook._parse_claude_cli_message(entry)
    print("字符串格式测试:")
    print(f"  输入: {entry['message']['content']}")
    print(f"  输出: {result['content'] if result else 'None'}")
    print(f"  角色: {result['role'] if result else 'None'}")
    
    return result and result['content'] == '这是一条测试用户消息'

def test_array_content():
    """测试数组格式的content"""
    hook = SageStopHook()
    
    # 模拟数组格式的用户消息
    entry = {
        'type': 'user',
        'message': {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': '这是数组格式的消息'},
                {'type': 'text', 'text': '包含多个部分'}
            ]
        },
        'timestamp': '2025-08-02T01:00:00.000Z',
        'uuid': 'test-uuid'
    }
    
    result = hook._parse_claude_cli_message(entry)
    print("\n数组格式测试:")
    print(f"  输入: {entry['message']['content']}")
    print(f"  输出: {result['content'] if result else 'None'}")
    print(f"  角色: {result['role'] if result else 'None'}")
    
    expected = '这是数组格式的消息\n包含多个部分'
    return result and result['content'] == expected

def test_tool_result_content():
    """测试工具结果格式的content"""
    hook = SageStopHook()
    
    # 模拟工具结果格式的用户消息
    entry = {
        'type': 'user',
        'message': {
            'role': 'user',
            'content': [
                {
                    'tool_use_id': 'toolu_123',
                    'type': 'tool_result',
                    'content': '这是工具执行结果',
                    'is_error': False
                }
            ]
        },
        'timestamp': '2025-08-02T01:00:00.000Z',
        'uuid': 'test-uuid'
    }
    
    result = hook._parse_claude_cli_message(entry)
    print("\n工具结果格式测试:")
    print(f"  输入: {entry['message']['content']}")
    print(f"  输出: {result['content'] if result else 'None'}")
    print(f"  角色: {result['role'] if result else 'None'}")
    
    # 工具结果应该被正确解析（即使没有特殊处理，至少不应该分解）
    return result is not None

def main():
    print("开始测试用户消息解析器修复...")
    
    try:
        test1 = test_string_content()
        test2 = test_array_content()
        test3 = test_tool_result_content()
        
        print(f"\n测试结果:")
        print(f"  字符串格式测试: {'✅ 通过' if test1 else '❌ 失败'}")
        print(f"  数组格式测试: {'✅ 通过' if test2 else '❌ 失败'}")
        print(f"  工具结果格式测试: {'✅ 通过' if test3 else '❌ 失败'}")
        
        if all([test1, test2, test3]):
            print("\n🎉 所有测试通过！用户消息解析器修复成功！")
            return 0
        else:
            print("\n❌ 部分测试失败，需要进一步修复")
            return 1
            
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())