#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sage Stop Hook (轻量级版本)
使用 Unix Socket 与守护进程通信，避免重复初始化
"""
import sys
import os
import json
import logging
import time
from typing import Dict, Any, Optional

# 导入HookExecutionContext
sys.path.insert(0, str(Path(__file__).parent.parent))
from context import create_hook_context

# 使用HookExecutionContext后设置Python路径
from pathlib import Path

# 需要在create_hook_context后才能导入sage_client
# from sage_client import SageClient, is_daemon_running

# 配置日志
logger = logging.getLogger(__name__)


def extract_conversation_from_file(file_path: str) -> Optional[Dict[str, Any]]:
    """从文件中提取对话内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 查找用户输入和助手响应
        user_input = None
        assistant_response = []
        in_assistant_section = False
        
        for line in lines:
            if line.startswith("Human:"):
                user_input = line[6:].strip()
            elif line.startswith("Assistant:"):
                in_assistant_section = True
                assistant_response.append(line[10:].strip())
            elif in_assistant_section and line.strip():
                assistant_response.append(line.strip())
        
        if user_input and assistant_response:
            return {
                "user_input": user_input,
                "assistant_response": "\n".join(assistant_response)
            }
    
    except Exception as e:
        logger.error(f"解析文件失败: {e}")
    
    return None


class LightweightSageStopHook:
    """轻量级Sage Stop Hook - HookExecutionContext架构版本"""
    
    def __init__(self):
        # 创建执行上下文
        self.context = create_hook_context(__file__)
    
    def save_to_sage(self, conversation: Dict[str, Any]) -> bool:
        """保存对话到 Sage"""
        start_time = time.time()
        
        try:
            # 设置Python路径
            self.context.setup_python_path()
            
            # 现在可以安全导入sage_client
            from sage_client import SageClient, is_daemon_running
            
            # 检查守护进程状态
            if not is_daemon_running():
                logger.error("Sage 守护进程未运行")
                # 可以选择启动守护进程或回退到直接调用
                return False
            
            # 使用客户端保存
            with SageClient(timeout=10.0) as client:
                response = client.save_memory(
                    user_input=conversation["user_input"],
                    assistant_response=conversation["assistant_response"],
                    metadata={
                        "source": "stop_hook_lightweight",
                        "timestamp": time.time(),
                        "processing_time": time.time() - start_time
                    }
            )
            
            if response.get('status') == 'ok':
                logger.info(f"对话已保存到 Sage (耗时: {time.time() - start_time:.3f}秒)")
                logger.info(f"记忆ID: {response.get('memory_id')}")
                return True
            else:
                logger.error(f"保存失败: {response.get('message')}")
                return False
                
    except Exception as e:
        logger.error(f"保存到 Sage 失败: {e}")
        return False


def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 检查参数
    if len(sys.argv) < 2:
        logger.error("用法: sage_stop_hook_lightweight.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # 提取对话
    conversation = extract_conversation_from_file(file_path)
    if not conversation:
        logger.warning("未找到有效的对话内容")
        sys.exit(0)
    
    # 创建轻量级hook实例
    hook = LightweightSageStopHook()
    
    logger.info(f"提取到对话: 用户输入长度={len(conversation['user_input'])}, "
                f"助手响应长度={len(conversation['assistant_response'])}")
    
    # 保存到 Sage
    success = hook.save_to_sage(conversation)
    
    # 返回状态码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()