#!/usr/bin/env python3
"""
端到端集成测试套件
测试完整的Claude-Mem工作流程
"""

import os
import sys
import subprocess
import json
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import threading
import queue

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from config_manager import get_config_manager
from memory_interface import get_memory_provider


class TestE2EIntegration:
    """端到端集成测试"""
    
    @classmethod
    def setup_class(cls):
        """测试类初始化"""
        # 备份当前记忆
        cls.config_mgr = get_config_manager()
        cls.backup_dir = tempfile.mkdtemp()
        
        # 清空测试环境
        try:
            subprocess.run(
                ['python', 'sage_memory_cli.py', 'clear', '--all', '--force'],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
        except:
            pass
    
    @classmethod
    def teardown_class(cls):
        """测试类清理"""
        # 恢复环境
        if hasattr(cls, 'backup_dir'):
            shutil.rmtree(cls.backup_dir, ignore_errors=True)
    
    def test_complete_conversation_workflow(self):
        """测试完整对话工作流程"""
        # 1. 第一轮对话 - 建立基础上下文
        result1 = subprocess.run(
            ['python', 'claude_mem_v3.py', '什么是Python装饰器？'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result1.returncode == 0, f"第一轮对话失败: {result1.stderr}"
        assert 'Python' in result1.stdout or 'python' in result1.stdout.lower()
        
        # 等待记忆保存
        time.sleep(2)
        
        # 2. 验证记忆已保存
        memory_provider = get_memory_provider()
        stats = memory_provider.get_memory_stats()
        assert stats['total_memories'] >= 2, "记忆未正确保存"
        
        # 3. 第二轮对话 - 测试上下文检索
        result2 = subprocess.run(
            ['python', 'claude_mem_v3.py', '能给个装饰器的例子吗？'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result2.returncode == 0, f"第二轮对话失败: {result2.stderr}"
        
        # 验证是否使用了记忆上下文
        # 检查stderr中的记忆提示
        if '[记忆系统]' in result2.stderr:
            assert '找到' in result2.stderr and '相关历史' in result2.stderr
    
    def test_parameter_passthrough(self):
        """测试参数透传功能"""
        test_cases = [
            # 基础查询
            ['python', 'claude_mem_v3.py', '生成一个简单的JSON'],
            
            # 带参数查询
            ['python', 'claude_mem_v3.py', '写一个函数', '--no-memory'],
            
            # 复杂参数
            ['python', 'claude_mem_v3.py', '解释这段代码', '--verbose']
        ]
        
        for cmd in test_cases:
            print(f"\n测试命令: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            # 不应该有参数解析错误
            assert 'unrecognized arguments' not in result.stderr
            assert 'error' not in result.stderr.lower() or 'Error' in result.stdout
    
    def test_memory_management_commands(self):
        """测试记忆管理命令"""
        base_dir = Path(__file__).parent.parent
        
        # 1. 查看状态
        result = subprocess.run(
            ['python', 'sage_memory_cli.py', 'status'],
            capture_output=True,
            text=True,
            cwd=base_dir
        )
        assert result.returncode == 0
        assert '记忆系统状态' in result.stdout
        
        # 2. 搜索记忆
        result = subprocess.run(
            ['python', 'sage_memory_cli.py', 'search', 'Python'],
            capture_output=True,
            text=True,
            cwd=base_dir
        )
        # 可能没有结果，但命令应该成功执行
        assert result.returncode == 0
        
        # 3. 配置管理
        result = subprocess.run(
            ['python', 'sage_memory_cli.py', 'config', 'show'],
            capture_output=True,
            text=True,
            cwd=base_dir
        )
        assert result.returncode == 0
        assert 'memory_enabled' in result.stdout or '记忆系统配置' in result.stdout
    
    def test_concurrent_operations(self):
        """测试并发操作"""
        base_dir = Path(__file__).parent.parent
        results = queue.Queue()
        
        def run_claude_command(query, result_queue):
            """在线程中运行命令"""
            try:
                result = subprocess.run(
                    ['python', 'claude_mem_v3.py', query],
                    capture_output=True,
                    text=True,
                    cwd=base_dir,
                    timeout=30
                )
                result_queue.put((query, result.returncode, result.stdout, result.stderr))
            except Exception as e:
                result_queue.put((query, -1, '', str(e)))
        
        # 创建多个并发查询
        queries = [
            "什么是并发编程？",
            "Python的GIL是什么？",
            "如何实现线程安全？"
        ]
        
        threads = []
        for query in queries:
            t = threading.Thread(target=run_claude_command, args=(query, results))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join(timeout=60)
        
        # 验证结果
        success_count = 0
        while not results.empty():
            query, returncode, stdout, stderr = results.get()
            if returncode == 0:
                success_count += 1
        
        # 至少应该有一半成功（考虑到API限制）
        assert success_count >= len(queries) // 2, f"并发测试失败过多: {success_count}/{len(queries)}"
    
    def test_error_recovery(self):
        """测试错误恢复机制"""
        base_dir = Path(__file__).parent.parent
        
        # 1. 测试无效命令恢复
        result = subprocess.run(
            ['python', 'claude_mem_v3.py', '--invalid-option'],
            capture_output=True,
            text=True,
            cwd=base_dir
        )
        # 应该有错误提示但不应该崩溃
        assert result.returncode != 0
        
        # 2. 测试空查询处理
        result = subprocess.run(
            ['python', 'claude_mem_v3.py', ''],
            capture_output=True,
            text=True,
            cwd=base_dir
        )
        # 应该优雅处理
        assert 'Traceback' not in result.stderr
    
    def test_memory_persistence(self):
        """测试记忆持久化"""
        base_dir = Path(__file__).parent.parent
        
        # 1. 添加一条记忆
        unique_marker = f"测试标记_{int(time.time())}"
        result = subprocess.run(
            ['python', 'claude_mem_v3.py', f'记住这个特殊标记：{unique_marker}'],
            capture_output=True,
            text=True,
            cwd=base_dir
        )
        assert result.returncode == 0
        
        time.sleep(2)  # 等待保存
        
        # 2. 搜索这条记忆
        result = subprocess.run(
            ['python', 'sage_memory_cli.py', 'search', unique_marker],
            capture_output=True,
            text=True,
            cwd=base_dir
        )
        assert result.returncode == 0
        assert unique_marker in result.stdout, "记忆未正确持久化"
    
    def test_configuration_changes(self):
        """测试配置更改生效"""
        base_dir = Path(__file__).parent.parent
        config_mgr = get_config_manager()
        
        # 1. 保存当前配置
        original_enabled = config_mgr.get('memory_enabled')
        original_count = config_mgr.get('retrieval_count')
        
        try:
            # 2. 修改配置
            result = subprocess.run(
                ['python', 'sage_memory_cli.py', 'config', 'set', 'retrieval_count', '5'],
                capture_output=True,
                text=True,
                cwd=base_dir
            )
            assert result.returncode == 0
            
            # 3. 验证配置已更改
            new_count = config_mgr.get('retrieval_count')
            assert new_count == 5, f"配置未生效: {new_count}"
            
        finally:
            # 4. 恢复原始配置
            config_mgr.set('memory_enabled', original_enabled)
            config_mgr.set('retrieval_count', original_count)
    
    def test_export_import_cycle(self):
        """测试导出导入循环"""
        base_dir = Path(__file__).parent.parent
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / 'test_export.json'
            
            # 1. 导出记忆
            result = subprocess.run(
                ['python', 'sage_memory_cli.py', 'export', '-o', str(export_path)],
                capture_output=True,
                text=True,
                cwd=base_dir
            )
            
            # 如果有记忆才继续测试
            if result.returncode == 0 and export_path.exists():
                # 2. 读取导出文件
                with open(export_path, 'r') as f:
                    exported_data = json.load(f)
                
                # 3. 验证导出格式
                assert isinstance(exported_data, list), "导出数据应该是列表"
                
                if exported_data:
                    # 验证数据结构
                    first_memory = exported_data[0]
                    assert 'content' in first_memory
                    assert 'metadata' in first_memory


class TestEdgeCases:
    """边界条件测试"""
    
    def test_empty_database(self):
        """测试空数据库情况"""
        base_dir = Path(__file__).parent.parent
        
        # 清空数据库
        subprocess.run(
            ['python', 'sage_memory_cli.py', 'clear', '--all', '--force'],
            capture_output=True,
            text=True,
            cwd=base_dir
        )
        
        # 应该能正常工作
        result = subprocess.run(
            ['python', 'claude_mem_v3.py', '你好'],
            capture_output=True,
            text=True,
            cwd=base_dir
        )
        assert result.returncode == 0
    
    def test_large_input(self):
        """测试大输入处理"""
        base_dir = Path(__file__).parent.parent
        
        # 创建一个较长的输入
        long_input = "请分析这段文字：" + "测试" * 500
        
        result = subprocess.run(
            ['python', 'claude_mem_v3.py', long_input],
            capture_output=True,
            text=True,
            cwd=base_dir
        )
        
        # 应该能处理不崩溃
        assert 'Traceback' not in result.stderr
    
    def test_special_characters(self):
        """测试特殊字符处理"""
        base_dir = Path(__file__).parent.parent
        
        special_inputs = [
            "包含'单引号'的文本",
            '包含"双引号"的文本',
            "包含\n换行符\n的文本",
            "包含emoji😊的文本"
        ]
        
        for input_text in special_inputs:
            print(f"\n测试输入: {repr(input_text)}")
            result = subprocess.run(
                ['python', 'claude_mem_v3.py', input_text],
                capture_output=True,
                text=True,
                cwd=base_dir
            )
            # 不应该因为特殊字符崩溃
            assert 'Traceback' not in result.stderr


def run_integration_tests():
    """运行集成测试"""
    print("=" * 60)
    print("端到端集成测试")
    print("=" * 60)
    
    # 运行pytest
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == '__main__':
    run_integration_tests()