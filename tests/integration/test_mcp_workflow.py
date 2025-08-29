#!/usr/bin/env python3
"""
测试完整的MCP工作流程，包括initialized通知
"""
import os
import subprocess
import json
import sys

def test_mcp_full_workflow():
    """测试完整的MCP工作流程"""
    try:
        print("🔍 测试完整MCP工作流程...")
        
        # 1. 初始化请求
        mcp_init = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "sage-hook", "version": "1.0.0"}
            }
        }
        
        # 2. initialized通知
        mcp_initialized = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        # 3. 工具调用
        mcp_call = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "generate_prompt",
                "arguments": {
                    "context": "测试Hook调用MCP的完整流程",
                    "style": "default"
                }
            }
        }
        
        # 准备输入数据（按顺序）
        input_data = (
            json.dumps(mcp_init) + '\n' +
            json.dumps(mcp_initialized) + '\n' +
            json.dumps(mcp_call) + '\n'
        )
        
        print("📤 发送完整MCP会话...")
        print("步骤1: Initialize")
        print("步骤2: Initialized通知")
        print("步骤3: 工具调用")
        
        # 调用 Sage MCP Server
        sage_mcp_path = os.path.join(os.getenv('SAGE_HOME', '.'), "sage_mcp_stdio_single.py")
        cmd = [sys.executable, sage_mcp_path]
        
        result = subprocess.run(
            cmd,
            input=input_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            text=True
        )
        
        print(f"\n📥 MCP响应 (return code: {result.returncode}):")
        print(f"STDERR: {result.stderr}")
        
        if result.returncode == 0:
            # 解析响应
            lines = result.stdout.strip().split('\n')
            print(f"\n🔍 解析响应行数: {len(lines)}")
            
            for i, line in enumerate(lines):
                if line.strip():
                    print(f"Line {i+1}: {line.strip()}")
                    try:
                        response = json.loads(line.strip())
                        
                        # 检查是否是工具调用响应
                        if response.get('id') == 3 and 'result' in response:
                            print(f"  ✅ 找到工具调用响应: ID={response.get('id')}")
                            result_content = response.get('result')
                            print(f"  📊 Result类型: {type(result_content)}")
                            
                            # 检查Hook期望的格式: result[0].text
                            if isinstance(result_content, dict) and 'content' in result_content:
                                content_list = result_content['content']
                                if isinstance(content_list, list) and len(content_list) > 0:
                                    first_item = content_list[0]
                                    if isinstance(first_item, dict) and 'text' in first_item:
                                        text_content = first_item.get('text', '')
                                        print(f"  ✅ Hook期望格式匹配: {len(text_content)} 字符")
                                        print(f"  📝 文本内容: {text_content}")
                                        return True
                                    else:
                                        print(f"  ❌ Hook期望格式不匹配: content[0]不是带'text'字段的字典")
                                        print(f"  📝 实际格式: {first_item}")
                                else:
                                    print(f"  ❌ Hook期望格式不匹配: content不是非空数组")
                            else:
                                print(f"  ❌ Hook期望格式不匹配: result不包含content")
                                print(f"  📝 实际结构: {result_content}")
                        elif response.get('id') == 3 and 'error' in response:
                            print(f"  ❌ 工具调用出错: {response['error']}")
                            
                    except json.JSONDecodeError as e:
                        print(f"  ❌ JSON解析失败: {e}")
        else:
            print(f"❌ MCP调用失败: return code {result.returncode}")
            
        return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_mcp_full_workflow()
    print(f"\n🎯 测试结果: {'成功' if success else '失败'}")