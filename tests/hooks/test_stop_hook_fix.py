#!/usr/bin/env python3
"""
测试 Sage Stop Hook 修复后的功能
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

def test_stop_hook_fix():
    """测试修复后的 Stop Hook"""
    print("🧪 测试 Stop Hook 修复...")
    
    # 创建模拟的 Claude CLI transcript
    test_transcript = Path(tempfile.mkdtemp()) / "test_transcript.jsonl"
    
    with open(test_transcript, 'w', encoding='utf-8') as f:
        # 用户消息
        user_entry = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "测试消息：这是用户输入"}]
            },
            "timestamp": time.time() - 1
        }
        f.write(json.dumps(user_entry) + '\n')
        
        # 助手消息
        assistant_entry = {
            "type": "assistant",
            "message": {
                "role": "assistant", 
                "content": [{"type": "text", "text": "测试回复：这是助手回复，包含修复验证内容"}]
            },
            "timestamp": time.time()
        }
        f.write(json.dumps(assistant_entry) + '\n')
    
    # 准备输入数据
    hook_input = {
        "session_id": f"fix-test-{int(time.time())}",
        "transcript_path": str(test_transcript),  # 确保是字符串
        "stop_hook_active": False
    }
    
    try:
        # 调用修复后的 Stop Hook
        process = subprocess.run([
            "python3", "/Users/jet/Sage/hooks/scripts/sage_stop_hook.py"
        ], input=json.dumps(hook_input), text=True, capture_output=True, timeout=30)
        
        print(f"返回码: {process.returncode}")
        print(f"stdout: {process.stdout}")
        if process.stderr:
            print(f"stderr: {process.stderr}")
        
        # 检查是否修复成功
        if process.returncode == 0:
            print("✅ Stop Hook 执行成功！修复生效")
            return True
        else:
            print("❌ Stop Hook 仍然失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False
    finally:
        # 清理测试文件
        try:
            test_transcript.unlink()
            test_transcript.parent.rmdir()
        except:
            pass

if __name__ == "__main__":
    success = test_stop_hook_fix()
    sys.exit(0 if success else 1)
