#!/usr/bin/env python3
"""
测试数据提取功能的脚本
验证增强版archiver能否正确提取tool_use和tool_result
"""

import json
import tempfile
import os
import sys
sys.path.append('/Users/jet/Sage/hooks/scripts')

from sage_archiver_enhanced import EnhancedSageArchiver

def create_test_transcript():
    """创建包含各种content类型的测试transcript"""
    test_data = [
        # User message
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please read the README file"}
                ]
            }
        },
        # Assistant message with tool use
        {
            "type": "assistant", 
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll read the README file for you."},
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "id": "tool_123",
                        "input": {"file_path": "/Users/test/README.md"}
                    }
                ]
            }
        },
        # Tool result
        {
            "type": "tool_result",
            "tool_use_id": "tool_123",
            "content": "# README\nThis is a test project.",
            "is_error": False
        },
        # Assistant final response
        {
            "type": "assistant",
            "message": {
                "role": "assistant", 
                "content": [
                    {"type": "text", "text": "The README file contains a header and says this is a test project."}
                ]
            }
        }
    ]
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        for entry in test_data:
            f.write(json.dumps(entry) + '\n')
        return f.name

def test_extraction():
    """测试数据提取功能"""
    print("=== 测试增强版数据提取功能 ===\n")
    
    # 创建测试数据
    transcript_path = create_test_transcript()
    print(f"创建测试transcript: {transcript_path}")
    
    # 创建archiver实例
    archiver = EnhancedSageArchiver()
    
    # 测试提取
    user_msg, assistant_msg, tool_calls, tool_results = archiver.extract_complete_interaction(transcript_path)
    
    print("\n=== 提取结果 ===")
    print(f"用户消息: {user_msg}")
    print(f"助手消息: {assistant_msg}")
    print(f"工具调用数: {len(tool_calls)}")
    if tool_calls:
        print("工具调用详情:")
        for tc in tool_calls:
            print(f"  - {tc['name']} (ID: {tc['id']})")
            print(f"    输入: {tc['input']}")
    
    print(f"\n工具结果数: {len(tool_results)}")
    if tool_results:
        print("工具结果详情:")
        for tr in tool_results:
            print(f"  - ID: {tr['tool_use_id']}")
            print(f"    错误: {tr['is_error']}")
            print(f"    内容: {tr['content'][:50]}...")
    
    # 清理
    os.unlink(transcript_path)
    
    # 验证结果
    success = all([
        user_msg is not None,
        assistant_msg is not None,
        len(tool_calls) > 0,
        len(tool_results) > 0
    ])
    
    print(f"\n测试结果: {'✅ 成功' if success else '❌ 失败'}")
    print(f"数据完整性: {sum([bool(user_msg), bool(assistant_msg), len(tool_calls)>0, len(tool_results)>0])/4*100:.0f}%")
    
    return success

if __name__ == "__main__":
    test_extraction()