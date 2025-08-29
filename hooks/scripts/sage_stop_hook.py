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
            
            # 提取完整交互数据（带会话ID用于Hook关联）
            self.logger.info("Starting interaction extraction")
            session_id = input_data.get('session_id', '')
            conversation_data = self._extract_complete_interaction(lines, session_id)
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
    
    def _extract_complete_interaction(self, lines: List[str], session_id: str = None) -> Dict[str, Any]:
        """从JSONL行中提取完整的交互数据（包含工具调用） - Hook整合版本"""
        messages = []
        tool_calls = []
        
        # 加载会话的Hook数据
        hook_data = {}
        if session_id:
            hook_data = self._load_session_hook_data(session_id)
            self.logger.info(f"Processing with {len(hook_data)} hook records for session {session_id}")
        
        # 从后往前解析，获取最近的交互
        for line in reversed(lines[-50:]):  # 检查最后50行
            if not line.strip():
                continue
                
            try:
                entry = json.loads(line.strip())
                entry_type = entry.get('type', '')
                
                if entry_type in ['user', 'assistant']:
                    # 使用增强的消息解析器
                    if hook_data:
                        message_data = self._parse_claude_cli_message_enriched(entry, hook_data)
                    else:
                        message_data = self._parse_claude_cli_message(entry)
                    
                    if message_data:
                        messages.insert(0, message_data)
                        
                        # 提取工具调用信息（增强版）
                        if entry_type == 'assistant':
                            tool_info = self._extract_tool_calls_from_message(entry)
                            if tool_info:
                                tool_calls.extend(tool_info)
                            
                            # 从Hook数据中提取额外的工具信息
                            enrichments = message_data.get('tool_enrichments', [])
                            for enrichment in enrichments:
                                if enrichment.get('enriched', False):
                                    call_id = enrichment.get('call_id')
                                    if call_id and call_id in hook_data:
                                        hook_record = hook_data[call_id]
                                        enhanced_tool_info = {
                                            'tool_name': enrichment.get('tool_name'),
                                            'tool_input': hook_record.get('pre_call', {}).get('tool_input', {}),
                                            'tool_output': hook_record.get('post_call', {}).get('tool_output', {}),
                                            'call_id': call_id,
                                            'timestamp': hook_record.get('pre_call', {}).get('timestamp'),
                                            'execution_time_ms': hook_record.get('post_call', {}).get('execution_time_ms'),
                                            'is_error': hook_record.get('post_call', {}).get('is_error', False),
                                            'enriched_from_hook': True
                                        }
                                        tool_calls.append(enhanced_tool_info)
                                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Skipping invalid JSON line: {e}")
                continue
        
        # 统计增强信息
        enriched_messages = len([m for m in messages if m.get('enriched_count', 0) > 0])
        enriched_tools = len([t for t in tool_calls if t.get('enriched_from_hook', False)])
        
        self.logger.info(f"Extracted {len(messages)} messages ({enriched_messages} enriched), {len(tool_calls)} tool calls ({enriched_tools} enriched)")
        
        return {
            'messages': messages,
            'tool_calls': tool_calls,
            'message_count': len(messages),
            'tool_call_count': len(tool_calls),
            'hook_data_count': len(hook_data),
            'enriched_message_count': enriched_messages,
            'enriched_tool_count': enriched_tools,
            'extraction_method': 'claude_cli_jsonl_with_hooks' if hook_data else 'claude_cli_jsonl'
        }
    
    def _parse_claude_cli_message(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析Claude CLI消息格式 - 支持字符串和数组格式，增强Agent报告识别"""
        entry_type = entry.get('type', '')
        
        # 特殊处理：检查是否是user-prompt-submit-hook消息
        is_submit_hook = entry.get('isVisibleInTranscriptOnly', False)
        
        message = entry.get('message', {})
        
        # 对于user消息，content可能是字符串或数组
        if entry_type == 'user':
            # user消息的content直接在message.content中
            content = message.get('content', '')
            content_parts = []
            
            if isinstance(content, str):
                content_parts = [content]
            elif isinstance(content, list):
                # 处理用户消息中的thinking类型
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            content_parts.append(item.get('text', ''))
                        elif item.get('type') == 'thinking':
                            thinking_content = item.get('thinking', '')
                            content_parts.append(f"[用户思维链]\n{thinking_content}")
                    elif isinstance(item, str):
                        content_parts.append(item)
        else:
            # assistant消息的content是数组格式
            content = message.get('content', [])
            content_parts = []
            
            if isinstance(content, str):
                content_parts.append(content)
            elif isinstance(content, list):
                # 现有的数组处理逻辑
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            content_parts.append(item.get('text', ''))
                        elif item.get('type') == 'thinking':
                            thinking_content = item.get('thinking', '')
                            content_parts.append(f"[思维链]\n{thinking_content}")
                        elif item.get('type') == 'tool_use':
                            tool_name = item.get('name', 'unknown_tool')
                            content_parts.append(f"[工具调用: {tool_name}]")
                        elif item.get('type') == 'tool_result':
                            tool_content = item.get('content', '')
                            if tool_content:
                                content_parts.append(tool_content)
                    elif isinstance(item, str):
                        content_parts.append(item)
        
        if content_parts or entry_type == 'user':  # 确保user消息即使内容为空也被处理
            # 确保正确的角色映射
            role = 'user' if entry_type == 'user' else 'assistant'
            
            # 合并内容
            full_content = '\n'.join(content_parts) if content_parts else ''
            
            # 检测并解析Agent报告
            agent_info = self._parse_agent_report(full_content)
            
            result = {
                'role': role,
                'content': full_content,
                'timestamp': entry.get('timestamp'),
                'uuid': entry.get('uuid'),
                'is_submit_hook': is_submit_hook,  # 标记是否是submit hook消息
                'is_agent_report': agent_info is not None,  # 标记是否包含agent报告
                'agent_metadata': agent_info  # 附加agent元数据
            }
            
            # 如果检测到Agent报告，记录详细日志
            if agent_info:
                self.logger.info(f"Detected Agent Report: {agent_info.get('agent_name', 'unknown')} - {agent_info.get('report_type', 'general')}")
            
            # 调试日志
            if entry_type == 'user':
                self.logger.debug(f"Parsed user message: {result['content'][:100]}... (submit_hook: {is_submit_hook})")
            
            return result
        return None
    
    def _parse_agent_report(self, content: str) -> Optional[Dict[str, Any]]:
        """识别并解析Agent报告，支持多种格式"""
        import re
        
        if not content:
            return None
        
        agent_info = {}
        
        # 模式1: 标准格式 "=== [Type] Report by @agent_name ===" 或中文格式
        # 支持英文格式和中文格式
        patterns = [
            r'===\s*(?:(.+?)\s+)?Report\s+by\s+@([\w-]+)\s*===',  # 英文格式，支持连字符
            r'===\s*(.+?报告)\s+by\s+@([\w-]+)\s*===',  # 中文格式，支持连字符
        ]
        
        match1 = None
        for pattern in patterns:
            match1 = re.search(pattern, content, re.IGNORECASE)
            if match1:
                break
        if match1:
            agent_info['report_type'] = match1.group(1) or 'General'
            agent_info['agent_name'] = match1.group(2)
            agent_info['format'] = 'standard'
        
        # 模式2: 简化格式 "Agent Report: agent_name"
        elif 'Agent Report:' in content or 'AGENT REPORT:' in content:
            pattern2 = r'Agent Report:\s*(\w+)'
            match2 = re.search(pattern2, content, re.IGNORECASE)
            if match2:
                agent_info['agent_name'] = match2.group(1)
                agent_info['report_type'] = 'General'
                agent_info['format'] = 'simple'
        
        # 模式3: @agent_name 开头的报告
        elif content.strip().startswith('@'):
            pattern3 = r'^@(\w+)\s+'
            match3 = re.match(pattern3, content.strip())
            if match3:
                agent_info['agent_name'] = match3.group(1)
                agent_info['report_type'] = 'Direct'
                agent_info['format'] = 'mention'
        
        # 如果找到了agent信息，继续提取更多元数据
        if agent_info:
            # 提取任务ID
            task_id_pattern = r'(?:Task|执行|任务)\s*ID:\s*([^\s\n]+)'
            task_match = re.search(task_id_pattern, content, re.IGNORECASE)
            if task_match:
                agent_info['task_id'] = task_match.group(1)
            
            # 提取执行时间
            time_pattern = r'(?:执行时间|Execution Time|Duration|耗时):\s*([0-9.]+)\s*(?:秒|s|ms|毫秒)'
            time_match = re.search(time_pattern, content, re.IGNORECASE)
            if time_match:
                agent_info['execution_time'] = time_match.group(1)
            
            # 检查是否包含结构化元数据
            metadata_pattern = r'<!--\s*AGENT_METADATA\s*(.*?)\s*-->'
            metadata_match = re.search(metadata_pattern, content, re.DOTALL)
            if metadata_match:
                try:
                    embedded_metadata = json.loads(metadata_match.group(1))
                    agent_info['embedded_metadata'] = embedded_metadata
                    # 合并嵌入的元数据
                    if 'agent_id' in embedded_metadata:
                        agent_info['agent_id'] = embedded_metadata['agent_id']
                    if 'internal_metrics' in embedded_metadata:
                        agent_info['metrics'] = embedded_metadata['internal_metrics']
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse embedded agent metadata")
            
            # 统计报告内容特征
            agent_info['content_features'] = {
                'has_execution_id': bool(re.search(r'执行ID|Execution ID|Task ID', content, re.IGNORECASE)),
                'has_metrics': bool(re.search(r'指标|Metrics|统计|Statistics', content, re.IGNORECASE)),
                'has_errors': bool(re.search(r'错误|Error|失败|Failed|❌', content)),
                'has_warnings': bool(re.search(r'警告|Warning|注意|⚠️', content)),
                'has_success': bool(re.search(r'成功|Success|完成|✅', content)),
                'has_recommendations': bool(re.search(r'建议|Recommend|Suggestion|下一步', content, re.IGNORECASE))
            }
            
            # 计算报告完整性得分
            feature_count = sum(agent_info['content_features'].values())
            agent_info['completeness_score'] = feature_count / len(agent_info['content_features'])
            
            self.logger.info(f"Parsed agent report: {agent_info}")
            return agent_info
        
        # 通用Agent检测：更严格的匹配规则，避免误判
        # 必须同时满足更特定的条件
        agent_patterns = [
            r'agent\s+report',  # "agent report"
            r'@\w+\s+(?:report|summary|分析|报告)',  # "@name report/summary"
            r'(?:代理|Agent)\s*[:：]\s*\w+',  # "Agent: name"
            r'by\s+@\w+',  # "by @agent"
        ]
        
        for pattern in agent_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                # 尝试提取agent名称
                agent_name_pattern = r'(?:agent|代理|@)\s*[:\s]*(\w+)'
                name_match = re.search(agent_name_pattern, content, re.IGNORECASE)
                
                return {
                    'agent_name': name_match.group(1) if name_match else 'unknown',
                    'report_type': 'Inferred',
                    'format': 'generic',
                    'confidence': 'low',
                    'content_features': {
                        'has_execution_id': False,
                        'has_metrics': False,
                        'has_errors': False,
                        'has_warnings': False,
                        'has_success': False,
                        'has_recommendations': False
                    },
                    'completeness_score': 0.0
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
                    tool_calls = self.aggregator.aggregate_current_session()
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
                    full_content = '\n'.join(current_content).strip()
                    
                    # 检测并解析Agent报告
                    agent_info = self._parse_agent_report(full_content)
                    
                    message_data = {
                        'role': current_role,
                        'content': full_content,
                        'timestamp': time.time(),
                        'is_agent_report': agent_info is not None,
                        'agent_metadata': agent_info
                    }
                    
                    # 如果检测到Agent报告，记录详细日志
                    if agent_info:
                        self.logger.info(f"Detected Agent Report in text format: {agent_info.get('agent_name', 'unknown')} - {agent_info.get('report_type', 'general')}")
                    
                    messages.append(message_data)
                current_role = 'user'
                current_content = [line[6:].strip()]  # Remove 'Human:' prefix
            elif line.startswith('Assistant:'):
                if current_role and current_content:
                    full_content = '\n'.join(current_content).strip()
                    
                    # 检测并解析Agent报告
                    agent_info = self._parse_agent_report(full_content)
                    
                    message_data = {
                        'role': current_role,
                        'content': full_content,
                        'timestamp': time.time(),
                        'is_agent_report': agent_info is not None,
                        'agent_metadata': agent_info
                    }
                    
                    # 如果检测到Agent报告，记录详细日志
                    if agent_info:
                        self.logger.info(f"Detected Agent Report in text format: {agent_info.get('agent_name', 'unknown')} - {agent_info.get('report_type', 'general')}")
                    
                    messages.append(message_data)
                current_role = 'assistant'
                current_content = [line[10:].strip()]  # Remove 'Assistant:' prefix
            else:
                if current_role:
                    current_content.append(line)
        
        # 添加最后一条消息
        if current_role and current_content:
            full_content = '\n'.join(current_content).strip()
            
            # 检测并解析Agent报告
            agent_info = self._parse_agent_report(full_content)
            
            message_data = {
                'role': current_role,
                'content': full_content,
                'timestamp': time.time(),
                'is_agent_report': agent_info is not None,
                'agent_metadata': agent_info
            }
            
            # 如果检测到Agent报告，记录详细日志
            if agent_info:
                self.logger.info(f"Detected Agent Report in text format: {agent_info.get('agent_name', 'unknown')} - {agent_info.get('report_type', 'general')}")
            
            messages.append(message_data)
        
        return messages
    
    def get_project_id(self) -> str:
        """生成项目唯一标识"""
        project_path = os.getcwd()
        return hashlib.md5(project_path.encode()).hexdigest()[:12]
    
    def _load_session_hook_data(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        """加载指定会话的所有 Hook 记录"""
        hook_data = {}
        if not self.temp_dir.exists():
            self.logger.warning(f"Temp directory {self.temp_dir} does not exist")
            return hook_data
        
        loaded_count = 0
        for complete_file in self.temp_dir.glob('complete_*.json'):
            try:
                # 使用文件锁安全读取
                if file_lock_available:
                    json_lock = JsonFileLock(complete_file)
                    record = json_lock.safe_read()
                else:
                    with open(complete_file, 'r', encoding='utf-8') as f:
                        record = json.load(f)
                
                if record and record.get('pre_call', {}).get('session_id') == session_id:
                    call_id = record.get('call_id')
                    if call_id:
                        hook_data[call_id] = record
                        loaded_count += 1
                        
            except Exception as e:
                self.logger.warning(f"Failed to load hook file {complete_file}: {e}")
                continue
        
        self.logger.info(f"Loaded {loaded_count} hook records for session {session_id}")
        return hook_data
    
    def _find_matching_hook_record(self, tool_name: str, transcript_timestamp: Any, hook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """通过工具名和时间戳匹配 Hook 记录"""
        if not hook_data:
            return None
            
        # 首先尝试工具名匹配（主要匹配方式）
        matching_records = []
        for record in hook_data.values():
            if record.get('pre_call', {}).get('tool_name') == tool_name:
                matching_records.append(record)
        
        if not matching_records:
            return None
        
        # 如果只有一个匹配的记录，直接返回
        if len(matching_records) == 1:
            return matching_records[0]
        
        # 如果有多个匹配记录，尝试时间戳匹配
        if transcript_timestamp:
            try:
                # 处理不同格式的时间戳
                if isinstance(transcript_timestamp, str):
                    # 尝试解析ISO格式时间戳
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(transcript_timestamp.replace('Z', '+00:00'))
                        transcript_timestamp = dt.timestamp()
                    except ValueError:
                        # 如果解析失败，回退到工具名匹配
                        return matching_records[0]
                
                # 按时间戳相近度查找（10秒容忍度）
                best_match = None
                min_time_diff = float('inf')
                
                for record in matching_records:
                    pre_call = record.get('pre_call', {})
                    hook_timestamp = pre_call.get('timestamp', 0)
                    time_diff = abs(float(transcript_timestamp) - float(hook_timestamp))
                    
                    if time_diff < min_time_diff and time_diff < 10:  # 10 second tolerance
                        min_time_diff = time_diff
                        best_match = record
                
                if best_match:
                    self.logger.debug(f"Found matching hook record for {tool_name} with time diff {min_time_diff:.2f}s")
                    return best_match
                    
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Timestamp parsing error: {e}, falling back to tool name matching")
        
        # 回退到返回第一个匹配的记录
        return matching_records[0]
    
    def _parse_claude_cli_message_enriched(self, entry: Dict[str, Any], hook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析消息并整合完整 Hook 数据 - 支持字符串和数组格式"""
        message = entry.get('message', {})
        content = message.get('content', [])
        
        content_parts = []
        tool_enrichments = []
        
        # 修复：处理字符串格式的content
        if isinstance(content, str):
            content_parts.append(content)
        elif isinstance(content, list):
            # 现有的数组处理逻辑
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        content_parts.append(item.get('text', ''))
                    elif item.get('type') == 'thinking':
                        thinking_content = item.get('thinking', '')
                        content_parts.append(f"[思维链]\n{thinking_content}")
                    elif item.get('type') == 'tool_use':
                        tool_name = item.get('name', 'unknown_tool')
                        tool_id = item.get('id', '')
                        
                        # 查找匹配的 Hook 记录
                        hook_record = self._find_matching_hook_record(tool_name, entry.get('timestamp'), hook_data)
                        
                        if hook_record:
                            # 提取完整工具交互
                            pre_call = hook_record.get('pre_call', {})
                            post_call = hook_record.get('post_call', {})
                        else:
                            # 没有Hook记录时初始化空字典
                            pre_call = {}
                            post_call = {}
                        
                        tool_detail = f"[工具调用: {tool_name}]\n"
                        
                        # 添加工具输入
                        tool_input = pre_call.get('tool_input', {})
                        if tool_input:
                            tool_detail += f"输入参数:\n{json.dumps(tool_input, ensure_ascii=False, indent=2)}\n\n"
                        
                        # 特殊处理 ZEN 工具的 AI 对话
                        tool_output = post_call.get('tool_output', {})
                        if tool_name.startswith('mcp__zen__'):
                            # 提取 AI 对话内容
                            if isinstance(tool_output, list) and len(tool_output) > 0:
                                zen_response = tool_output[0]
                                if isinstance(zen_response, dict) and 'text' in zen_response:
                                    try:
                                        zen_content = json.loads(zen_response['text'])
                                        ai_content = zen_content.get('content', '')
                                        if ai_content:
                                            tool_detail += f"AI分析结果:\n{ai_content}\n\n"
                                    except json.JSONDecodeError:
                                        tool_detail += f"ZEN响应:\n{zen_response['text']}\n\n"
                            
                            # 添加 ZEN 分析元数据
                            zen_analysis = post_call.get('zen_analysis', {})
                            if zen_analysis:
                                tool_detail += f"分析元数据: {json.dumps(zen_analysis, ensure_ascii=False)}\n"
                        else:
                            # 常规工具输出
                            if tool_output:
                                tool_detail += f"执行结果:\n{json.dumps(tool_output, ensure_ascii=False, indent=2)}\n"
                        
                        # 添加执行指标
                        if post_call.get('execution_time_ms'):
                            tool_detail += f"执行时间: {post_call['execution_time_ms']}ms\n"
                        
                        if post_call.get('is_error'):
                            tool_detail += f"错误信息: {post_call.get('error_message', '')}\n"
                        
                        content_parts.append(tool_detail)
                        tool_enrichments.append({
                            'tool_name': tool_name,
                            'tool_id': tool_id,
                            'call_id': hook_record.get('call_id') if hook_record else None,
                            'enriched': bool(hook_record)
                        })
                elif item.get('type') == 'tool_result':
                    tool_content = item.get('content', '')
                    if tool_content:
                        content_parts.append(tool_content)
                # 新增：SubagentStop 处理逻辑
                elif item.get('agent_type'):
                    agent_type = item.get('agent_type')
                    self.logger.info(f"Detected SubagentStop with agent_type: {agent_type}")
                    
                    # 处理 coding-executor 特定逻辑
                    if agent_type == 'coding-executor':
                        subagent_enrichments = self._handle_coding_executor_stop(item)
                        if subagent_enrichments:
                            tool_enrichments.extend(subagent_enrichments)
                    
                    # 添加 agent_type 信息到 tool_enrichments 用于后续处理
                    tool_enrichments.append({
                        'type': 'subagent_stop',
                        'agent_type': agent_type,
                        'agent_data': item
                    })
                elif isinstance(item, str):
                    content_parts.append(item)
        
        # 构建完整消息对象
        if content_parts:
            entry_type = entry.get('type')
            role = 'user' if entry_type == 'user' else 'assistant'
            
            return {
                'role': role,
                'content': '\n'.join(content_parts),
                'timestamp': entry.get('timestamp'),
                'uuid': entry.get('uuid'),
                'tool_enrichments': tool_enrichments,
                'enriched_count': len([e for e in tool_enrichments if e.get('enriched', False)])
            }
        return None
    
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
            
            # 添加调试日志
            self.logger.info(f"Found {len(user_messages)} user messages and {len(assistant_messages)} assistant messages")
            
            if user_messages:
                # 过滤掉user-prompt-submit-hook消息，只保留原始用户输入
                original_user_messages = []
                for msg in user_messages:
                    content = msg.get('content', '')
                    # 跳过包含user-prompt-submit-hook标签的消息
                    if '<user-prompt-submit-hook>' not in content:
                        original_user_messages.append(msg)
                    else:
                        self.logger.debug(f"Filtered out user-prompt-submit-hook message")
                
                if original_user_messages:
                    user_input = original_user_messages[-1].get('content', '')  # 最后一条原始用户消息
                    self.logger.info(f"Using original user message: {user_input[:100]}...")
                else:
                    self.logger.warning("All user messages are user-prompt-submit-hook messages")
                    user_input = ""
            
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
            
            # 改进验证逻辑：只有当两者都为空时才拒绝
            if not user_input and not assistant_response:
                self.logger.warning("Both user_input and assistant_response are empty, rejecting save")
                return False
            
            # 分类记录不同消息类型
            if not user_input and assistant_response:
                self.logger.info(f"Assistant-only message detected (tool call result or system message): {len(assistant_response)} chars")
            elif user_input and not assistant_response:
                self.logger.info(f"User-only message detected: {len(user_input)} chars")
            else:
                self.logger.info(f"Standard conversation - user: {len(user_input)} chars, assistant: {len(assistant_response)} chars")
            
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
        import json
        from datetime import datetime
        
        def make_serializable(obj):
            """递归将对象转换为可序列化格式"""
            if isinstance(obj, Path):
                return str(obj)
            elif hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
                # 优先使用对象自己的 to_dict 方法（如 ToolCall, Turn 等）
                return make_serializable(obj.to_dict())
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, '__dict__'):  # 处理其他自定义对象
                return {k: make_serializable(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [make_serializable(item) for item in obj]
            elif isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            else:
                # 对于其他类型，尝试转换为字符串
                try:
                    json.dumps(obj)  # 测试是否可序列化
                    return obj
                except (TypeError, ValueError):
                    return str(obj)
        
        return make_serializable(data)
    
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
    
    def _handle_coding_executor_stop(self, agent_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """处理 coding-executor SubagentStop 事件"""
        try:
            self.logger.info("Processing coding-executor SubagentStop event")
            enrichments = []
            
            # 触发 code-review 子代理
            if self._trigger_code_review_subagent():
                enrichments.append({
                    'type': 'subagent_trigger',
                    'target_agent': 'code-review',
                    'triggered_by': 'coding-executor',
                    'status': 'triggered',
                    'timestamp': time.time()
                })
                self.logger.info("code-review subagent triggered successfully")
            else:
                enrichments.append({
                    'type': 'subagent_trigger',
                    'target_agent': 'code-review',
                    'triggered_by': 'coding-executor',
                    'status': 'failed',
                    'timestamp': time.time()
                })
                self.logger.warning("Failed to trigger code-review subagent")
            
            # 延迟触发 report-generator（给 code-review 一些时间完成）
            if self._trigger_report_generator_subagent(delay_seconds=30):
                enrichments.append({
                    'type': 'subagent_trigger',
                    'target_agent': 'report-generator',
                    'triggered_by': 'coding-executor',
                    'status': 'scheduled',
                    'timestamp': time.time(),
                    'delay_seconds': 30
                })
                self.logger.info("report-generator subagent scheduled successfully")
            else:
                enrichments.append({
                    'type': 'subagent_trigger',
                    'target_agent': 'report-generator',
                    'triggered_by': 'coding-executor',
                    'status': 'failed',
                    'timestamp': time.time()
                })
                self.logger.warning("Failed to schedule report-generator subagent")
            
            return enrichments
            
        except Exception as e:
            self.logger.error(f"Error in _handle_coding_executor_stop: {e}")
            return []
    
    def _trigger_code_review_subagent(self) -> bool:
        """触发 code-review 子代理"""
        try:
            # 获取最新的 git diff
            git_diff = self._get_latest_git_diff()
            
            # 构造 code-review 命令
            review_prompt = f"""基于最新的 git diff 进行全面代码审查：

{git_diff if git_diff.strip() else "注意：未获取到 git diff，请基于项目当前状态进行审查"}

请重点检查：
1. 代码质量和规范性
2. 潜在错误和安全问题
3. 性能优化机会
4. 统计方法的严谨性（如适用）
5. 测试覆盖和边界条件
"""

            claude_cmd = [
                '/usr/local/bin/claude', 
                '--allowedTools', '*',
                '--max-turns', '6',
                'code-review',
                review_prompt
            ]
            
            # 在后台启动 code-review
            process = subprocess.Popen(
                claude_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True  # 创建新的进程组，避免继承信号
            )
            
            self.logger.info(f"Started code-review subagent with PID: {process.pid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to trigger code-review subagent: {e}")
            return False
    
    def _trigger_report_generator_subagent(self, delay_seconds: int = 0) -> bool:
        """触发 report-generator 子代理（可选延迟）"""
        try:
            report_prompt = f"""请基于最近的 coding-executor 执行和 code-review 审查结果，生成综合阶段报告。

请生成包含以下内容的报告：
1. 执行阶段概述
2. 代码变更摘要  
3. 质量评估结果
4. 发现的问题和建议
5. 下一步行动建议

报告应保存到 docs/执行报告/ 目录，使用时间戳命名格式。
"""

            if delay_seconds > 0:
                # 使用 sleep 命令延迟执行
                claude_cmd = [
                    'sh', '-c', 
                    f'sleep {delay_seconds} && /usr/local/bin/claude --allowedTools "*" --max-turns 6 report-generator "{report_prompt}"'
                ]
            else:
                claude_cmd = [
                    '/usr/local/bin/claude',
                    '--allowedTools', '*', 
                    '--max-turns', '6',
                    'report-generator',
                    report_prompt
                ]
            
            # 在后台启动 report-generator
            process = subprocess.Popen(
                claude_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, 
                text=True,
                start_new_session=True
            )
            
            action = "scheduled" if delay_seconds > 0 else "started"
            self.logger.info(f"{action.capitalize()} report-generator subagent with PID: {process.pid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to trigger report-generator subagent: {e}")
            return False
    
    def _get_latest_git_diff(self) -> str:
        """获取最新的 git diff"""
        try:
            # 尝试获取 staged changes
            result = subprocess.run(
                ['git', 'diff', '--cached', '--no-pager'],
                capture_output=True, text=True, timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
            
            # 如果没有 staged changes，获取 working directory changes  
            result = subprocess.run(
                ['git', 'diff', '--no-pager'],
                capture_output=True, text=True, timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
                
            # 如果都没有，尝试获取最近一次提交的 diff
            result = subprocess.run(
                ['git', 'diff', '--no-pager', 'HEAD~1'],
                capture_output=True, text=True, timeout=15
            )
            
            if result.returncode == 0:
                return result.stdout
                
            return ""
            
        except subprocess.TimeoutExpired:
            self.logger.warning("Git diff command timed out")
            return ""
        except Exception as e:
            self.logger.warning(f"Failed to get git diff: {e}")
            return ""
    
    def _process_subagent_triggers(self, conversation_data: Dict[str, Any]) -> None:
        """处理 SubagentStop 触发逻辑"""
        try:
            self.logger.info("Processing SubagentStop triggers...")
            
            # 检查是否有 SubagentStop 相关的工具增强
            messages = conversation_data.get('messages', [])
            subagent_triggers_found = False
            
            for message in messages:
                tool_enrichments = message.get('tool_enrichments', [])
                for enrichment in tool_enrichments:
                    if enrichment.get('type') == 'subagent_stop':
                        agent_type = enrichment.get('agent_type')
                        self.logger.info(f"Found SubagentStop trigger for agent_type: {agent_type}")
                        
                        if agent_type == 'coding-executor':
                            self.logger.info("Processing coding-executor SubagentStop trigger")
                            subagent_triggers_found = True
                            # 触发逻辑已经在 _handle_coding_executor_stop 中处理了
                            break
            
            # 如果没有找到明确的 SubagentStop 标记，检查 agent 报告
            if not subagent_triggers_found:
                for message in reversed(messages):
                    agent_metadata = message.get('agent_metadata')
                    if agent_metadata:
                        agent_name = agent_metadata.get('agent_name', '').lower()
                        if any(keyword in agent_name for keyword in ['coding-executor', 'coding_executor', 'executor']):
                            self.logger.info(f"Detected coding-executor completion from agent metadata: {agent_name}")
                            
                            # 手动触发 SubagentStop 处理
                            fake_agent_data = {
                                'agent_type': 'coding-executor',
                                'agent_name': agent_name,
                                'detected_from': 'agent_metadata'
                            }
                            self._handle_coding_executor_stop(fake_agent_data)
                            subagent_triggers_found = True
                            break
            
            if not subagent_triggers_found:
                self.logger.debug("No SubagentStop triggers found in conversation")
            else:
                self.logger.info("SubagentStop trigger processing completed")
                
        except Exception as e:
            self.logger.error(f"Error processing SubagentStop triggers: {e}")
    
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
            
            # 处理 SubagentStop 触发逻辑（在数据保存成功后）
            if db_success or backup_success:
                self._process_subagent_triggers(conversation_data)
            
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
