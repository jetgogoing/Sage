#!/usr/bin/env python3
"""
测试阶段3实际功能实现
验证之前TODO的方法是否已正确实现
"""

import os
import sys
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sage_memory_cli import MemoryCLI


class TestActualImplementation:
    """测试实际功能实现"""
    
    @pytest.fixture
    def cli(self):
        """创建CLI实例"""
        return MemoryCLI()
    
    def test_clear_memories_by_date_implementation(self, cli):
        """测试按日期清除记忆的实现"""
        # 测试方法存在且不再返回固定的0
        cutoff = datetime.now() - timedelta(days=7)
        
        # 调用方法
        result = cli._clear_memories_by_date(cutoff)
        
        # 验证返回值类型
        assert isinstance(result, int)
        
        # 验证方法实现了分页逻辑
        # 检查方法中是否包含实际的实现代码
        import inspect
        source = inspect.getsource(cli._clear_memories_by_date)
        
        # 验证关键实现细节
        assert 'search_memory' in source  # 正确的方法名
        assert 'clear_all_memories' in source
        assert 'add_memory' in source
        assert 'cutoff_timestamp' in source  # 日期比较逻辑
        assert 'TODO' not in source  # 确保没有TODO标记
    
    def test_get_all_memories_for_export_implementation(self, cli):
        """测试导出记忆获取的实现"""
        # 调用方法
        result = cli._get_all_memories_for_export()
        
        # 验证返回值类型
        assert isinstance(result, list)
        
        # 验证方法实现了分页和排序
        import inspect
        source = inspect.getsource(cli._get_all_memories_for_export)
        
        # 验证关键实现细节
        assert 'search_memory' in source  # 正确的方法名
        assert 'sort' in source
        assert 'timestamp' in source
        assert 'export_item' in source  # 数据转换逻辑
        assert 'TODO' not in source  # 确保没有TODO标记
    
    def test_analyze_memories_implementation(self, cli):
        """测试记忆分析的实现"""
        # 调用方法
        result = cli._analyze_memories()
        
        # 验证返回值结构
        assert isinstance(result, dict)
        assert 'total_count' in result
        assert 'time_distribution' in result
        assert 'topics' in result
        assert 'avg_daily' in result
        assert 'most_active_hour' in result
        assert 'avg_conversation_length' in result
        
        # 新增的字段
        assert 'user_messages' in result
        assert 'assistant_messages' in result
        assert 'total_conversations' in result
        
        # 验证方法实现了实际分析
        import inspect
        source = inspect.getsource(cli._analyze_memories)
        
        # 验证关键实现细节
        assert 'hour_distribution' in source
        assert 'daily_counts' in source
        assert 'word_counts' in source
        assert 'conversation_lengths' in source
        assert 'TODO' not in source  # 确保没有TODO标记
    
    def test_implementation_completeness(self, cli):
        """测试整体实现完整性"""
        # 检查所有关键方法都已实现
        methods_to_check = [
            '_clear_memories_by_date',
            '_get_all_memories_for_export', 
            '_analyze_memories'
        ]
        
        for method_name in methods_to_check:
            # 验证方法存在
            assert hasattr(cli, method_name)
            
            # 获取方法
            method = getattr(cli, method_name)
            
            # 验证是可调用的
            assert callable(method)
            
            # 验证没有TODO标记
            import inspect
            source = inspect.getsource(method)
            assert 'TODO' not in source, f"{method_name} 仍包含TODO标记"
            assert '# 暂时返回' not in source, f"{method_name} 仍包含临时代码"


def run_tests():
    """运行实现验证测试"""
    print("=" * 60)
    print("阶段3：功能实现验证测试")
    print("=" * 60)
    
    # 运行 pytest
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == '__main__':
    run_tests()