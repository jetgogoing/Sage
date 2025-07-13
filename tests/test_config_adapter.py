#!/usr/bin/env python3
"""
测试配置适配器功能
"""

import unittest
import sys
import json
import tempfile
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config_adapter import ConfigAdapter, get_config_adapter, get_config, set_config


class TestConfigAdapter(unittest.TestCase):
    """测试配置适配器"""
    
    def setUp(self):
        """设置测试环境"""
        self.adapter = ConfigAdapter()
        # 创建临时配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.adapter._legacy_config_file = Path(self.temp_dir) / 'config.json'
        
    def tearDown(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_default_values(self):
        """测试默认配置值"""
        # 测试获取默认值
        self.assertTrue(self.adapter.get('memory_enabled', True))
        self.assertEqual(self.adapter.get('retrieval_count', 3), 3)
        self.assertEqual(self.adapter.get('similarity_threshold', 0.7), 0.7)
        
    def test_legacy_config_loading(self):
        """测试旧配置加载"""
        # 创建禁用config_manager的适配器
        adapter = ConfigAdapter(use_config_manager=False)
        adapter._legacy_config_file = Path(self.temp_dir) / 'config.json'
        
        # 创建旧配置文件
        legacy_config = {
            'memory_enabled': False,
            'retrieval_count': 5,
            'custom_key': 'custom_value'
        }
        
        adapter._legacy_config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(adapter._legacy_config_file, 'w') as f:
            json.dump(legacy_config, f)
        
        # 验证配置值
        self.assertFalse(adapter.get('memory_enabled'))
        self.assertEqual(adapter.get('retrieval_count'), 5)
        self.assertEqual(adapter.get('custom_key'), 'custom_value')
        
    def test_set_config(self):
        """测试设置配置"""
        # 设置新值
        success = self.adapter.set('test_key', 'test_value')
        self.assertTrue(success)
        
        # 验证值已保存
        self.assertEqual(self.adapter.get('test_key'), 'test_value')
        
        # 验证文件已更新
        if self.adapter._legacy_config_file.exists():
            with open(self.adapter._legacy_config_file, 'r') as f:
                saved_config = json.load(f)
                self.assertEqual(saved_config['test_key'], 'test_value')
                
    def test_convenience_functions(self):
        """测试便捷函数"""
        # 测试 get_config
        value = get_config('memory_enabled', True)
        self.assertIsNotNone(value)
        
        # 测试 set_config
        success = set_config('test_convenience', 'test_value')
        self.assertTrue(success)
        self.assertEqual(get_config('test_convenience'), 'test_value')
        
    def test_migration(self):
        """测试配置迁移"""
        # 创建禁用config_manager的适配器
        adapter = ConfigAdapter(use_config_manager=False)
        adapter._legacy_config_file = Path(self.temp_dir) / 'config.json'
        
        # 创建旧配置
        legacy_config = {
            'memory_enabled': False,
            'retrieval_count': 10,
            'async_save': False
        }
        
        adapter._legacy_config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(adapter._legacy_config_file, 'w') as f:
            json.dump(legacy_config, f)
        
        # 执行加载
        adapter._load_legacy_config()
        
        # 验证旧配置已加载
        self.assertFalse(adapter.get('memory_enabled'))
        self.assertEqual(adapter.get('retrieval_count'), 10)


if __name__ == '__main__':
    unittest.main()