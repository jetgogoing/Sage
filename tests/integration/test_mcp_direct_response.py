#!/usr/bin/env python3
"""
直接测试MCP响应格式是否符合Hook的期望
"""
import subprocess
import json
import sys

def test_mcp_response_format():
    """测试MCP服务器的实际响应格式"""
    try:
        print("🔍 测试MCP响应格式...")
        
        # 构建完整的 MCP 会话
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
        
        mcp_call = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "generate_prompt",
                "arguments": {
                    "context": "测试Hook调用MCP的响应格式",
                    "style": "default"
                }
            }
        }
        
        # 准备输入数据
        input_data = json.dumps(mcp_init) + '\n' + json.dumps(mcp_call) + '\n'
        
        print("📤 发送MCP请求...")
        print(f"输入数据: {input_data.strip()}")
        
        # 调用 Sage MCP Server
        sage_mcp_path = "/Users/jet/Sage/sage_mcp_stdio_single.py"
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
        print(f"STDOUT: {result.stdout}")
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
                        print(f"  解析成功: {json.dumps(response, indent=2, ensure_ascii=False)}")
                        
                        # 检查是否是工具调用响应
                        if response.get('id') == 2 and 'result' in response:
                            print(f"  ✅ 找到工具调用响应: ID={response.get('id')}")
                            result_content = response.get('result')
                            print(f"  📊 Result内容: {result_content}")
                            
                            # 检查Hook期望的格式
                            if isinstance(result_content, list) and len(result_content) > 0:
                                first_item = result_content[0]
                                if isinstance(first_item, dict) and 'text' in first_item:
                                    text_content = first_item.get('text', '')
                                    print(f"  ✅ Hook期望格式匹配: {len(text_content)} 字符")
                                    print(f"  📝 文本内容: {text_content}")
                                else:
                                    print(f"  ❌ Hook期望格式不匹配: 第一个元素不是带'text'字段的字典")
                            else:
                                print(f"  ❌ Hook期望格式不匹配: result不是非空数组")
                            
                    except json.JSONDecodeError as e:
                        print(f"  ❌ JSON解析失败: {e}")
        else:
            print(f"❌ MCP调用失败: return code {result.returncode}")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_mcp_response_format()
    print(f"\n🎯 测试结果: {'成功' if success else '失败'}")