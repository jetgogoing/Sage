#!/usr/bin/env python3
"""
Sage PostToolUse Hook - 工具执行后结果捕获
在工具执行后捕获结果和错误，与PreToolUse数据关联形成完整调用链

主要功能:
1. 捕获工具执行结果
2. 关联PreToolUse数据
3. 特殊处理ZEN工具
4. 生成完整调用记录
"""

import json
import sys
import time
import os
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from temp_file_cleaner import get_cleaner
from file_lock import JsonFileLock

class SagePostToolCapture:
    """工具执行后结果捕获器"""
    
    def __init__(self):
        # 设置用户级临时目录
        self.temp_dir = Path.home() / '.sage_hooks_temp'
        self.temp_dir.mkdir(exist_ok=True)
        
        # 设置日志
        self.setup_logging()
        self.logger.info("SagePostToolCapture initialized")
        
    def setup_logging(self):
        """设置日志配置"""
        log_dir = Path("/Users/jet/Sage/hooks/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / "post_tool_capture.log"
        
        self.logger = logging.getLogger('SagePostToolCapture')
        self.logger.setLevel(logging.DEBUG)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # 格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def find_pre_tool_data(self, session_id: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """查找对应的PreToolUse数据"""
        # 查找所有pre文件
        pre_files = list(self.temp_dir.glob('pre_*.json'))
        
        # 按修改时间倒序，优先匹配最近的
        pre_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for pre_file in pre_files:
            try:
                # 使用文件锁安全读取
                json_lock = JsonFileLock(pre_file)
                pre_data = json_lock.safe_read()
                
                if pre_data is None:
                    continue
                
                # 匹配session_id和tool_name
                if (pre_data.get('session_id') == session_id and 
                    pre_data.get('tool_name') == tool_name):
                    
                    self.logger.info(f"Found matching pre-tool data: {pre_data['call_id']}")
                    return pre_data, pre_file
                    
            except Exception as e:
                self.logger.error(f"Error reading pre file {pre_file}: {e}")
                continue
        
        self.logger.warning(f"No matching pre-tool data found for {tool_name} in session {session_id}")
        return None, None
    
    def extract_zen_analysis(self, tool_output: Any) -> Dict[str, Any]:
        """提取ZEN工具的AI分析结果"""
        zen_data = {
            'is_zen_tool': True,
            'analysis_type': 'unknown'
        }
        
        if isinstance(tool_output, dict):
            # 提取关键信息
            zen_data.update({
                'status': tool_output.get('status'),
                'model_used': tool_output.get('metadata', {}).get('model_used'),
                'thinking_mode': tool_output.get('thinking_mode'),
                'confidence': tool_output.get('confidence'),
                'continuation_id': tool_output.get('continuation_id')
            })
            
            # 分析内容摘要
            if 'content' in tool_output:
                content = str(tool_output['content'])
                zen_data['content_preview'] = content[:500] + '...' if len(content) > 500 else content
            
            # 提取findings
            if 'findings' in tool_output:
                zen_data['findings_summary'] = tool_output['findings']
        
        return zen_data
    
    def capture_post_tool_state(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """捕获工具执行后的状态"""
        session_id = input_data.get('session_id', 'unknown')
        tool_name = input_data.get('tool_name', 'unknown')
        
        # 查找对应的pre数据
        pre_result = self.find_pre_tool_data(session_id, tool_name)
        if not pre_result:
            # 没有找到pre数据，创建独立的post记录
            self.logger.warning("Creating standalone post-tool record")
            call_id = f"post_only_{int(time.time()*1000)}"
            pre_data = None
            pre_file = None
        else:
            pre_data, pre_file = pre_result
            call_id = pre_data['call_id']
        
        # 构建post数据 - 修复字段名从tool_output到tool_response
        tool_response = input_data.get('tool_response', {})
        post_call_data = {
            'timestamp': time.time(),
            'session_id': session_id,
            'tool_name': tool_name,
            'tool_output': tool_response,  # 保存完整的tool_response
            'execution_time_ms': input_data.get('execution_time_ms'),
            'is_error': input_data.get('is_error', False),
            'error_message': input_data.get('error_message', '')
        }
        
        # 特殊处理ZEN工具
        if tool_name.startswith('mcp__zen__'):
            zen_analysis = self.extract_zen_analysis(post_call_data['tool_output'])
            post_call_data['zen_analysis'] = zen_analysis
            self.logger.info(f"Captured ZEN tool analysis: {tool_name}")
        
        # 创建完整记录
        complete_record = {
            'call_id': call_id,
            'pre_call': pre_data,
            'post_call': post_call_data,
            'complete_timestamp': time.time()
        }
        
        # 保存完整记录（使用文件锁）
        complete_file = self.temp_dir / f"complete_{call_id}.json"
        json_lock = JsonFileLock(complete_file)
        
        try:
            if not json_lock.safe_write(complete_record):
                raise Exception("Failed to write complete record with file lock")
            
            # 清理pre文件（也需要锁）
            if pre_file and pre_file.exists():
                try:
                    pre_file.unlink()
                    self.logger.info(f"Cleaned up pre file: {pre_file.name}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up pre file: {e}")
            
            self.logger.info(f"Saved complete tool record: {call_id}")
            
            return {
                "status": "processed",
                "call_id": call_id,
                "tool_name": tool_name,
                "execution_time_ms": post_call_data.get('execution_time_ms'),
                "is_error": post_call_data['is_error']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to save post-tool state: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def cleanup_orphaned_files(self):
        """清理孤立的pre文件（超过1小时未匹配）"""
        try:
            cleaner = get_cleaner(str(self.temp_dir), max_age_hours=1.0)  # 1小时的孤立文件
            stats = cleaner.cleanup_once()
            if stats['cleaned_files'] > 0:
                self.logger.info(f"Cleaned up {stats['cleaned_files']} orphaned files")
        except Exception as e:
            self.logger.error(f"Error during orphaned file cleanup: {e}")
    
    def process_hook(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理PostToolUse Hook输入"""
        self.logger.info(f"Processing PostToolUse Hook for tool: {input_data.get('tool_name', 'unknown')}")
        
        # 捕获状态
        result = self.capture_post_tool_state(input_data)
        
        # 定期清理孤立文件
        if hash(time.time()) % 50 == 0:  # 2%的概率触发清理
            self.cleanup_orphaned_files()
        
        return result

def main():
    """主函数"""
    try:
        # 读取标准输入
        input_data = json.load(sys.stdin)
        
        # 创建捕获器实例并处理
        capturer = SagePostToolCapture()
        result = capturer.process_hook(input_data)
        
        # 输出结果
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"PostToolUse hook error: {str(e)}"
        }
        print(json.dumps(error_result))
        # 使用正确的错误码表示失败
        sys.exit(1)

if __name__ == "__main__":
    main()