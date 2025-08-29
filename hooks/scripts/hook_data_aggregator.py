#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hook Data Aggregator - 跨Hook数据协作机制
整合PreToolUse、PostToolUse和Stop Hook的数据，实现完整的交互链追踪

主要功能:
1. 聚合工具调用完整数据
2. 跨项目数据管理
3. 为Stop Hook提供增强数据
4. 统计和分析功能
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import hashlib
# 添加当前目录到sys.path以导入file_lock
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from file_lock import JsonFileLock

# 添加项目路径以导入Turn模型
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sage_core.interfaces.turn import ToolCall

class HookDataAggregator:
    """Hook数据聚合器"""
    
    def __init__(self):
        # 用户级临时目录
        self.temp_dir = Path.home() / '.sage_hooks_temp'
        self.temp_dir.mkdir(exist_ok=True)
        
        # 设置日志
        self.setup_logging()
        self.logger.info("HookDataAggregator initialized")
        
    def setup_logging(self):
        """设置日志配置"""
        # 确保SAGE_HOME被正确解析
        sage_home = os.getenv('SAGE_HOME')
        if not sage_home:
            # 如果SAGE_HOME未设置，使用脚本所在目录的父目录
            sage_home = Path(__file__).parent.parent.parent
        else:
            sage_home = Path(sage_home)
        
        log_dir = sage_home / "logs" / "Hooks"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / "data_aggregator.log"
        
        self.logger = logging.getLogger('HookDataAggregator')
        self.logger.setLevel(logging.DEBUG)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # 格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def get_project_id(self, cwd: str = None) -> str:
        """获取项目唯一标识"""
        cwd = cwd or os.getcwd()
        project_name = os.path.basename(cwd)
        hash_suffix = hashlib.md5(cwd.encode()).hexdigest()[:8]
        return f"{project_name}_{hash_suffix}"
    
    def aggregate_session_tools(self, session_id: str, project_id: str = None) -> Dict[str, Any]:
        """
        聚合指定会话的所有工具调用数据
        支持项目筛选
        """
        if project_id is None:
            project_id = self.get_project_id()
        
        tool_records = []
        stats = {
            'total_tools': 0,
            'successful_tools': 0,
            'failed_tools': 0,
            'tool_types': {},
            'zen_tools': 0,
            'total_execution_time': 0
        }
        
        # 扫描complete文件
        for complete_file in self.temp_dir.glob('complete_*.json'):
            try:
                # 使用文件锁安全读取
                json_lock = JsonFileLock(complete_file)
                record = json_lock.safe_read()
                
                if record is None:
                    continue
                
                # 检查session和project匹配
                pre_call = record.get('pre_call', {})
                post_call = record.get('post_call', {})
                
                if pre_call.get('session_id') == session_id:
                    # 项目筛选（如果指定）
                    if project_id and pre_call.get('project_id') != project_id:
                        continue
                    
                    tool_records.append(record)
                    
                    # 更新统计
                    tool_name = pre_call.get('tool_name', 'unknown')
                    stats['total_tools'] += 1
                    stats['tool_types'][tool_name] = stats['tool_types'].get(tool_name, 0) + 1
                    
                    if post_call.get('is_error'):
                        stats['failed_tools'] += 1
                    else:
                        stats['successful_tools'] += 1
                    
                    if tool_name.startswith('mcp__zen__'):
                        stats['zen_tools'] += 1
                    
                    exec_time = post_call.get('execution_time_ms', 0)
                    if exec_time:
                        stats['total_execution_time'] += exec_time
                        
            except Exception as e:
                self.logger.error(f"Error reading complete file {complete_file}: {e}")
                continue
        
        # 按时间排序
        tool_records.sort(key=lambda x: x.get('pre_call', {}).get('timestamp', 0))
        
        return {
            'session_id': session_id,
            'project_id': project_id,
            'tool_records': tool_records,
            'stats': stats,
            'aggregated_at': time.time()
        }
    
    def get_cross_project_sessions(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        获取跨项目的会话信息
        返回最近N小时内的所有会话及其项目分布
        """
        cutoff_time = time.time() - (hours * 3600)
        sessions = {}
        
        # 扫描所有complete文件
        for complete_file in self.temp_dir.glob('complete_*.json'):
            try:
                # 检查文件时间
                if complete_file.stat().st_mtime < cutoff_time:
                    continue
                
                # 使用文件锁安全读取
                json_lock = JsonFileLock(complete_file)
                record = json_lock.safe_read()
                
                if record is None:
                    continue
                
                pre_call = record.get('pre_call', {})
                session_id = pre_call.get('session_id')
                project_id = pre_call.get('project_id')
                
                if session_id and project_id:
                    if session_id not in sessions:
                        sessions[session_id] = {
                            'session_id': session_id,
                            'projects': set(),
                            'tool_count': 0,
                            'first_seen': pre_call.get('timestamp', 0),
                            'last_seen': pre_call.get('timestamp', 0)
                        }
                    
                    sessions[session_id]['projects'].add(project_id)
                    sessions[session_id]['tool_count'] += 1
                    sessions[session_id]['last_seen'] = max(
                        sessions[session_id]['last_seen'],
                        pre_call.get('timestamp', 0)
                    )
                    
            except Exception as e:
                self.logger.error(f"Error processing file {complete_file}: {e}")
                continue
        
        # 转换set为list
        result = []
        for session_data in sessions.values():
            session_data['projects'] = list(session_data['projects'])
            session_data['is_cross_project'] = len(session_data['projects']) > 1
            result.append(session_data)
        
        # 按最后活动时间排序
        result.sort(key=lambda x: x['last_seen'], reverse=True)
        
        return result
    
    def enhance_stop_hook_data(self, session_id: str, user_message: str, 
                             assistant_message: str, tool_calls: List[Dict], 
                             tool_results: List[Dict]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        为Stop Hook增强数据，整合Pre/Post工具调用信息
        返回：(增强的工具数据, 增强的元数据)
        """
        # 聚合当前会话的工具数据
        aggregated = self.aggregate_session_tools(session_id)
        
        # 构建增强的工具调用链
        enhanced_tool_chain = []
        tool_id_map = {}  # 映射tool_use_id到完整记录
        
        # 首先处理Pre/Post配对的数据
        for record in aggregated['tool_records']:
            pre = record.get('pre_call', {})
            post = record.get('post_call', {})
            
            enhanced_call = {
                'call_id': record.get('call_id'),
                'tool_name': pre.get('tool_name'),
                'tool_input': pre.get('tool_input'),
                'tool_output': post.get('tool_output'),
                'execution_time_ms': post.get('execution_time_ms'),
                'is_error': post.get('is_error', False),
                'error_message': post.get('error_message', ''),
                'timestamp': pre.get('timestamp'),
                'project_id': pre.get('project_id')
            }
            
            # 特殊处理ZEN工具
            if post.get('zen_analysis'):
                enhanced_call['zen_analysis'] = post['zen_analysis']
            
            enhanced_tool_chain.append(enhanced_call)
            
            # 建立ID映射（如果有）
            if pre.get('call_id'):
                tool_id_map[pre['call_id']] = enhanced_call
        
        # 增强的元数据
        enhanced_metadata = {
            'tool_chain_complete': True,
            'tool_chain_length': len(enhanced_tool_chain),
            'aggregation_stats': aggregated['stats'],
            'data_sources': {
                'stop_hook': True,
                'pre_tool_hook': len(aggregated['tool_records']) > 0,
                'post_tool_hook': len(aggregated['tool_records']) > 0
            },
            'data_completeness_score': self.calculate_completeness_score(
                tool_calls, tool_results, enhanced_tool_chain
            )
        }
        
        return enhanced_tool_chain, enhanced_metadata
    
    def calculate_completeness_score(self, transcript_tools: List[Dict], 
                                   transcript_results: List[Dict], 
                                   enhanced_chain: List[Dict]) -> float:
        """
        计算数据完整性评分
        基于：transcript中的工具调用 vs 实际捕获的完整数据
        """
        if not transcript_tools and not enhanced_chain:
            return 1.0  # 没有工具调用，完整性100%
        
        if not transcript_tools:
            transcript_tools = []
        
        # 计算捕获率
        transcript_count = len(transcript_tools)
        captured_count = len(enhanced_chain)
        
        if transcript_count == 0:
            return 1.0
        
        capture_rate = min(captured_count / transcript_count, 1.0)
        
        # 计算数据质量（有pre和post数据的比例）
        quality_score = 0
        for call in enhanced_chain:
            tool_input = call.get('tool_input')
            tool_output = call.get('tool_output')
            
            # 检查是否有实际内容，而不仅仅是存在
            has_input = tool_input and (
                isinstance(tool_input, dict) and len(tool_input) > 0 or
                isinstance(tool_input, (str, list)) and len(str(tool_input).strip()) > 0
            )
            has_output = tool_output and (
                isinstance(tool_output, dict) and len(tool_output) > 0 or
                isinstance(tool_output, (str, list)) and len(str(tool_output).strip()) > 0
            )
            
            if has_input and has_output:
                quality_score += 1
        
        quality_rate = quality_score / len(enhanced_chain) if enhanced_chain else 0
        
        # 综合评分（70%捕获率 + 30%质量）
        completeness = (capture_rate * 0.7) + (quality_rate * 0.3)
        
        self.logger.info(f"Completeness score: {completeness:.2%} "
                        f"(capture: {capture_rate:.2%}, quality: {quality_rate:.2%})")
        
        return completeness
    
    def cleanup_old_data(self, hours: int = 48):
        """
        清理超过指定时间的数据
        """
        cutoff_time = time.time() - (hours * 3600)
        cleaned_files = 0
        
        # 清理所有类型的临时文件
        for pattern in ['pre_*.json', 'complete_*.json']:
            for temp_file in self.temp_dir.glob(pattern):
                try:
                    if temp_file.stat().st_mtime < cutoff_time:
                        temp_file.unlink()
                        cleaned_files += 1
                except Exception as e:
                    self.logger.error(f"Error cleaning file {temp_file}: {e}")
        
        if cleaned_files > 0:
            self.logger.info(f"Cleaned {cleaned_files} old files")
        
        return cleaned_files
    
    def generate_session_report(self, session_id: str) -> Dict[str, Any]:
        """
        生成会话的详细报告
        """
        aggregated = self.aggregate_session_tools(session_id)
        cross_project_info = self.get_cross_project_sessions(1)  # 最近1小时
        
        # 找到当前会话信息
        current_session = None
        for session in cross_project_info:
            if session['session_id'] == session_id:
                current_session = session
                break
        
        report = {
            'session_id': session_id,
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_tools': aggregated['stats']['total_tools'],
                'success_rate': (aggregated['stats']['successful_tools'] / 
                               aggregated['stats']['total_tools'] * 100 
                               if aggregated['stats']['total_tools'] > 0 else 0),
                'zen_tools_used': aggregated['stats']['zen_tools'],
                'total_execution_time_ms': aggregated['stats']['total_execution_time'],
                'is_cross_project': current_session['is_cross_project'] if current_session else False,
                'projects_involved': current_session['projects'] if current_session else [self.get_project_id()]
            },
            'tool_breakdown': aggregated['stats']['tool_types'],
            'timeline': [
                {
                    'timestamp': record.get('pre_call', {}).get('timestamp'),
                    'tool': record.get('pre_call', {}).get('tool_name'),
                    'project': record.get('pre_call', {}).get('project_name'),
                    'execution_time': record.get('post_call', {}).get('execution_time_ms'),
                    'status': 'error' if record.get('post_call', {}).get('is_error') else 'success'
                }
                for record in aggregated['tool_records']
            ]
        }
        
        return report
    
    def aggregate_current_session(self) -> List[ToolCall]:
        """
        聚合当前会话的工具调用数据，返回ToolCall对象列表
        供简化的stop hook使用
        """
        tool_calls = []
        
        # 获取当前session_id - 从环境变量或最新的文件中推断
        session_id = os.environ.get('CLAUDE_SESSION_ID')
        
        if not session_id:
            # 尝试从最近的complete文件中获取session_id
            latest_file = None
            latest_time = 0
            
            for complete_file in self.temp_dir.glob('complete_*.json'):
                try:
                    mtime = complete_file.stat().st_mtime
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_file = complete_file
                except:
                    continue
            
            if latest_file:
                try:
                    json_lock = JsonFileLock(latest_file)
                    record = json_lock.safe_read()
                    if record:
                        session_id = record.get('pre_call', {}).get('session_id')
                except Exception as e:
                    self.logger.error(f"Error reading latest file for session_id: {e}")
        
        if not session_id:
            self.logger.warning("无法确定当前session_id")
            return tool_calls
        
        # 使用现有的聚合方法获取数据
        aggregated = self.aggregate_session_tools(session_id)
        
        # 转换为ToolCall对象
        for record in aggregated['tool_records']:
            pre_call = record.get('pre_call', {})
            post_call = record.get('post_call', {})
            
            # 创建ToolCall对象
            tool_call = ToolCall(
                tool_name=pre_call.get('tool_name', 'unknown'),
                tool_input=pre_call.get('tool_input', {}),
                tool_output=post_call.get('tool_output'),
                status='error' if post_call.get('is_error') else 'success',
                error_message=post_call.get('error_message'),
                execution_time_ms=post_call.get('execution_time_ms'),
                call_id=record.get('call_id')
            )
            
            # 设置时间戳
            if pre_call.get('timestamp'):
                from datetime import datetime
                tool_call.timestamp = datetime.fromtimestamp(pre_call['timestamp'])
            
            tool_calls.append(tool_call)
        
        self.logger.info(f"聚合了 {len(tool_calls)} 个工具调用 (session: {session_id})")
        return tool_calls
    
    def cleanup_processed_files(self, tool_calls: List[ToolCall]) -> int:
        """
        清理已处理的工具调用相关的临时文件
        返回清理的文件数量
        """
        cleaned_count = 0
        
        # 获取所有已处理的call_id
        processed_call_ids = {tc.call_id for tc in tool_calls if tc.call_id}
        
        if not processed_call_ids:
            return cleaned_count
        
        # 清理对应的complete文件
        for complete_file in self.temp_dir.glob('complete_*.json'):
            try:
                # 从文件名提取call_id
                filename = complete_file.stem  # 去掉.json
                if filename.startswith('complete_'):
                    call_id = filename[9:]  # 去掉'complete_'前缀
                    
                    if call_id in processed_call_ids:
                        complete_file.unlink()
                        cleaned_count += 1
                        self.logger.debug(f"清理已处理文件: {complete_file.name}")
                        
            except Exception as e:
                self.logger.error(f"清理文件 {complete_file} 时出错: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"清理了 {cleaned_count} 个已处理的临时文件")
        
        return cleaned_count

# 单例实例
_aggregator_instance = None

def get_aggregator() -> HookDataAggregator:
    """获取聚合器单例"""
    global _aggregator_instance
    if _aggregator_instance is None:
        _aggregator_instance = HookDataAggregator()
    return _aggregator_instance

if __name__ == "__main__":
    # 测试代码
    aggregator = get_aggregator()
    print("Hook Data Aggregator initialized")
    
    # 清理旧数据
    cleaned = aggregator.cleanup_old_data(48)
    print(f"Cleaned {cleaned} old files")