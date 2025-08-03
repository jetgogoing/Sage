#!/usr/bin/env python3
"""
测试Stop Hook的数据库保存功能
验证修复后的Stop Hook能否正确调用sage_core进行数据库持久化
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

async def test_stop_hook_database_save():
    """测试Stop Hook的数据库保存功能"""
    
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
    
    # 2. 创建模拟Claude CLI transcript文件
    print("📝 创建模拟transcript文件...")
    test_data = {
        "session_id": "test-session-12345",
        "user_message": "这是一个Stop Hook数据库保存功能测试",
        "assistant_response": "我明白了，这是测试Stop Hook是否能将对话正确保存到数据库并进行向量化存储的功能验证。"
    }
    
    # 创建Claude CLI格式的JSONL文件在允许的目录
    test_transcript_path = "/Users/jet/Sage/tests/integration/test_transcript.jsonl"
    with open(test_transcript_path, 'w', encoding='utf-8') as f:
        # 用户消息
        user_entry = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": test_data["user_message"]}]
            }
        }
        f.write(json.dumps(user_entry) + '\n')
        
        # 助手回复
        assistant_entry = {
            "type": "assistant", 
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": test_data["assistant_response"]}]
            }
        }
        f.write(json.dumps(assistant_entry) + '\n')
        
        transcript_path = test_transcript_path
    
    # 3. 准备Stop Hook输入数据
    hook_input = {
        "session_id": test_data["session_id"],
        "transcript_path": transcript_path,
        "stop_hook_active": False
    }
    
    print(f"🚀 调用Stop Hook进行数据库保存测试...")
    
    # 4. 调用Stop Hook
    try:
        hook_process = subprocess.Popen([
            "python3", "/Users/jet/Sage/hooks/scripts/sage_stop_hook.py"
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        stdout, stderr = hook_process.communicate(input=json.dumps(hook_input), timeout=30)
        
        print(f"Hook执行完成 - 返回码: {hook_process.returncode}")
        if stderr:
            print(f"Hook stderr: {stderr}")
        
    except subprocess.TimeoutExpired:
        print("❌ Hook执行超时")
        hook_process.kill()
        return False
    except Exception as e:
        print(f"❌ Hook执行异常: {e}")
        return False
    finally:
        # 清理临时文件
        Path(transcript_path).unlink(missing_ok=True)
    
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
        print(f"✅ 成功！记忆数量从 {initial_count} 增加到 {final_count}")
        
        # 8. 查看最新保存的记忆内容
        print("🔍 查看最新保存的记忆...")
        result = subprocess.run([
            "docker", "exec", "sage-db", "psql", "-U", "sage", "-d", "sage_memory",
            "-c", "SELECT user_input, assistant_response, created_at FROM memories ORDER BY created_at DESC LIMIT 1;"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("📝 最新记忆内容:")
            print(result.stdout)
        
        return True
    else:
        print(f"❌ 失败！记忆数量未增加，仍为 {final_count}")
        return False

async def main():
    """主测试函数"""
    print("🧪 开始Stop Hook数据库保存功能测试")
    print("=" * 50)
    
    success = await test_stop_hook_database_save()
    
    print("=" * 50)
    if success:
        print("🎉 Stop Hook数据库保存功能测试通过！")
    else:
        print("💥 Stop Hook数据库保存功能测试失败！")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)