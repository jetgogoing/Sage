#!/usr/bin/env python3
"""
Sage Stop Hook - 统一会话结束处理脚本 (已修复版本)
修复内容：
1. 统一路径处理，使用pathlib.Path
2. 实现fail-fast错误处理机制
3. 修复Claude CLI消息角色映射
4. 解决JSON序列化问题
"""

import json
import sys
import subprocess
import logging
import time
import os
import hashlib
import asyncio
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

# 导入HookExecutionContext
sys.path.insert(0, str(Path(__file__).parent.parent))
from context import create_hook_context

# 导入完整安全验证工具
try:
    from security_utils import InputValidator, PathValidator, ResourceLimiter, SecurityError
    security_available = True
except ImportError:
    security_available = False
    print("Warning: Full security validation not available, using basic validation")

# 导入数据聚合器
try:
    from hook_data_aggregator import HookDataAggregator
    aggregator_available = True
except ImportError:
    aggregator_available = False

# 文件锁机制
try:
    from file_lock import JsonFileLock
    file_lock_available = True
except ImportError:
    file_lock_available = False

class SageStopHook:
    """统一的Sage会话结束处理器 - 已修复版本"""
    
    def __init__(self):
        # 使用HookExecutionContext统一架构
        self.context = create_hook_context(__file__)
        self.logger = self.context.setup_logging('SageStopHook', 'sage_stop_hook.log')
        
        # 安全验证器
        if security_available:
            self.input_validator = InputValidator()
            self.path_validator = PathValidator()
            self.resource_limiter = ResourceLimiter()
        else:
            self.input_validator = None
            self.path_validator = None
            self.resource_limiter = None
            
        # 数据聚合器
        if aggregator_available:
            self.aggregator = HookDataAggregator()
        else:
            self.aggregator = None
            
        # 输出目录 - 统一使用Path对象
        self.output_dir = Path(self.context.get_backup_dir())
        self.temp_dir = Path.home() / '.sage_hooks_temp'
        self.temp_dir.mkdir(exist_ok=True)
        
        self.logger.info("Sage Stop Hook initialized with unified architecture (FIXED)")
    
    def parse_input(self) -> Dict[str, Any]:
        """解析并验证输入数据"""
        try:
            input_text = sys.stdin.read().strip()
            if not input_text:
                self.logger.error("No input provided")
                self._fail_fast("No input provided")
            
            # 尝试解析JSON输入
            try:
                input_data = json.loads(input_text)
                if isinstance(input_data, dict):
                    return self._validate_json_input(input_data)
            except json.JSONDecodeError:
                pass
            
            # 处理纯文本输入（Human:/Assistant:格式）
            return self._parse_text_input(input_text)
            
        except Exception as e:
            self.logger.error(f"Failed to parse input: {e}")
            self._fail_fast(f"Input parsing failed: {e}")
    
    def _fail_fast(self, error_message: str) -> None:
        """立即退出机制"""
        self.logger.error(f"FAIL FAST: {error_message}")
        print(f"ERROR: {error_message}")
        sys.exit(1)
    
    def _validate_json_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证JSON格式输入"""
        if self.input_validator:
            try:
                # 验证session_id
                session_id = input_data.get('session_id', '')
                if session_id:
                    self.input_validator.validate_session_id(session_id)
                
                # 验证文件路径 - 统一转换为Path对象
                transcript_path_str = input_data.get('transcript_path', '')
                if transcript_path_str:
                    transcript_path = Path(transcript_path_str)
                    try:
                        validated_path = self.path_validator.validate_transcript_path(str(transcript_path))
                        if validated_path:
                            # 保持为Path对象，但在input_data中存储字符串（避免后续序列化问题）
                            input_data['transcript_path'] = str(validated_path)
                        else:
                            # 验证失败，但仍然保持字符串格式
                            input_data['transcript_path'] = str(transcript_path)
                    except Exception as path_error:
                        self.logger.warning(f"Path validation failed: {path_error}")
                        # 对于路径验证失败，我们允许继续，但记录警告，确保存储为字符串
                        input_data['transcript_path'] = str(transcript_path)
                
                self.logger.info(f"JSON input validated: session_id={session_id}")
                return input_data
                
            except Exception as e:
                self.logger.error(f"JSON input validation failed: {e}")
                self._fail_fast(f"Input validation failed: {e}")
        else:
            # 基本验证
            if len(str(input_data)) > 100000:  # 100KB限制
                self._fail_fast("Input data too large")
            return input_data
    
    def _parse_text_input(self, text: str) -> Dict[str, Any]:
        """解析Human:/Assistant:格式的文本输入"""
        if self.input_validator:
            try:
                clean_text = self.input_validator.sanitize_string(text, max_length=50000)
            except Exception as e:
                self.logger.error(f"Text sanitization failed: {e}")
                self._fail_fast(f"Text sanitization failed: {e}")
        else:
            clean_text = text[:50000]  # 基本长度限制
        
        self.logger.info(f"Text input parsed: {len(clean_text)} characters")
        return {
            'format': 'text',
            'content': clean_text,
            'session_id': f"text-session-{int(time.time())}"
        }
    
    def detect_input_format(self, input_data: Dict[str, Any]) -> str:
        """检测输入数据格式"""
        if 'transcript_path' in input_data and input_data['transcript_path']:
            return 'claude_cli_jsonl'
        elif 'format' in input_data and input_data['format'] == 'text':
            return 'human_assistant_text'
        elif 'content' in input_data:
            return 'human_assistant_text'
        else:
            return 'unknown'
    
    def process_claude_cli_jsonl(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Claude CLI的transcript.jsonl文件 - 修复版本"""
        transcript_path_str = input_data.get('transcript_path', '')
        if not transcript_path_str:
            self._fail_fast("No transcript path provided")
        
        # 调试信息
        self.logger.info(f"Processing transcript path: {transcript_path_str} (type: {type(transcript_path_str)})")
        
        # 统一转换为Path对象 - 确保处理字符串输入
        if isinstance(transcript_path_str, (str, Path)):
            transcript_path = Path(transcript_path_str)
            self.logger.info(f"Converted to Path object: {transcript_path} (type: {type(transcript_path)})")
        else:
            self._fail_fast(f"Invalid transcript path type: {type(transcript_path_str)}")
        
        # Fail-fast检查文件存在性
        try:
            path_exists = transcript_path.exists()
            self.logger.info(f"Path exists check: {path_exists}")
            if not path_exists:
                self._fail_fast(f"Transcript file not found: {transcript_path}")
        except Exception as e:
            self.logger.error(f"Error checking path existence: {e}")
            self._fail_fast(f"Path existence check failed: {e}")
        
        try:
            # 安全读取文件
            self.logger.info(f"Starting file read for: {transcript_path}")
            if self.resource_limiter:
                try:
                    self.resource_limiter.limit_file_operations(transcript_path, max_size=100*1024*1024)
                    # 尝试传递Path对象，如果失败则传递字符串
                    try:
                        lines = self.resource_limiter.safe_read_lines(transcript_path, max_lines=10000)
                    except (AttributeError, TypeError):
                        lines = self.resource_limiter.safe_read_lines(str(transcript_path), max_lines=10000)
                except Exception as rl_error:
                    self.logger.warning(f"Resource limiter failed: {rl_error}, falling back to direct file read")
                    with open(transcript_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
            else:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            
            self.logger.info(f"Successfully read {len(lines)} lines from file")
            
            # 提取完整交互数据
            self.logger.info("Starting interaction extraction")
            conversation_data = self._extract_complete_interaction(lines)
            self.logger.info("Interaction extraction completed")
            
            # 调试信息：输出提取到的消息数量和类型
            messages = conversation_data.get('messages', [])
            self.logger.info(f"Extracted {len(messages)} messages")
            
            # 统计角色分布
            role_counts = {}
            for msg in messages:
                role = msg.get('role', 'unknown')
                role_counts[role] = role_counts.get(role, 0) + 1
            
            self.logger.info(f"Role distribution: {role_counts}")
            
            # 显示前3条消息的详细信息
            for i, msg in enumerate(messages[:3]):
                self.logger.info(f"Message {i}: role={msg.get('role')}, content_len={len(msg.get('content', ''))}")
            
            # Fail-fast检查是否有有效消息
            if not messages:
                self._fail_fast("No messages extracted from transcript")
            
            # 增强元数据 - 确保transcript_path是字符串（避免JSON序列化问题）
            conversation_data.update({
                'session_id': input_data.get('session_id', ''),
                'transcript_path': str(transcript_path),  # 强制转换为字符串
                'project_id': self.get_project_id(),
                'project_name': os.path.basename(os.getcwd()),
                'processing_timestamp': time.time(),
                'format': 'claude_cli_jsonl'
            })
            
            return conversation_data
            
        except Exception as e:
            self.logger.error(f"Failed to process Claude CLI JSONL: {e}")
            self._fail_fast(f"JSONL processing failed: {e}")
    
    def _extract_complete_interaction(self, lines: List[str]) -> Dict[str, Any]:
        """从JSONL行中提取完整的交互数据（包含工具调用） - 修复版本"""
        messages = []
        tool_calls = []
        
        # 从后往前解析，获取最近的交互
        for line in reversed(lines[-50:]):  # 检查最后50行
            if not line.strip():
                continue
                
            try:
                entry = json.loads(line.strip())
                entry_type = entry.get('type', '')
                
                if entry_type in ['user', 'assistant']:
                    message_data = self._parse_claude_cli_message(entry)
                    if message_data:
                        messages.insert(0, message_data)
                        
                        # 提取工具调用信息
                        if entry_type == 'assistant':
                            tool_info = self._extract_tool_calls_from_message(entry)
                            if tool_info:
                                tool_calls.extend(tool_info)
                                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Skipping invalid JSON line: {e}")
                continue
        
        return {
            'messages': messages,
            'tool_calls': tool_calls,
            'message_count': len(messages),
            'tool_call_count': len(tool_calls),
            'extraction_method': 'claude_cli_jsonl'
        }
    
    def _parse_claude_cli_message(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析Claude CLI消息格式 - 修复版本"""
        message = entry.get('message', {})
        content_list = message.get('content', [])
        
        content_parts = []
        for item in content_list:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    content_parts.append(item.get('text', ''))
                elif item.get('type') == 'thinking':
                    thinking_content = item.get('thinking', '')
                    content_parts.append(f"[思维链]\n{thinking_content}")
                elif item.get('type') == 'tool_use':
                    tool_name = item.get('name', 'unknown_tool')
                    content_parts.append(f"[工具调用: {tool_name}]")
            elif isinstance(item, str):
                content_parts.append(item)
        
        if content_parts:
            # 关键修复：确保正确的角色映射
            entry_type = entry.get('type')
            # Claude CLI 使用 'user' 和 'assistant'，我们需要确保正确映射
            role = 'user' if entry_type == 'user' else 'assistant'
            
            return {
                'role': role,  # 修复：确保角色正确映射
                'content': '\n'.join(content_parts),
                'timestamp': entry.get('timestamp'),
                'uuid': entry.get('uuid')
            }
        return None
    
    def _extract_tool_calls_from_message(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从助手消息中提取工具调用信息"""
        message = entry.get('message', {})
        content_list = message.get('content', [])
        tool_calls = []
        
        for item in content_list:
            if isinstance(item, dict) and item.get('type') == 'tool_use':
                tool_calls.append({
                    'tool_name': item.get('name', 'unknown'),
                    'tool_input': item.get('input', {}),
                    'call_id': item.get('id', ''),
                    'timestamp': entry.get('timestamp'),
                    'message_uuid': entry.get('uuid')
                })
        
        return tool_calls
    
    def process_human_assistant_text(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Human:/Assistant:格式的文本"""
        content = input_data.get('content', '')
        if not content:
            self._fail_fast("No content provided for text processing")
        
        try:
            # 解析Human/Assistant对话
            messages = self._parse_human_assistant_format(content)
            
            # Fail-fast检查是否有有效消息
            if not messages:
                self._fail_fast("No messages extracted from text content")
            
            # 聚合当前会话的工具调用数据
            tool_calls = []
            if self.aggregator:
                try:
                    session_data = self.aggregator.aggregate_current_session()
                    tool_calls = session_data.get('tool_calls', [])
                    self.logger.info(f"Aggregated {len(tool_calls)} tool calls from session")
                except Exception as e:
                    self.logger.warning(f"Failed to aggregate tool calls: {e}")
            
            return {
                'messages': messages,
                'tool_calls': tool_calls,
                'message_count': len(messages),
                'tool_call_count': len(tool_calls),
                'session_id': input_data.get('session_id', ''),
                'project_id': self.get_project_id(),
                'project_name': os.path.basename(os.getcwd()),
                'processing_timestamp': time.time(),
                'format': 'human_assistant_text',
                'extraction_method': 'text_parsing_with_aggregation'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process Human/Assistant text: {e}")
            self._fail_fast(f"Text processing failed: {e}")
    
    def _parse_human_assistant_format(self, content: str) -> List[Dict[str, Any]]:
        """解析Human:/Assistant:格式文本"""
        messages = []
        current_role = None
        current_content = []
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('Human:'):
                if current_role and current_content:
                    messages.append({
                        'role': current_role,
                        'content': '\n'.join(current_content).strip(),
                        'timestamp': time.time()
                    })
                current_role = 'user'
                current_content = [line[6:].strip()]  # Remove 'Human:' prefix
            elif line.startswith('Assistant:'):
                if current_role and current_content:
                    messages.append({
                        'role': current_role,
                        'content': '\n'.join(current_content).strip(),
                        'timestamp': time.time()
                    })
                current_role = 'assistant'
                current_content = [line[10:].strip()]  # Remove 'Assistant:' prefix
            else:
                if current_role:
                    current_content.append(line)
        
        # 添加最后一条消息
        if current_role and current_content:
            messages.append({
                'role': current_role,
                'content': '\n'.join(current_content).strip(),
                'timestamp': time.time()
            })
        
        return messages
    
    def get_project_id(self) -> str:
        """生成项目唯一标识"""
        project_path = os.getcwd()
        return hashlib.md5(project_path.encode()).hexdigest()[:12]
    
    def save_to_database(self, conversation_data: Dict[str, Any]) -> bool:
        """保存数据到Sage Core数据库 - 修复版本"""
        try:
            self.logger.info("Initializing Sage Core for database save...")
            start_time = time.time()
            
            # 使用上下文设置Python路径
            self.context.setup_python_path()
            
            # 获取配置
            sage_config = self.context.get_sage_config()
            
            # 导入Sage Core - 使用正确的导入路径
            from sage_core.singleton_manager import get_sage_core
            from sage_core.interfaces.core_service import MemoryContent
            
            # 构建消息内容
            messages = conversation_data.get('messages', [])
            if not messages:
                self.logger.warning("No messages to save")
                return False
            
            # 提取用户输入和助手响应 - 改进版本
            user_input = ""
            assistant_response = ""
            
            # 更智能的消息提取：优先最后一对对话
            user_messages = [msg for msg in messages if msg.get('role') == 'user']
            assistant_messages = [msg for msg in messages if msg.get('role') == 'assistant']
            
            if user_messages:
                user_input = user_messages[-1].get('content', '')  # 最后一条用户消息
            if assistant_messages:
                assistant_response = assistant_messages[-1].get('content', '')  # 最后一条助手消息
            
            # 如果仍然缺少，尝试从所有消息中构建
            if not user_input and not assistant_response:
                all_content = []
                for msg in messages:
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    all_content.append(f"{role.capitalize()}: {content}")
                
                if all_content:
                    # 将所有内容作为一个对话保存
                    user_input = "Conversation Archive"
                    assistant_response = "\n\n".join(all_content)
            
            if not user_input or not assistant_response:
                self.logger.warning(f"Missing content - user_input: {bool(user_input)}, assistant_response: {bool(assistant_response)}")
                self.logger.info(f"Available messages: {len(messages)} total, {len(user_messages)} user, {len(assistant_messages)} assistant")
                return False
            
            # 构建元数据
            metadata = {
                'session_id': conversation_data.get('session_id', ''),
                'project_id': conversation_data.get('project_id', ''),
                'project_name': conversation_data.get('project_name', ''),
                'format': conversation_data.get('format', ''),
                'extraction_method': conversation_data.get('extraction_method', ''),
                'processing_timestamp': conversation_data.get('processing_timestamp', time.time()),
                'message_count': conversation_data.get('message_count', 0),
                'tool_call_count': conversation_data.get('tool_call_count', 0),
                'tool_calls': conversation_data.get('tool_calls', [])
            }
            
            # 异步保存函数
            async def save_to_sage_core():
                sage = await get_sage_core()
                await sage.initialize(sage_config)
                
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
                        result = future.result(timeout=30)
                        elapsed_time = time.time() - start_time
                        self.logger.info(f"Database save completed in {elapsed_time:.2f}s")
                        return result
                else:
                    # 如果没有运行的事件循环，直接运行
                    result = asyncio.run(save_to_sage_core())
                    elapsed_time = time.time() - start_time
                    self.logger.info(f"Database save completed in {elapsed_time:.2f}s")
                    return result
            except Exception as e:
                self.logger.error(f"Async database save failed: {e}")
                return False
            
        except Exception as e:
            self.logger.error(f"Database save failed: {e}")
            return False
    
    def save_local_backup(self, conversation_data: Dict[str, Any]) -> bool:
        """保存本地备份文件 - 修复版本"""
        try:
            timestamp = int(time.time())
            session_id = conversation_data.get('session_id', 'unknown')
            filename = f"conversation_{session_id}_{timestamp}.json"
            backup_path = self.output_dir / filename  # 使用Path对象
            
            # 准备备份数据 - 确保所有Path对象都转换为字符串
            backup_data = {
                'backup_timestamp': timestamp,
                'backup_version': 'sage_stop_hook_v2.04_fixed',
                'conversation_data': self._prepare_serializable_data(conversation_data),
                'system_info': {
                    'cwd': os.getcwd(),
                    'python_version': sys.version,
                    'platform': os.name
                }
            }
            
            # 写入备份文件
            if file_lock_available:
                json_lock = JsonFileLock(backup_path)
                success = json_lock.safe_write(backup_data)
            else:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False)
                success = True
            
            if success:
                self.logger.info(f"Local backup saved: {backup_path}")
                return True
            else:
                self.logger.error(f"Failed to save local backup: {backup_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Local backup failed: {e}")
            return False
    
    def _prepare_serializable_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """确保数据可以JSON序列化 - 修复版本"""
        serializable_data = {}
        for key, value in data.items():
            if isinstance(value, Path):
                serializable_data[key] = str(value)  # 转换Path为字符串
            elif isinstance(value, dict):
                serializable_data[key] = self._prepare_serializable_data(value)
            elif isinstance(value, list):
                serializable_data[key] = [
                    str(item) if isinstance(item, Path) else item 
                    for item in value
                ]
            else:
                serializable_data[key] = value
        return serializable_data
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if not self.temp_dir.exists():
                return
            
            cutoff_time = time.time() - 3600  # 1小时前的文件
            cleaned_count = 0
            
            for temp_file in self.temp_dir.glob("*.json"):
                try:
                    if temp_file.stat().st_mtime < cutoff_time:
                        temp_file.unlink()
                        cleaned_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to clean temp file {temp_file}: {e}")
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned {cleaned_count} temporary files")
                
        except Exception as e:
            self.logger.warning(f"Temp file cleanup failed: {e}")
    
    def run(self) -> None:
        """主运行逻辑 - 修复版本"""
        start_time = time.time()
        
        try:
            # 解析输入 - 包含fail-fast机制
            input_data = self.parse_input()
            if not input_data:
                self._fail_fast("No valid input data")
            
            # 检测输入格式并处理
            input_format = self.detect_input_format(input_data)
            self.logger.info(f"Detected input format: {input_format}")
            
            if input_format == 'claude_cli_jsonl':
                conversation_data = self.process_claude_cli_jsonl(input_data)
            elif input_format == 'human_assistant_text':
                conversation_data = self.process_human_assistant_text(input_data)
            else:
                self._fail_fast(f"Unsupported input format: {input_format}")
            
            if not conversation_data:
                self._fail_fast("Failed to process conversation data")
            
            # 保存到数据库（主要策略）
            db_success = self.save_to_database(conversation_data)
            
            # 保存本地备份（保障策略）
            backup_success = self.save_local_backup(conversation_data)
            
            # 清理临时文件
            self.cleanup_temp_files()
            
            # 执行结果
            elapsed_time = time.time() - start_time
            
            if db_success:
                self.logger.info(f"Conversation archived successfully in {elapsed_time:.2f}s")
                print(f"SUCCESS: Conversation archived (DB: {db_success}, Backup: {backup_success})")
            elif backup_success:
                self.logger.info(f"Conversation backup saved (DB failed) in {elapsed_time:.2f}s")
                print(f"PARTIAL: Backup saved, database failed")
            else:
                self.logger.error(f"All save methods failed in {elapsed_time:.2f}s")
                self._fail_fast("All save methods failed")
                
        except Exception as e:
            self.logger.error(f"Unexpected error in main execution: {e}")
            self._fail_fast(f"Unexpected error: {e}")


def main():
    """入口函数"""
    hook = SageStopHook()
    hook.run()


if __name__ == "__main__":
    main()
