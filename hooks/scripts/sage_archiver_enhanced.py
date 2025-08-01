#!/usr/bin/env python3
"""
Enhanced Sage Archiver Hook (HookExecutionContext版本)
增强版对话归档脚本，使用统一的HookExecutionContext架构

Phase 2 重构目标:
1. 使用HookExecutionContext替代硬编码路径管理
2. 统一配置获取和环境检测逻辑
3. 保持原有功能完全不变
4. 提供更好的跨平台兼容性和可维护性
"""

import json
import sys
import subprocess
import logging
import time
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# 导入HookExecutionContext
sys.path.insert(0, str(Path(__file__).parent.parent))
from context import create_hook_context

# 尝试导入简化版security_utils，如果失败则定义基本验证
try:
    from security_utils_simple import SimplifiedSecurityUtils as SecurityUtils
except ImportError:
    # 定义基本的安全工具类
    class SecurityUtils:
        @staticmethod
        def validate_basic_input(input_str: str, max_length: int = 100000) -> str:
            if not input_str:
                return ""
            if len(input_str) > max_length:
                return input_str[:max_length]
            return input_str

# 导入数据聚合器
try:
    from hook_data_aggregator import get_aggregator
    has_aggregator = True
except ImportError:
    has_aggregator = False

# 设置默认编码
import locale
locale.setlocale(locale.LC_ALL, '')

class EnhancedSageArchiver:
    """增强版Sage对话归档器 - HookExecutionContext架构版本"""
    
    def __init__(self):
        # 创建执行上下文
        self.context = create_hook_context(__file__)
        
        self.timeout = 30  # 归档操作超时时间
        self.setup_logging()
        
        # 添加项目标识
        self.project_id = self.get_project_id()
        self.project_name = self.context.project_root.name
        self.logger.info(f"EnhancedSageArchiver initialized for project: {self.project_name} (ID: {self.project_id})")
        
    def get_project_id(self) -> str:
        """获取当前项目的唯一标识"""
        project_root_str = str(self.context.project_root)
        project_name = self.context.project_root.name
        hash_suffix = hashlib.md5(project_root_str.encode()).hexdigest()[:8]
        return f"{project_name}_{hash_suffix}"
    
    def enhance_metadata_with_project(self, metadata: Dict) -> Dict:
        """为元数据添加项目信息"""
        metadata['project_id'] = self.project_id
        metadata['project_name'] = self.project_name
        metadata['project_path'] = str(self.context.project_root)
        metadata['cross_project_session'] = True  # 标记为跨项目共享会话
        return metadata
        
    def setup_logging(self):
        """设置日志配置 - 使用HookExecutionContext"""
        # 使用上下文提供的标准化日志设置
        self.logger = self.context.setup_logging(
            logger_name='EnhancedSageArchiver',
            log_filename='archiver_enhanced.log'
        )
        self.logger.setLevel(logging.DEBUG)
    
    def extract_complete_interaction(self, transcript_path: str) -> Tuple[Optional[str], Optional[str], List[Dict], List[Dict]]:
        """
        从transcript文件中提取完整的交互数据，支持思维链和完整会话历史
        返回: (user_message, assistant_message, tool_calls, tool_results)
        """
        if not Path(transcript_path).exists():
            self.logger.warning(f"Transcript file not found: {transcript_path}")
            return None, None, [], []
        
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            user_message = None
            assistant_message = None
            tool_calls = []
            tool_results = []
            
            # 从最后一行开始向前查找，寻找最后一组完整交互
            for line in reversed(lines):
                if not line.strip():
                    continue
                    
                try:
                    entry = json.loads(line.strip())
                    entry_type = entry.get('type', '')
                    
                    # 提取assistant消息
                    if entry_type == 'assistant' and assistant_message is None:
                        message = entry.get('message', {})
                        if message.get('role') == 'assistant':
                            content_parts = []
                            content_list = message.get('content', [])
                            
                            for content_item in content_list:
                                if isinstance(content_item, dict):
                                    if content_item.get('type') == 'text':
                                        text_content = content_item.get('text', '')
                                        if text_content:
                                            content_parts.append(text_content)
                                    elif content_item.get('type') == 'tool_use':
                                        # 记录工具调用
                                        tool_calls.append({
                                            'tool_name': content_item.get('name', ''),
                                            'tool_input': content_item.get('input', {}),
                                            'tool_use_id': content_item.get('id', '')
                                        })
                            
                            if content_parts:
                                assistant_message = '\n'.join(content_parts)
                    
                    # 提取tool_result
                    elif entry_type == 'tool_result':
                        message = entry.get('message', {})
                        if message.get('role') == 'user':
                            content_list = message.get('content', [])
                            for content_item in content_list:
                                if isinstance(content_item, dict) and content_item.get('type') == 'tool_result':
                                    tool_results.append({
                                        'tool_use_id': content_item.get('tool_use_id', ''),
                                        'content': content_item.get('content', ''),
                                        'is_error': content_item.get('is_error', False)
                                    })
                    
                    # 提取user消息 - 修复：支持缺少type字段和字符串content的情况
                    elif user_message is None:
                        message = entry.get('message', {})
                        # 检查是否为用户消息：entry_type == 'user' 或者 缺少type但role='user'
                        is_user_message = (entry_type == 'user') or (not entry_type and message.get('role') == 'user')
                        
                        if is_user_message:
                            content_parts = []
                            content = message.get('content', [])
                            
                            # 修复：支持content为字符串或列表的情况
                            if isinstance(content, str):
                                # content是字符串的情况（如hook触发的消息）
                                if content.strip():
                                    content_parts.append(content)
                            elif isinstance(content, list):
                                # content是列表的情况（标准格式）
                                for content_item in content:
                                    if isinstance(content_item, dict) and content_item.get('type') == 'text':
                                        text_content = content_item.get('text', '')
                                        if text_content:
                                            content_parts.append(text_content)
                            
                            if content_parts:
                                user_message = '\n'.join(content_parts)
                    
                    # 如果找到了用户消息和助手消息，就停止查找
                    if user_message and assistant_message:
                        break
                        
                except json.JSONDecodeError:
                    continue
            
            # 清理和验证数据
            if user_message:
                user_message = SecurityUtils.validate_basic_input(user_message, 50000)
            if assistant_message:
                assistant_message = SecurityUtils.validate_basic_input(assistant_message, 100000)
            
            self.logger.info(f"Extracted interaction - User: {len(user_message or '')} chars, "
                           f"Assistant: {len(assistant_message or '')} chars, "
                           f"Tool calls: {len(tool_calls)}, Tool results: {len(tool_results)}")
            
            return user_message, assistant_message, tool_calls, tool_results
        
        except Exception as e:
            self.logger.error(f"Error extracting interaction from {transcript_path}: {e}")
            return None, None, [], []
    
    def call_sage_core_directly(self, user_input: str, assistant_response: str, metadata: Dict[str, Any]) -> bool:
        """直接调用sage_core进行内存存储 - 使用HookExecutionContext配置"""
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
                    user_input=user_input,
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
                        self.logger.info("Direct sage_core save successful")
                        return result
                else:
                    # 如果没有运行的事件循环，直接运行
                    result = asyncio.run(save_to_sage_core())
                    self.logger.info("Direct sage_core save successful")
                    return result
            except Exception as e:
                self.logger.error(f"Direct sage_core save failed: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in sage_core call: {e}")
            return False
    
    def backup_locally(self, user_input: str, assistant_response: str, metadata: Dict[str, Any], 
                      tool_calls: List[Dict], tool_results: List[Dict]) -> bool:
        """本地备份完整交互数据 - 使用HookExecutionContext"""
        try:
            # 使用上下文获取备份目录
            backup_dir = self.context.get_backup_dir()
            
            backup_data = {
                'timestamp': metadata.get('timestamp', time.time()), 
                'session_id': metadata.get('session_id', ''),
                'user_input': user_input,
                'assistant_response': assistant_response,
                'tool_calls': tool_calls,
                'tool_results': tool_results,
                'metadata': metadata,
                'enhanced_version': True,
                'context_info': {
                    'platform': self.context.get_platform_info(),
                    'project_root': str(self.context.project_root)
                }
            }
            
            backup_file = backup_dir / f"conversation_{int(metadata.get('timestamp', time.time()))}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Enhanced backup saved to {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in local backup: {e}")
            return False
    
    def parse_input(self) -> Dict[str, Any]:
        """解析Hook输入数据"""
        try:
            raw_input = sys.stdin.read()
            if not raw_input:
                self.logger.warning("Empty input received")
                return {}
            
            input_data = json.loads(raw_input)
            session_id = input_data.get('session_id', '')
            
            self.logger.info(f"Received hook input: session_id={session_id}")
            return input_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse input JSON: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Unexpected error parsing input: {e}")
            return {}
    
    def run(self) -> None:
        """主运行逻辑"""
        start_time = time.time()
        
        try:
            # 解析输入
            input_data = self.parse_input()
            if not input_data:
                sys.exit(1)
            
            session_id = input_data.get('session_id', '')
            transcript_path = input_data.get('transcript_path', '')
            
            if not session_id:
                self.logger.warning("No session_id provided")
                sys.exit(1)
            
            if not transcript_path or not Path(transcript_path).exists():
                self.logger.warning(f"Invalid transcript path: {transcript_path}")
                sys.exit(1)
            
            # 提取完整的交互数据
            user_input, assistant_response, tool_calls, tool_results = self.extract_complete_interaction(transcript_path)
            
            if not user_input or not assistant_response:
                self.logger.warning("No complete conversation to archive")
                sys.exit(1)
            
            # 构建增强的元数据
            metadata = {
                'session_id': session_id,
                'timestamp': time.time(),
                'source': 'claude-cli-hook-enhanced',
                'tool_calls_count': len(tool_calls),
                'tool_results_count': len(tool_results),
                'user_input_length': len(user_input),
                'assistant_response_length': len(assistant_response),
                'has_tool_interactions': len(tool_calls) > 0 or len(tool_results) > 0
            }
            
            # 添加项目信息
            metadata = self.enhance_metadata_with_project(metadata) 
            
            # 尝试直接调用sage_core
            success = self.call_sage_core_directly(user_input, assistant_response, metadata)
            
            # 无论成功与否，都进行本地备份
            self.backup_locally(user_input, assistant_response, metadata, tool_calls, tool_results)
            
            # 如果有数据聚合器，发送数据
            if has_aggregator:
                try:
                    aggregator = get_aggregator()
                    if aggregator:
                        aggregator.add_conversation_data({
                            'session_id': session_id,
                            'timestamp': metadata['timestamp'],
                            'user_length': len(user_input),
                            'assistant_length': len(assistant_response),
                            'tool_calls': len(tool_calls),
                            'success': success
                        })
                except Exception as e:
                    self.logger.warning(f"Failed to send data to aggregator: {e}")
            
            execution_time = time.time() - start_time
            if success:
                self.logger.info(f"Enhanced archiving completed successfully in {execution_time:.2f}s")
            else:
                self.logger.error(f"Enhanced archiving failed after {execution_time:.2f}s (but backup saved)")
            
        except Exception as e:
            self.logger.error(f"Unexpected error in main execution: {e}")
            sys.exit(1)


def main():
    """入口函数"""
    archiver = EnhancedSageArchiver()
    archiver.run()


if __name__ == "__main__":
    main()