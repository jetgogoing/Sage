#!/usr/bin/env python3
"""
Sage Archiver Hook
用于 Claude Code CLI Stop Hook 的对话归档脚本

作用：
1. 在对话结束时触发
2. 提取完整的对话内容
3. 调用 Sage MCP Server 的 S (Save) 工具进行归档
4. 实现对话的持久化存储和知识管理
"""

import json
import os
import sys
import subprocess
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# 导入HookExecutionContext
sys.path.insert(0, str(Path(__file__).parent.parent))
from context import create_hook_context

from security_utils import path_validator, input_validator, resource_limiter, SecurityError


class SageArchiver:
    """Sage 对话归档器 - HookExecutionContext架构版本"""
    
    def __init__(self):
        # 创建执行上下文
        self.context = create_hook_context(__file__)
        
        self.timeout = 30  # 归档操作超时时间
        self.setup_logging()
    
    def setup_logging(self):
        """设置日志配置 - 使用HookExecutionContext"""
        # 使用上下文提供的标准化日志设置
        self.logger = self.context.setup_logging(
            logger_name='SageArchiver',
            log_filename='archiver.log'
        )
        self.logger.setLevel(logging.DEBUG)
    
    def parse_input(self) -> Dict[str, Any]:
        """解析 Hook 输入数据"""
        try:
            # 安全地读取和验证输入
            raw_input = sys.stdin.read()
            if not raw_input:
                self.logger.warning("Empty input received")
                return {}
            
            # 使用安全验证器验证输入
            input_data = input_validator.validate_json_input(raw_input, max_size=1024*1024)  # 1MB 限制
            
            # 验证 session_id
            session_id = input_data.get('session_id', '')
            if session_id:
                try:
                    input_validator.validate_session_id(session_id)
                except SecurityError as e:
                    self.logger.error(f"Invalid session_id: {e}")
                    return {}
            
            self.logger.info(f"Received Stop hook input: session_id={input_data.get('session_id', 'unknown')}")
            return input_data
            
        except SecurityError as e:
            self.logger.error(f"Security validation failed: {e}")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse input JSON: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Unexpected error parsing input: {e}")
            return {}
    
    def validate_transcript_path(self, transcript_path: str) -> bool:
        """验证 transcript 文件路径的有效性"""
        if not transcript_path:
            self.logger.warning("No transcript path provided")
            return False
        
        try:
            # 使用安全验证器验证路径
            validated_path = path_validator.validate_transcript_path(transcript_path)
            if not validated_path:
                return False
                
            # 检查文件大小
            resource_limiter.limit_file_operations(validated_path, max_size=100*1024*1024)  # 100MB 限制
            
            return True
            
        except SecurityError as e:
            self.logger.error(f"Transcript path validation failed: {e}")
            return False
    
    def extract_last_conversation(self, transcript_path: str) -> Optional[Tuple[str, str]]:
        """提取最后一轮对话 (user_prompt, assistant_response)"""
        try:
            # 使用安全验证器验证路径
            validated_path = path_validator.validate_transcript_path(transcript_path)
            if not validated_path:
                return None
            
            # 使用资源限制器安全读取文件
            resource_limiter.limit_file_operations(validated_path, max_size=100*1024*1024)  # 100MB 限制
            lines = resource_limiter.safe_read_lines(validated_path, max_lines=1000)  # 最多1000行
            
            if not lines:
                self.logger.warning("No content in transcript file")
                return None
            
            # 解析 Claude CLI JSONL 格式，查找最后一轮对话
            user_message = None
            assistant_message = None
            
            # 从后往前查找最近的用户消息和助手回复
            for line in reversed(lines):
                try:
                    entry = json.loads(line)
                    entry_type = entry.get('type', '')
                    
                    # Claude CLI 格式：assistant 消息
                    if entry_type == 'assistant' and assistant_message is None:
                        message = entry.get('message', {})
                        if message.get('role') == 'assistant':
                            content_list = message.get('content', [])
                            # 提取文本内容
                            text_content = []
                            for content_item in content_list:
                                if isinstance(content_item, dict) and content_item.get('type') == 'text':
                                    text_content.append(content_item.get('text', ''))
                            
                            if text_content:
                                full_content = '\n'.join(text_content)
                                assistant_message = input_validator.sanitize_string(full_content, max_length=50000)
                    
                    # Claude CLI 格式：user 消息  
                    elif entry_type == 'user' and user_message is None:
                        message = entry.get('message', {})
                        if message.get('role') == 'user':
                            content_list = message.get('content', [])
                            # 提取文本内容
                            text_content = []
                            for content_item in content_list:
                                if isinstance(content_item, dict) and content_item.get('type') == 'text':
                                    text_content.append(content_item.get('text', ''))
                            
                            if text_content:
                                full_content = '\n'.join(text_content)
                                user_message = input_validator.sanitize_string(full_content, max_length=10000)
                    
                    # 找到一对完整的对话后停止
                    if user_message and assistant_message:
                        break
                        
                except json.JSONDecodeError:
                    continue
            
            if user_message and assistant_message:
                self.logger.info(f"Extracted conversation pair: user({len(user_message)} chars), assistant({len(assistant_message)} chars)")
                return (user_message, assistant_message)
            else:
                self.logger.warning("Could not find complete conversation pair")
                return None
                
        except SecurityError as e:
            self.logger.error(f"Security validation failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting conversation from {transcript_path}: {e}")
            return None
    
    def call_sage_save(self, session_id: str, user_prompt: str, assistant_response: str) -> bool:
        """调用 Sage MCP Server 的 S (Save) 工具归档对话"""
        try:
            # 构建元数据
            metadata = {
                'session_id': session_id,
                'timestamp': time.time(),
                'source': 'claude-cli-hook',
                'turn_count': 1,
                'user_prompt_length': len(user_prompt),
                'assistant_response_length': len(assistant_response)
            }
            
            self.logger.info(f"Archiving conversation for session {session_id}")
            
            # 调用真实的 Sage Core 进行数据库持久化
            success = self._call_real_sage_core(user_prompt, assistant_response, metadata)
            
            if success:
                # 数据库保存成功后，执行本地备份作为冗余保护
                self._simulate_sage_save(user_prompt, assistant_response, metadata)
                self.logger.info(f"Successfully archived conversation for session {session_id}")
                return True
            else:
                # 数据库保存失败，仍执行本地备份
                self._simulate_sage_save(user_prompt, assistant_response, metadata)
                self.logger.error(f"Failed to archive conversation to database for session {session_id}, but backup saved locally")
                return False
                
        except Exception as e:
            # 异常情况下仍执行本地备份
            self._simulate_sage_save(user_prompt, assistant_response, metadata)
            self.logger.error(f"Error calling Sage MCP Save: {e}")
            return False
    
    def _call_real_sage_core(self, user_prompt: str, assistant_response: str, metadata: Dict[str, Any]) -> bool:
        """真实的 Sage Core 调用 - 直接调用sage_core.save_memory - 使用HookExecutionContext"""
        start_time = time.time()
        try:
            # 使用上下文设置Python路径
            self.context.setup_python_path()
            
            import asyncio
            
            async def save_to_sage_core():
                from sage_core.singleton_manager import get_sage_core
                from sage_core.interfaces.core_service import MemoryContent
                
                # 使用上下文获取配置
                config = self.context.get_sage_config()
                
                sage = await get_sage_core()
                await sage.initialize(config)
                
                # 构建MemoryContent对象
                content = MemoryContent(
                    user_input=user_prompt,
                    assistant_response=assistant_response,
                    metadata=metadata,
                    session_id=metadata.get('session_id')
                )
                
                # 保存到数据库并向量化
                memory_id = await sage.save_memory(content)
                return memory_id is not None and memory_id != ""
            
            # 运行异步调用
            try:
                # 检查是否存在运行中的事件循环
                try:
                    loop = asyncio.get_running_loop()
                    loop_running = True
                except RuntimeError:
                    loop_running = False
                
                if loop_running:
                    # 如果已经在事件循环中，创建新任务
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, save_to_sage_core())
                        result = future.result(timeout=self.timeout)
                        execution_time = time.time() - start_time
                        self.logger.info(f"Direct sage_core save successful: memory saved to database in {execution_time:.2f}s")
                        return result
                else:
                    # 如果没有运行的事件循环，直接运行
                    result = asyncio.run(save_to_sage_core())
                    execution_time = time.time() - start_time
                    self.logger.info(f"Direct sage_core save successful: memory saved to database in {execution_time:.2f}s")
                    return result
            except Exception as e:
                execution_time = time.time() - start_time
                self.logger.error(f"Direct sage_core save failed after {execution_time:.2f}s: {e}")
                return False
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Real Sage Core call failed after {execution_time:.2f}s: {e}")
            return False

    def _simulate_sage_save(self, user_prompt: str, assistant_response: str, metadata: Dict[str, Any]) -> bool:
        """本地备份完整交互数据 - 使用HookExecutionContext"""
        try:
            # 使用上下文获取备份目录
            backup_dir = self.context.get_backup_dir()
            
            backup_data = {
                'timestamp': metadata['timestamp'],
                'session_id': metadata['session_id'],
                'user_prompt': user_prompt,
                'assistant_response': assistant_response,
                'metadata': metadata
            }
            
            backup_file = backup_dir / f"conversation_{int(metadata['timestamp'])}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Backup saved to {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in simulated save: {e}")
            return False
    
    def check_stop_hook_active(self, input_data: Dict[str, Any]) -> bool:
        """检查是否处于 stop_hook_active 状态，防止死循环"""
        stop_hook_active = input_data.get('stop_hook_active', False)
        if stop_hook_active:
            self.logger.warning("stop_hook_active is True, skipping to prevent infinite loop")
            return True
        return False
    
    def run(self) -> None:
        """主运行逻辑"""
        start_time = time.time()
        
        try:
            # 解析输入
            input_data = self.parse_input()
            if not input_data:
                sys.exit(1)  # 使用错误码表示失败
            
            # 检查死循环防护
            if self.check_stop_hook_active(input_data):
                sys.exit(1)
            
            session_id = input_data.get('session_id', '')
            transcript_path = input_data.get('transcript_path', '')
            
            if not session_id:
                self.logger.warning("No session_id provided")
                sys.exit(1)
            
            # 验证 session_id
            try:
                input_validator.validate_session_id(session_id)
            except SecurityError as e:
                self.logger.error(f"Invalid session_id: {e}")
                sys.exit(1)
            
            # 验证 transcript 文件
            if not self.validate_transcript_path(transcript_path):
                sys.exit(1)
            
            # 提取最后一轮对话
            conversation = self.extract_last_conversation(transcript_path)
            if not conversation:
                self.logger.warning("No conversation to archive")
                sys.exit(1)
            
            user_prompt, assistant_response = conversation
            
            # 调用 Sage MCP 归档
            success = self.call_sage_save(session_id, user_prompt, assistant_response)
            
            execution_time = time.time() - start_time
            if success:
                self.logger.info(f"Archiving completed successfully in {execution_time:.2f}s")
            else:
                self.logger.error(f"Archiving failed after {execution_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Unexpected error in main execution: {e}")
            sys.exit(1)  # 使用错误码表示失败


def main():
    """入口函数"""
    archiver = SageArchiver()
    archiver.run()


if __name__ == "__main__":
    main()