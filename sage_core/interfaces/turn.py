#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turn数据模型 - 表示一次完整的对话交互
包含用户输入、工具调用和助手响应
"""
from dataclasses import dataclass, field
from typing import List, Any, Dict, Optional
from datetime import datetime
import uuid


@dataclass
class ToolCall:
    """工具调用记录"""
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Any = None
    status: str = "pending"  # pending, success, error
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'tool_name': self.tool_name,
            'tool_input': self.tool_input,
            'tool_output': self.tool_output,
            'status': self.status,
            'error_message': self.error_message,
            'execution_time_ms': self.execution_time_ms,
            'call_id': self.call_id,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class Turn:
    """一次完整的对话轮次"""
    session_id: str
    user_prompt: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    final_response: Optional[str] = None
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> ToolCall:
        """添加工具调用"""
        tool_call = ToolCall(tool_name=tool_name, tool_input=tool_input)
        self.tool_calls.append(tool_call)
        return tool_call
    
    def update_tool_result(self, call_id: str, tool_output: Any, 
                          status: str = "success", error_message: Optional[str] = None,
                          execution_time_ms: Optional[float] = None):
        """更新工具调用结果"""
        for tool_call in self.tool_calls:
            if tool_call.call_id == call_id:
                tool_call.tool_output = tool_output
                tool_call.status = status
                tool_call.error_message = error_message
                tool_call.execution_time_ms = execution_time_ms
                break
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于存储）"""
        return {
            'turn_id': self.turn_id,
            'session_id': self.session_id,
            'user_prompt': self.user_prompt,
            'tool_calls': [tc.to_dict() for tc in self.tool_calls],
            'final_response': self.final_response,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    def get_summary(self) -> str:
        """获取摘要信息"""
        tool_summary = ""
        if self.tool_calls:
            tool_names = [tc.tool_name for tc in self.tool_calls]
            tool_summary = f"\n使用的工具: {', '.join(tool_names)}"
            
        return f"""
用户: {self.user_prompt[:100]}...{tool_summary}
助手: {(self.final_response or '')[:100]}...
"""