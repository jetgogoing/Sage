#!/usr/bin/env python3
"""
Simplified Security Utils for Local Deployment
本地部署简化版安全工具
"""

import os
import hashlib
from pathlib import Path
from typing import Dict, Any

class SimplifiedSecurityUtils:
    """简化的安全工具类 - 适用于本地个人部署"""
    
    @staticmethod
    def validate_basic_input(input_str: str, max_length: int = 100000) -> str:
        """基本的输入验证 - 仅限长度检查"""
        if not input_str:
            return ""
        if len(input_str) > max_length:
            return input_str[:max_length]
        return input_str
    
    @staticmethod
    def get_project_id(cwd: str = None) -> str:
        """获取项目唯一标识"""
        cwd = cwd or os.getcwd()
        project_name = os.path.basename(cwd)
        hash_suffix = hashlib.md5(cwd.encode()).hexdigest()[:8]
        return f"{project_name}_{hash_suffix}"
    
    @staticmethod
    def validate_path(path: str) -> bool:
        """基本的路径验证"""
        try:
            # 确保路径不包含危险字符
            if '..' in path or path.startswith('/etc') or path.startswith('/sys'):
                return False
            return True
        except:
            return False
    
    @staticmethod
    def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """清理元数据 - 简化版"""
        if not isinstance(metadata, dict):
            return {}
        
        # 移除过长的值
        cleaned = {}
        for key, value in metadata.items():
            if isinstance(value, str) and len(value) > 1000:
                cleaned[key] = value[:1000] + "..."
            else:
                cleaned[key] = value
        
        return cleaned

# 兼容性别名
SecurityUtils = SimplifiedSecurityUtils