#!/usr/bin/env python3
"""
阶段3：用户控制功能测试
测试配置管理和用户控制命令
"""

import os
import sys
import subprocess
import tempfile
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from config_manager import ConfigManager, get_config_manager
from sage_memory_cli import MemoryCLI


class TestConfigExtensions:
    """测试配置系统扩展"""
    
    def test_memory_config_fields(self):
        """测试记忆系统配置字段"""
        config_mgr = get_config_manager()
        config = config_mgr.config
        
        # 验证新字段存在
        assert hasattr(config, 'retrieval_count')
        assert hasattr(config, 'similarity_threshold')
        assert hasattr(config, 'time_decay')
        assert hasattr(config, 'max_age_days')
        assert hasattr(config, 'max_context_tokens')
        assert hasattr(config, 'async_save')
        assert hasattr(config, 'cache_ttl')
        assert hasattr(config, 'prompt_template')
        assert hasattr(config, 'show_memory_hints')
        assert hasattr(config, 'memory_hint_color')
        assert hasattr(config, 'verbose_mode')
        
        # 验证默认值
        assert config.retrieval_count == 3
        assert config.similarity_threshold == 0.7
        assert config.time_decay is True
        assert config.max_age_days == 30
        assert config.max_context_tokens == 2000
        assert config.async_save is True
        assert config.cache_ttl == 300
        assert config.show_memory_hints is True
        assert config.memory_hint_color == "cyan"
        assert config.verbose_mode is False
    
    def test_config_env_overrides(self):
        """测试环境变量覆盖"""
        # 设置环境变量
        os.environ['SAGE_RETRIEVAL_COUNT'] = '5'
        os.environ['SAGE_SIMILARITY_THRESHOLD'] = '0.8'
        os.environ['SAGE_TIME_DECAY'] = 'false'
        os.environ['SAGE_SHOW_MEMORY_HINTS'] = 'false'
        
        # 创建新的配置管理器
        with tempfile.TemporaryDirectory() as tmpdir:
            config_mgr = ConfigManager(config_dir=Path(tmpdir))
            config = config_mgr.config
            
            # 验证环境变量覆盖
            assert config.retrieval_count == 5
            assert config.similarity_threshold == 0.8
            assert config.time_decay is False
            assert config.show_memory_hints is False
        
        # 清理环境变量
        for key in ['SAGE_RETRIEVAL_COUNT', 'SAGE_SIMILARITY_THRESHOLD', 
                    'SAGE_TIME_DECAY', 'SAGE_SHOW_MEMORY_HINTS']:
            os.environ.pop(key, None)
    
    def test_config_get_set(self):
        """测试配置读写"""
        config_mgr = get_config_manager()
        
        # 测试获取
        original_value = config_mgr.get('retrieval_count')
        assert original_value == 3
        
        # 测试设置
        success = config_mgr.set('retrieval_count', 7)
        assert success is True
        assert config_mgr.get('retrieval_count') == 7
        
        # 恢复原值
        config_mgr.set('retrieval_count', original_value)


class TestMemoryCLI:
    """测试记忆系统CLI"""
    
    @pytest.fixture
    def cli(self):
        """创建CLI实例"""
        return MemoryCLI()
    
    def test_cli_initialization(self, cli):
        """测试CLI初始化"""
        assert cli is not None
        assert cli.config is not None
    
    def test_sage_memory_command(self):
        """测试 sage-memory 命令是否可用"""
        # 检查命令是否存在
        sage_memory_path = Path.home() / '.local' / 'bin' / 'sage-memory'
        assert sage_memory_path.exists()
        assert os.access(sage_memory_path, os.X_OK)
        
        # 测试帮助命令
        result = subprocess.run(
            ['python3', str(Path(__file__).parent.parent / 'sage_memory_cli.py'), '--help'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert 'Sage 记忆系统管理工具' in result.stdout
    
    def test_config_command(self):
        """测试配置命令"""
        # 测试显示配置
        result = subprocess.run(
            ['python3', str(Path(__file__).parent.parent / 'sage_memory_cli.py'), 'config', 'show'],
            capture_output=True,
            text=True
        )
        # 注意：可能因为记忆系统未初始化而失败，这是预期的
        assert 'memory_enabled' in result.stdout or '记忆系统未初始化' in result.stdout


class TestVisualFeedback:
    """测试视觉反馈功能"""
    
    def test_memory_hints_config(self):
        """测试记忆提示配置"""
        config_mgr = get_config_manager()
        
        # 检查默认启用
        assert config_mgr.get('show_memory_hints') is True
        assert config_mgr.get('memory_hint_color') == 'cyan'
        
        # 测试禁用
        config_mgr.set('show_memory_hints', False)
        assert config_mgr.get('show_memory_hints') is False
        
        # 恢复默认
        config_mgr.set('show_memory_hints', True)
    
    def test_print_memory_hint(self):
        """测试记忆提示打印功能"""
        # 这里我们只测试函数是否存在
        from claude_mem_v3 import ImprovedCrossplatformClaude
        
        # 创建实例
        mem = ImprovedCrossplatformClaude()
        
        # 验证方法存在
        assert hasattr(mem, 'print_memory_hint')
        assert callable(mem.print_memory_hint)


class TestUserWorkflow:
    """测试用户工作流程"""
    
    def test_complete_workflow(self):
        """测试完整的用户工作流程"""
        config_mgr = get_config_manager()
        
        # 1. 查看当前配置
        original_count = config_mgr.get('retrieval_count')
        
        # 2. 修改配置
        config_mgr.set('retrieval_count', 10)
        config_mgr.set('show_memory_hints', True)
        config_mgr.set('memory_hint_color', 'green')
        
        # 3. 验证修改
        assert config_mgr.get('retrieval_count') == 10
        assert config_mgr.get('show_memory_hints') is True
        assert config_mgr.get('memory_hint_color') == 'green'
        
        # 4. 导出配置
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = Path(f.name)
        
        success = config_mgr.export_config(export_path)
        assert success is True
        assert export_path.exists()
        
        # 验证导出内容
        with open(export_path, 'r') as f:
            exported = json.load(f)
            assert exported['retrieval_count'] == 10
            assert exported['memory_hint_color'] == 'green'
            assert exported['api_key'] == '<REDACTED>'  # 敏感信息被隐藏
        
        # 清理
        export_path.unlink()
        config_mgr.set('retrieval_count', original_count)
        config_mgr.set('memory_hint_color', 'cyan')


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("阶段3：用户控制功能测试")
    print("=" * 60)
    
    # 运行 pytest
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == '__main__':
    run_tests()