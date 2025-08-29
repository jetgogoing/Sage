#!/usr/bin/env python3
"""
Sage MCP 会话存储功能全链路测试
验证 PreToolUse -> PostToolUse -> Stop Hook 完整链路的会话存储功能

测试重点:
1. PreToolUse Hook: 捕获工具调用前的完整思维链
2. PostToolUse Hook: 捕获工具调用后的反馈和结果  
3. Stop Hook: 调用sage_core脚本存储到Docker数据库
4. 纯文本数据存储验证
5. 向量化数据存储验证
"""

import json
import sys
import subprocess
import tempfile
import time
import asyncio
import uuid
import os
from pathlib import Path
from typing import Dict, Any, List

# 添加项目路径
sys.path.insert(0, os.getenv('SAGE_HOME', '.'))

class SageMCPFullChainTest:
    """Sage MCP 全链路测试类"""
    
    def __init__(self):
        self.test_session_id = f"test-session-{int(time.time())}"
        self.temp_dir = Path.home() / '.sage_hooks_temp'
        self.temp_dir.mkdir(exist_ok=True)
        
        # Hook脚本路径
        self.pre_tool_script = os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_pre_tool_capture.py")
        self.post_tool_script = os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_post_tool_capture.py")
        self.stop_hook_script = os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts", "sage_stop_hook.py")
        
        print(f"🧪 初始化测试环境 - Session ID: {self.test_session_id}")
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        for temp_file in self.temp_dir.glob(f"*{self.test_session_id}*"):
            try:
                temp_file.unlink()
            except:
                pass
    
    async def test_pre_tool_capture(self) -> Dict[str, Any]:
        """测试 PreToolUse Hook 功能"""
        print("\n📝 测试 PreToolUse Hook...")
        
        # 模拟工具调用前的数据
        pre_tool_input = {
            "session_id": self.test_session_id,
            "tool_name": "mcp__zen__debug",
            "tool_input": {
                "step": "开始调试数据库连接问题",
                "hypothesis": "可能是连接池配置问题",
                "confidence": "exploring"
            },
            "user": "test_user",
            "environment": {
                "python_version": "3.11",
                "platform": "darwin"
            }
        }
        
        try:
            # 调用 PreToolUse Hook
            process = subprocess.run([
                "python3", self.pre_tool_script
            ], input=json.dumps(pre_tool_input), 
               text=True, capture_output=True, timeout=10)
            
            if process.returncode != 0:
                print(f"❌ PreToolUse Hook 执行失败: {process.stderr}")
                return {"success": False, "error": process.stderr}
            
            result = json.loads(process.stdout.strip())
            print(f"✅ PreToolUse Hook 成功: {result}")
            
            # 验证临时文件是否创建
            call_id = result.get("call_id")
            if call_id:
                temp_file = self.temp_dir / f"pre_{call_id}.json"
                if temp_file.exists():
                    print(f"✅ 临时文件已创建: {temp_file.name}")
                    return {"success": True, "call_id": call_id, "temp_file": str(temp_file)}
                else:
                    print(f"❌ 临时文件未找到: {temp_file}")
                    return {"success": False, "error": "临时文件未创建"}
            else:
                return {"success": False, "error": "未返回call_id"}
                
        except Exception as e:
            print(f"❌ PreToolUse Hook 测试异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_post_tool_capture(self, call_id: str) -> Dict[str, Any]:
        """测试 PostToolUse Hook 功能"""
        print("\n📝 测试 PostToolUse Hook...")
        
        # 模拟工具调用后的数据
        post_tool_input = {
            "session_id": self.test_session_id,
            "tool_name": "mcp__zen__debug",
            "tool_response": {
                "status": "debug_completed",
                "findings": "发现数据库连接池配置不当，max_connections设置过低",
                "confidence": "high",
                "model_used": "gemini-2.5-pro",
                "content": "经过调试分析，问题出现在PostgreSQL连接池配置上..."
            },
            "execution_time_ms": 1250,
            "is_error": False
        }
        
        try:
            # 调用 PostToolUse Hook
            process = subprocess.run([
                "python3", self.post_tool_script
            ], input=json.dumps(post_tool_input),
               text=True, capture_output=True, timeout=10)
            
            if process.returncode != 0:
                print(f"❌ PostToolUse Hook 执行失败: {process.stderr}")
                return {"success": False, "error": process.stderr}
            
            result = json.loads(process.stdout.strip())
            print(f"✅ PostToolUse Hook 成功: {result}")
            
            # 验证完整记录文件是否创建
            complete_file = self.temp_dir / f"complete_{call_id}.json"
            if complete_file.exists():
                print(f"✅ 完整记录文件已创建: {complete_file.name}")
                
                # 读取并验证文件内容
                with open(complete_file, 'r') as f:
                    complete_data = json.load(f)
                
                if ("pre_call" in complete_data and 
                    "post_call" in complete_data and
                    complete_data.get("call_id") == call_id):
                    print("✅ 完整记录数据结构正确")
                    return {"success": True, "complete_file": str(complete_file), "data": complete_data}
                else:
                    print("❌ 完整记录数据结构不正确")
                    return {"success": False, "error": "数据结构不正确"}
            else:
                print(f"❌ 完整记录文件未找到: {complete_file}")
                return {"success": False, "error": "完整记录文件未创建"}
                
        except Exception as e:
            print(f"❌ PostToolUse Hook 测试异常: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_stop_hook_database_storage(self) -> Dict[str, Any]:
        """测试 Stop Hook 数据库存储功能"""
        print("\n📝 测试 Stop Hook 数据库存储...")
        
        # 创建模拟的对话数据
        conversation_content = f"""Human: 请帮我调试一个数据库连接问题，连接经常超时。