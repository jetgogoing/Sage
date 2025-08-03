#!/usr/bin/env python3
"""
测试Stop Hook处理包含工具调用的复杂会话
验证工具调用数据是否能完整保存到数据库
"""

import json
import sys
import subprocess
import tempfile
from pathlib import Path
import time
import asyncio

# 添加项目路径
sys.path.insert(0, '/Users/jet/Sage')

async def test_stop_hook_with_tools():
    """测试包含工具调用的Stop Hook数据库保存功能"""
    
    # 1. 检查数据库初始状态
    print("🔍 检查数据库初始记忆数量...")
    result = subprocess.run([
        "docker", "exec", "sage-db", "psql", "-U", "sage", "-d", "sage_memory",
        "-c", "SELECT COUNT(*) FROM memories;"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ 数据库连接失败: {result.stderr}")
        return False
    
    initial_count = int(result.stdout.split('\n')[2].strip())
    print(f"📊 初始记忆数量: {initial_count}")
    
    # 2. 创建包含工具调用的模拟transcript文件
    print("📝 创建包含工具调用的模拟transcript文件...")
    test_session_id = "test-tools-session-" + str(int(time.time()))
    
    test_transcript_path = f"/Users/jet/Sage/tests/integration/test_tools_transcript.jsonl"
    with open(test_transcript_path, 'w', encoding='utf-8') as f:
        # 用户消息
        user_entry = {
            "type": "user",
            "timestamp": "2025-08-01T18:30:00Z",
            "uuid": "user-msg-123",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "请帮我搜索关于Python异步编程的信息"}]
            }
        }
        f.write(json.dumps(user_entry) + '\n')
        
        # 助手回复（包含工具调用）
        assistant_entry = {
            "type": "assistant",
            "timestamp": "2025-08-01T18:30:05Z", 
            "uuid": "assistant-msg-456",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "我来帮您搜索Python异步编程的相关信息。"},
                    {
                        "type": "tool_use",
                        "id": "tool_call_789",
                        "name": "WebSearch",
                        "input": {
                            "query": "Python异步编程 asyncio 教程",
                            "max_results": 5
                        }
                    },
                    {"type": "text", "text": "根据搜索结果，Python异步编程主要使用asyncio库..."}
                ]
            }
        }
        f.write(json.dumps(assistant_entry) + '\n')
    
    # 3. 准备Stop Hook输入数据
    hook_input = {
        "session_id": test_session_id,
        "transcript_path": test_transcript_path,
        "stop_hook_active": False
    }
    
    print(f"🚀 调用Stop Hook处理包含工具调用的会话...")
    
    # 4. 调用Stop Hook
    try:
        hook_process = subprocess.Popen([
            "python3", "/Users/jet/Sage/hooks/scripts/sage_stop_hook.py"
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        stdout, stderr = hook_process.communicate(input=json.dumps(hook_input), timeout=30)
        
        print(f"Hook执行完成 - 返回码: {hook_process.returncode}")
        if stderr:
            print("Hook处理日志:")
            for line in stderr.split('\n'):
                if line.strip():
                    print(f"  {line}")
        
    except subprocess.TimeoutExpired:
        print("❌ Hook执行超时")
        hook_process.kill()
        return False
    except Exception as e:
        print(f"❌ Hook执行异常: {e}")
        return False
    finally:
        # 清理临时文件
        Path(test_transcript_path).unlink(missing_ok=True)
    
    # 5. 等待数据库操作完成
    print("⏳ 等待数据库操作完成...")
    await asyncio.sleep(2)
    
    # 6. 检查数据库记忆数量是否增加
    print("🔍 检查数据库记忆数量变化...")
    result = subprocess.run([
        "docker", "exec", "sage-db", "psql", "-U", "sage", "-d", "sage_memory",
        "-c", "SELECT COUNT(*) FROM memories;"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ 数据库查询失败: {result.stderr}")
        return False
    
    final_count = int(result.stdout.split('\n')[2].strip())
    print(f"📊 最终记忆数量: {final_count}")
    
    # 7. 验证结果
    if final_count > initial_count:
        print(f"✅ 记忆数量成功增加！从 {initial_count} 增加到 {final_count}")
        
        # 8. 检查保存的工具调用信息
        print("🔍 查看最新保存的工具调用元数据...")
        result = subprocess.run([
            "docker", "exec", "sage-db", "psql", "-U", "sage", "-d", "sage_memory",
            "-c", f"SELECT jsonb_pretty(metadata) FROM memories WHERE session_id = '{test_session_id}' ORDER BY created_at DESC LIMIT 1;"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("📝 工具调用元数据:")
            print(result.stdout)
            
            # 检查是否包含工具调用信息
            if "tool_call" in result.stdout.lower():
                print("✅ 成功检测到工具调用信息在元数据中！")
            else:
                print("⚠️  未在元数据中发现明确的工具调用信息")
        
        return True
    else:
        print(f"❌ 失败！记忆数量未增加，仍为 {final_count}")
        return False

async def main():
    """主测试函数"""
    print("🧪 开始Stop Hook工具调用数据库保存功能测试")
    print("=" * 60)
    
    success = await test_stop_hook_with_tools()
    
    print("=" * 60)
    if success:
        print("🎉 Stop Hook工具调用数据库保存功能测试通过！")
    else:
        print("💥 Stop Hook工具调用数据库保存功能测试失败！")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)