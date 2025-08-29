#!/usr/bin/env python3
"""
Sage PreToolUse Hook - 工具调用前状态捕获
在工具执行前捕获调用参数和上下文，为完整的工具调用链追踪奠定基础

主要功能:
1. 捕获工具调用参数
2. 生成唯一call_id用于关联
3. 保存项目标识信息
4. 轻量级文件存储
"""

import json
import sys
import time
import uuid
import os
import hashlib
from pathlib import Path
from typing import Dict, Any
import logging

# 导入HookExecutionContext
sys.path.insert(0, str(Path(__file__).parent.parent))
from context import create_hook_context

from temp_file_cleaner import get_cleaner
from file_lock import JsonFileLock

class SagePreToolCapture:
    """工具调用前状态捕获器 - HookExecutionContext架构版本"""
    
    def __init__(self):
        # 创建执行上下文
        self.context = create_hook_context(__file__)
        
        # 设置用户级临时目录
        self.temp_dir = Path.home() / '.sage_hooks_temp'
        self.temp_dir.mkdir(exist_ok=True)
        
        # 设置日志
        self.setup_logging()
        self.logger.info("SagePreToolCapture initialized")
        
        # 初始化清理器（首次调用时触发清理）
        cleaner = get_cleaner(str(self.temp_dir), max_age_hours=24.0)
        # 使用更可靠的触发机制：基于概率而非环境变量
        import random
        if random.random() < 0.01:  # 1%概率触发清理，避免频繁阻塞
            try:
                stats = cleaner.cleanup_once()
                if stats['cleaned_files'] > 0:
                    self.logger.info(f"Cleaned {stats['cleaned_files']} old temp files")
            except Exception as e:
                self.logger.warning(f"Temp file cleanup failed: {e}")
        
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
        
        log_file = log_dir / "pre_tool_capture.log"
        
        self.logger = logging.getLogger('SagePreToolCapture')
        self.logger.setLevel(logging.DEBUG)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # 格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def get_project_id(self) -> str:
        """获取当前项目的唯一标识"""
        cwd = os.getcwd()
        project_name = os.path.basename(cwd)
        hash_suffix = hashlib.md5(cwd.encode()).hexdigest()[:8]
        return f"{project_name}_{hash_suffix}"
    
    
    def normalize_input_fields(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化输入字段名称 - 将camelCase转换为snake_case"""
        field_map = {
            'sessionId': 'session_id',
            'toolName': 'tool_name',
            'toolInput': 'tool_input',
            'toolOutput': 'tool_response',
            'executionTimeMs': 'execution_time_ms',
            'isError': 'is_error',
            'errorMessage': 'error_message'
        }
        
        normalized = {}
        for key, value in input_data.items():
            mapped_key = field_map.get(key, key)
            normalized[mapped_key] = value
        
        return normalized
        
    def capture_pre_tool_state(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """捕获工具调用前的状态"""
        # 标准化输入字段
        normalized_data = self.normalize_input_fields(input_data)
        
        # 生成唯一调用ID
        call_id = str(uuid.uuid4())
        
        # 提取关键信息
        pre_call_data = {
            'call_id': call_id,
            'timestamp': time.time(),
            'session_id': normalized_data.get('session_id', 'unknown'),
            'tool_name': normalized_data.get('tool_name', 'unknown'),
            'tool_input': normalized_data.get('tool_input', {}),
            'cwd': os.getcwd(),
            'project_id': self.get_project_id(),
            'project_name': os.path.basename(os.getcwd()),
            'project_path': os.getcwd(),
            'context': {
                'user': normalized_data.get('user', 'unknown'),
                'environment': normalized_data.get('environment', {})
            }
        }
        
        # 保存到临时文件（使用文件锁）
        temp_file = self.temp_dir / f"pre_{call_id}.json"
        json_lock = JsonFileLock(temp_file)
        
        try:
            if not json_lock.safe_write(pre_call_data):
                raise Exception("Failed to write with file lock")
            
            self.logger.info(f"Captured pre-tool state for {pre_call_data['tool_name']} (ID: {call_id})")
            
            # 定期清理旧文件（使用新的清理器）
            if hash(call_id) % 100 == 0:  # 1%的概率触发清理
                try:
                    cleaner = get_cleaner(str(self.temp_dir), max_age_hours=24.0)
                    stats = cleaner.cleanup_once()
                    if stats['cleaned_files'] > 0:
                        self.logger.info(f"Periodic cleanup: removed {stats['cleaned_files']} files")
                except Exception as e:
                    self.logger.warning(f"Periodic cleanup failed: {e}")
            
            return {
                "status": "captured",
                "call_id": call_id,
                "tool_name": pre_call_data['tool_name'],
                "project_id": pre_call_data['project_id']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to save pre-tool state: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def process_hook(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理PreToolUse Hook输入"""
        # 标准化输入字段
        normalized_data = self.normalize_input_fields(input_data)
        
        self.logger.info(f"Processing PreToolUse Hook for tool: {normalized_data.get('tool_name', 'unknown')}")
        
        # 验证必要字段
        if not normalized_data.get('tool_name'):
            self.logger.warning("No toolName provided in hook input")
            return {"status": "skipped", "message": "No toolName provided"}
        
        # 捕获状态
        result = self.capture_pre_tool_state(normalized_data)
        
        # 记录性能指标
        if result.get('status') == 'captured':
            self.logger.info(f"Hook execution completed successfully")
        
        return result

def main():
    """主函数"""
    try:
        # 读取标准输入
        input_data = json.load(sys.stdin)
        
        # 创建捕获器实例并处理
        capturer = SagePreToolCapture()
        result = capturer.process_hook(input_data)
        
        # 输出结果（轻量级，避免影响性能）
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"PreToolUse hook error: {str(e)}"
        }
        print(json.dumps(error_result))
        # 使用正确的错误码表示失败
        sys.exit(1)

if __name__ == "__main__":
    main()