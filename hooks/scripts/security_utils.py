#!/usr/bin/env python3
"""
安全工具模块
为 Sage Hooks 提供安全验证和防护功能

功能：
1. 路径遍历攻击防护
2. 输入验证和清理
3. 资源限制和保护
4. 敏感数据处理
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging


class SecurityError(Exception):
    """安全相关异常"""
    pass


class PathValidator:
    """路径安全验证器"""
    
    def __init__(self, allowed_base_paths: Optional[List[str]] = None):
        """
        初始化路径验证器
        
        Args:
            allowed_base_paths: 允许的基础路径列表
        """
        self.allowed_base_paths = allowed_base_paths or [
            os.getenv('SAGE_HOME', '.'),
            "/tmp/sage_hooks",
            "/tmp",  # 允许临时目录用于测试
            "/var/tmp",  # 系统临时目录
            "/private/tmp",  # macOS 系统中 /tmp 的实际路径
            os.path.expanduser("~/.claude"),  # Claude CLI 目录
        ]
        self.logger = logging.getLogger("security.path_validator")
    
    def validate_path(self, file_path: str, must_exist: bool = False) -> Path:
        """
        验证并规范化文件路径
        
        Args:
            file_path: 要验证的文件路径
            must_exist: 文件是否必须存在
            
        Returns:
            验证后的 Path 对象
            
        Raises:
            SecurityError: 路径不安全时抛出
        """
        if not file_path or not isinstance(file_path, str):
            raise SecurityError("Invalid file path: path must be a non-empty string")
        
        # 防止空字节注入
        if '\x00' in file_path:
            raise SecurityError("Null byte detected in file path")
        
        try:
            # 规范化路径，解析相对路径和符号链接
            normalized_path = Path(file_path).resolve()
        except (OSError, ValueError) as e:
            raise SecurityError(f"Failed to resolve path: {e}")
        
        # 检查路径是否在允许的基础路径内
        path_allowed = False
        for base_path in self.allowed_base_paths:
            try:
                base_resolved = Path(base_path).resolve()
                if normalized_path.is_relative_to(base_resolved):
                    path_allowed = True
                    break
            except (OSError, ValueError):
                continue
        
        if not path_allowed:
            self.logger.warning(f"Path access denied: {file_path} -> {normalized_path}")
            raise SecurityError(f"Path not allowed: {normalized_path}")
        
        # 检查文件是否存在（如果需要）
        if must_exist and not normalized_path.exists():
            raise SecurityError(f"Required file does not exist: {normalized_path}")
        
        # 检查文件权限
        if normalized_path.exists() and not os.access(normalized_path, os.R_OK):
            raise SecurityError(f"Insufficient permissions to read file: {normalized_path}")
        
        self.logger.debug(f"Path validated: {file_path} -> {normalized_path}")
        return normalized_path
    
    def validate_transcript_path(self, transcript_path: str) -> Optional[Path]:
        """
        专门用于验证 transcript 文件路径
        
        Args:
            transcript_path: transcript 文件路径
            
        Returns:
            验证后的 Path 对象，如果路径无效则返回 None
        """
        if not transcript_path:
            return None
        
        try:
            validated_path = self.validate_path(transcript_path, must_exist=True)
            
            # 额外验证：检查文件扩展名
            if validated_path.suffix.lower() not in ['.jsonl', '.json', '.log']:
                self.logger.warning(f"Unexpected transcript file extension: {validated_path.suffix}")
            
            # 检查文件大小（限制为100MB）
            file_size = validated_path.stat().st_size
            max_size = 100 * 1024 * 1024  # 100MB
            if file_size > max_size:
                raise SecurityError(f"Transcript file too large: {file_size} bytes (max: {max_size})")
            
            return validated_path
            
        except SecurityError as e:
            self.logger.error(f"Transcript path validation failed: {e}")
            return None


class InputValidator:
    """输入验证器"""
    
    # 危险字符模式
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script 标签
        r'javascript:',               # JavaScript 协议
        r'data:text/html',           # Data URL with HTML
        r'vbscript:',                # VBScript 协议
        r'onload\s*=',               # 事件处理器
        r'onerror\s*=',
        r'onclick\s*=',
    ]
    
    def __init__(self):
        self.logger = logging.getLogger("security.input_validator")
    
    def validate_json_input(self, raw_input: str, max_size: int = 1024 * 1024) -> Dict[str, Any]:
        """
        验证和解析 JSON 输入
        
        Args:
            raw_input: 原始输入字符串
            max_size: 最大输入大小（字节）
            
        Returns:
            解析后的 JSON 对象
            
        Raises:
            SecurityError: 输入不安全时抛出
        """
        if not raw_input:
            raise SecurityError("Empty input provided")
        
        # 检查输入大小
        if len(raw_input.encode('utf-8')) > max_size:
            raise SecurityError(f"Input too large: {len(raw_input)} bytes (max: {max_size})")
        
        # 检查危险模式
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, raw_input, re.IGNORECASE):
                self.logger.warning(f"Dangerous pattern detected: {pattern}")
                raise SecurityError("Potentially malicious content detected")
        
        try:
            data = json.loads(raw_input)
        except json.JSONDecodeError as e:
            raise SecurityError(f"Invalid JSON format: {e}")
        
        # 验证 JSON 结构
        if not isinstance(data, dict):
            raise SecurityError("Input must be a JSON object")
        
        return data
    
    def validate_session_id(self, session_id: str) -> str:
        """
        验证 session_id 格式
        
        Args:
            session_id: 会话ID
            
        Returns:
            验证后的 session_id
            
        Raises:
            SecurityError: session_id 格式不正确时抛出
        """
        if not session_id or not isinstance(session_id, str):
            raise SecurityError("session_id must be a non-empty string")
        
        # 检查长度
        if len(session_id) < 8 or len(session_id) > 128:
            raise SecurityError("session_id length must be between 8 and 128 characters")
        
        # 检查字符集 (只允许字母数字、连字符和下划线)
        if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
            raise SecurityError("session_id contains invalid characters")
        
        return session_id
    
    def sanitize_string(self, text: str, max_length: int = 200000, enable_chunking: bool = True) -> str:
        """
        清理字符串，移除潜在的危险内容
        
        Args:
            text: 要清理的字符串
            max_length: 最大长度，提高至200K
            enable_chunking: 是否启用分块处理
            
        Returns:
            清理后的字符串
        """
        if not text:
            return ""
        
        # 如果启用分块处理且文本很长，保持完整性
        if enable_chunking and len(text) > max_length:
            # 标记为需要分块处理，但不直接截断
            # 将在存储层进行分块处理
            pass
        elif len(text) > max_length:
            # 只有在禁用分块时才截断
            text = text[:max_length] + "...[truncated]"
        
        # 移除危险模式
        for pattern in self.DANGEROUS_PATTERNS:
            text = re.sub(pattern, '[REMOVED]', text, flags=re.IGNORECASE)
        
        # 移除控制字符
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        return text


class ResourceLimiter:
    """资源限制器"""
    
    def __init__(self):
        self.logger = logging.getLogger("security.resource_limiter")
    
    def limit_file_operations(self, file_path: Path, max_size: int = 50 * 1024 * 1024) -> None:
        """
        对文件操作进行资源限制检查
        
        Args:
            file_path: 文件路径
            max_size: 最大文件大小（字节）
            
        Raises:
            SecurityError: 超出资源限制时抛出
        """
        if not file_path.exists():
            return
        
        try:
            file_size = file_path.stat().st_size
            if file_size > max_size:
                raise SecurityError(f"File too large: {file_size} bytes (max: {max_size})")
        except OSError as e:
            raise SecurityError(f"Failed to check file size: {e}")
    
    def safe_read_lines(self, file_path: Path, max_lines: int = 10000) -> List[str]:
        """
        安全地按行读取文件，限制读取行数
        
        Args:
            file_path: 文件路径
            max_lines: 最大读取行数
            
        Returns:
            文件行列表
            
        Raises:
            SecurityError: 超出限制时抛出
        """
        try:
            lines = []
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    if i >= max_lines:
                        self.logger.warning(f"File has more than {max_lines} lines, truncating")
                        break
                    lines.append(line.strip())
            
            return lines
            
        except OSError as e:
            raise SecurityError(f"Failed to read file: {e}")
        except UnicodeDecodeError as e:
            raise SecurityError(f"File encoding error: {e}")


# 全局安全实例
path_validator = PathValidator()
input_validator = InputValidator()
resource_limiter = ResourceLimiter()


if __name__ == "__main__":
    # 测试安全工具
    print("=== 安全工具测试 ===")
    
    # 测试路径验证
    try:
        valid_path = path_validator.validate_path(os.path.join(os.getenv('SAGE_HOME', '.'), "test.txt"))
        print(f"✓ 路径验证通过: {valid_path}")
    except SecurityError as e:
        print(f"✗ 路径验证失败: {e}")
    
    # 测试危险路径
    try:
        dangerous_path = path_validator.validate_path("../../../etc/passwd")
        print(f"✗ 危险路径未被拦截: {dangerous_path}")
    except SecurityError as e:
        print(f"✓ 危险路径被成功拦截: {e}")
    
    # 测试输入验证
    try:
        safe_input = '{"session_id": "test_123", "prompt": "Hello world"}'
        data = input_validator.validate_json_input(safe_input)
        print(f"✓ 安全输入验证通过: {data}")
    except SecurityError as e:
        print(f"✗ 安全输入验证失败: {e}")
    
    # 测试危险输入
    try:
        dangerous_input = '{"session_id": "test", "prompt": "<script>alert(1)</script>"}'
        data = input_validator.validate_json_input(dangerous_input)
        print(f"✗ 危险输入未被拦截: {data}")
    except SecurityError as e:
        print(f"✓ 危险输入被成功拦截: {e}")
    
    print("=== 测试完成 ===")