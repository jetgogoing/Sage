#!/usr/bin/env python3
"""
测试改进后的 Stop Hook 数据整合功能
"""

import json
import sys
import os
import time
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'hooks' / 'scripts'))

from sage_stop_hook import SageStopHook

def create_test_hook_data(temp_dir: Path, session_id: str) -> dict:
    """创建测试用的Hook数据"""
    
    # 创建完整的Hook记录
    call_id = "test-call-12345"
    complete_record = {
        "call_id": call_id,
        "pre_call": {
            "call_id": call_id,
            "timestamp": time.time(),
            "session_id": session_id,
            "tool_name": "mcp__zen__chat",
            "tool_input": {
                "prompt": "测试ZEN工具的完整数据记录功能",
                "model": "openai/o3-mini"
            },
            "cwd": str(Path.cwd()),
            "project_id": "test_project",
            "project_name": "TestProject"
        },
        "post_call": {
            "timestamp": time.time() + 5,
            "session_id": session_id,
            "tool_name": "mcp__zen__chat",
            "tool_output": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "status": "success",
                        "content": "这是一个完整的ZEN工具AI分析结果，包含了详细的思维过程和结论。通过Hook数据整合，现在可以完整保存这些信息而不是简单的标记。",
                        "metadata": {
                            "model_used": "openai/o3-mini",
                            "thinking_mode": "medium"
                        }
                    })
                }
            ],
            "execution_time_ms": 2500,
            "is_error": False,
            "error_message": "",
            "zen_analysis": {
                "is_zen_tool": True,
                "analysis_type": "chat"
            }
        },
        "complete_timestamp": time.time() + 6
    }
    
    # 保存到临时目录
    complete_file = temp_dir / f"complete_{call_id}.json"
    with open(complete_file, 'w', encoding='utf-8') as f:
        json.dump(complete_record, f, indent=2, ensure_ascii=False)
    
    return complete_record

def create_test_transcript(session_id: str) -> list:
    """创建测试用的transcript数据"""
    
    transcript_lines = [
        json.dumps({
            "type": "user",
            "timestamp": "2025-08-02T01:00:00.000Z",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "请测试ZEN工具的完整数据记录功能"
                    }
                ]
            }
        }),
        json.dumps({
            "type": "assistant", 
            "timestamp": "2025-08-02T01:00:05.000Z",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "我来帮您测试ZEN工具的完整数据记录功能。"
                    },
                    {
                        "type": "tool_use",
                        "id": "test-tool-use-id",
                        "name": "mcp__zen__chat",
                        "input": {
                            "prompt": "测试ZEN工具的完整数据记录功能",
                            "model": "openai/o3-mini"
                        }
                    }
                ]
            }
        }),
        json.dumps({
            "type": "assistant",
            "timestamp": "2025-08-02T01:00:10.000Z", 
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "测试完成。通过Hook数据整合，现在可以保存完整的工具调用详情了。"
                    }
                ]
            }
        })
    ]
    
    return transcript_lines

def test_stop_hook_integration():
    """测试Stop Hook数据整合功能"""
    
    print("🧪 开始测试 Stop Hook 数据整合功能...")
    
    # 创建临时目录和数据
    session_id = "test-session-12345"
    
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        
        # 创建测试Hook数据
        print("📊 创建测试Hook数据...")
        hook_record = create_test_hook_data(temp_dir, session_id)
        
        # 创建测试transcript数据
        print("📝 创建测试transcript数据...")
        transcript_lines = create_test_transcript(session_id)
        
        # 初始化Stop Hook（模拟临时目录）
        print("🔧 初始化Stop Hook...")
        stop_hook = SageStopHook()
        stop_hook.temp_dir = temp_dir  # 使用测试临时目录
        
        # 测试Hook数据加载
        print("🔍 测试Hook数据加载...")
        hook_data = stop_hook._load_session_hook_data(session_id)
        print(f"✅ 加载了 {len(hook_data)} 个Hook记录")
        
        if hook_data:
            call_id = list(hook_data.keys())[0]
            record = hook_data[call_id]
            print(f"📋 Hook记录详情: tool_name={record['pre_call']['tool_name']}")
            print(f"📋 输入参数: {record['pre_call']['tool_input']}")
            print(f"📋 执行时间: {record['post_call']['execution_time_ms']}ms")
        
        # 测试完整交互提取
        print("🔄 测试完整交互提取...")
        conversation_data = stop_hook._extract_complete_interaction(transcript_lines, session_id)
        
        print(f"✅ 提取结果:")
        print(f"   - 消息数量: {conversation_data['message_count']}")
        print(f"   - 工具调用数量: {conversation_data['tool_call_count']}")
        print(f"   - Hook数据数量: {conversation_data['hook_data_count']}")
        print(f"   - 增强消息数量: {conversation_data['enriched_message_count']}")
        print(f"   - 增强工具数量: {conversation_data['enriched_tool_count']}")
        print(f"   - 提取方法: {conversation_data['extraction_method']}")
        
        # 检查消息内容是否被增强
        messages = conversation_data['messages']
        for i, msg in enumerate(messages):
            print(f"\n📨 消息 {i+1} ({msg['role']}):")
            content = msg['content']
            if len(content) > 200:
                print(f"   内容预览: {content[:200]}...")
            else:
                print(f"   内容: {content}")
            
            if 'tool_enrichments' in msg:
                enrichments = msg['tool_enrichments']
                print(f"   工具增强: {len(enrichments)} 个")
                for enrich in enrichments:
                    print(f"     - 工具: {enrich['tool_name']}, 增强: {enrich['enriched']}")
        
        # 检查工具调用详情
        tool_calls = conversation_data['tool_calls']
        for i, tool in enumerate(tool_calls):
            print(f"\n🔧 工具调用 {i+1}:")
            print(f"   工具名: {tool.get('tool_name')}")
            print(f"   Hook增强: {tool.get('enriched_from_hook', False)}")
            if tool.get('enriched_from_hook'):
                print(f"   执行时间: {tool.get('execution_time_ms')}ms")
                print(f"   有错误: {tool.get('is_error')}")
    
    print("\n🎉 测试完成！")

if __name__ == "__main__":
    test_stop_hook_integration()