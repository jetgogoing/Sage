#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sage Stop Hook (简化版)
直接初始化SageCore，保存完整的对话数据（包括工具调用）
为个人使用优化：简单、稳定、数据完整
"""
import sys
import os
import json
import logging
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sage_core.singleton_manager import get_sage_core
from sage_core.interfaces import MemoryContent
from sage_core.interfaces.turn import Turn, ToolCall
try:
    from hook_data_aggregator import HookDataAggregator
except ImportError:
    # 尝试从相对路径导入
    import sys
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    from hook_data_aggregator import HookDataAggregator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleSageStopHook:
    """简化的Stop Hook - 直接保存完整对话"""
    
    def __init__(self):
        self.aggregator = HookDataAggregator()
        
    def extract_conversation_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """从文件中提取对话内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取Human和Assistant部分
            lines = content.split('\n')
            user_input = None
            assistant_response = []
            in_assistant = False
            
            for line in lines:
                if line.startswith("Human:"):
                    user_input = line[6:].strip()
                elif line.startswith("Assistant:"):
                    in_assistant = True
                    # Assistant: 后面可能直接有内容
                    remaining = line[10:].strip()
                    if remaining:
                        assistant_response.append(remaining)
                elif in_assistant and line.strip():
                    assistant_response.append(line.strip())
            
            if user_input and assistant_response:
                return {
                    "user_input": user_input,
                    "assistant_response": "\n".join(assistant_response)
                }
                
        except Exception as e:
            logger.error(f"解析对话文件失败: {e}")
        
        return None
    
    async def save_complete_turn(self, conversation: Dict[str, Any], 
                                tool_calls: List[ToolCall]) -> bool:
        """保存完整的对话轮次"""
        start_time = time.time()
        
        try:
            logger.info("正在初始化SageCore（预计3-5秒）...")
            
            # 直接初始化SageCore - 简单可靠
            sage_core = await get_sage_core()
            
            init_time = time.time() - start_time
            logger.info(f"SageCore初始化完成，耗时: {init_time:.2f}秒")
            
            # 创建Turn对象
            turn = Turn(
                session_id=sage_core.memory_manager.current_session_id,
                user_prompt=conversation["user_input"],
                tool_calls=tool_calls,
                final_response=conversation["assistant_response"],
                metadata={
                    "source": "stop_hook_simple",
                    "init_time": init_time,
                    "total_processing_time": None  # 将在最后更新
                }
            )
            
            # 构建存储内容
            # 为了向后兼容，我们同时保存传统格式和新的Turn格式
            content = MemoryContent(
                user_input=turn.user_prompt,
                assistant_response=turn.final_response,
                metadata={
                    "turn_id": turn.turn_id,
                    "tool_calls": [tc.to_dict() for tc in turn.tool_calls],
                    "tool_count": len(turn.tool_calls),
                    "has_tools": len(turn.tool_calls) > 0,
                    **turn.metadata
                }
            )
            
            # 保存到数据库
            memory_id = await sage_core.save_memory(content)
            
            total_time = time.time() - start_time
            
            logger.info(f"对话已完整保存到Sage")
            logger.info(f"- 记忆ID: {memory_id}")
            logger.info(f"- 工具调用数: {len(turn.tool_calls)}")
            logger.info(f"- 总耗时: {total_time:.2f}秒")
            
            # 如果有工具调用，记录详情
            if turn.tool_calls:
                logger.info("工具调用详情:")
                for tc in turn.tool_calls:
                    logger.info(f"  - {tc.tool_name}: {tc.status}")
            
            return True
            
        except Exception as e:
            logger.error(f"保存完整对话失败: {e}")
            logger.exception("详细错误信息:")
            return False
    
    async def process(self, file_path: str) -> bool:
        """处理Hook"""
        logger.info("=== Sage Stop Hook (简化版) 开始处理 ===")
        
        # 1. 提取基本对话
        conversation = self.extract_conversation_from_file(file_path)
        if not conversation:
            logger.warning("未找到有效的对话内容")
            return False
        
        logger.info(f"提取到对话: 用户输入长度={len(conversation['user_input'])}, "
                   f"助手响应长度={len(conversation['assistant_response'])}")
        
        # 2. 聚合工具调用数据
        logger.info("正在聚合工具调用数据...")
        tool_calls = self.aggregator.aggregate_current_session()
        
        if tool_calls:
            logger.info(f"找到 {len(tool_calls)} 个工具调用")
            for tc in tool_calls:
                logger.info(f"  - {tc.tool_name} ({tc.status})")
        else:
            logger.info("本次对话没有工具调用")
        
        # 3. 保存完整数据
        success = await self.save_complete_turn(conversation, tool_calls)
        
        # 4. 清理临时文件（可选）
        if success and tool_calls:
            cleaned = self.aggregator.cleanup_processed_files(tool_calls)
            if cleaned > 0:
                logger.info(f"清理了 {cleaned} 个临时文件")
        
        logger.info(f"=== 处理完成，状态: {'成功' if success else '失败'} ===")
        return success


def main():
    """主函数"""
    # 支持两种调用方式：
    # 1. 作为Stop Hook被调用（从stdin读取JSON）
    # 2. 直接传入文件路径（用于测试）
    
    if len(sys.argv) > 1:
        # 测试模式：直接传入文件路径
        file_path = sys.argv[1]
    else:
        # Hook模式：从stdin读取
        try:
            input_data = json.load(sys.stdin)
            file_path = input_data.get('conversationFile')
            
            if not file_path:
                logger.error("输入数据中缺少conversationFile字段")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"读取输入数据失败: {e}")
            sys.exit(1)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        logger.error(f"对话文件不存在: {file_path}")
        sys.exit(1)
    
    # 创建Hook实例
    hook = SimpleSageStopHook()
    
    # 运行异步处理
    success = asyncio.run(hook.process(file_path))
    
    # 返回状态码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()