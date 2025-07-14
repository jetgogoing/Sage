#!/usr/bin/env python3
"""
单元测试 - 命令解析器
测试 SageCommandParser 的所有功能
"""

import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_mcp_stdio_v2 import SageCommandParser, CommandType


class TestCommandParser:
    """测试命令解析器"""
    
    def __init__(self):
        self.parser = SageCommandParser()
        self.test_results = []
        
    def test_save_command_parsing(self):
        """测试保存命令解析"""
        test_cases = [
            {
                "input": "/save",
                "expected_type": CommandType.SAVE,
                "expected_params": {}
            },
            {
                "input": "/SAVE",
                "expected_type": CommandType.SAVE,
                "expected_params": {}
            },
            {
                "input": "/save 这是一个标题",
                "expected_type": CommandType.SAVE,
                "expected_params": {"title": "这是一个标题"}
            },
            {
                "input": "/save 多个 空格 的 标题",
                "expected_type": CommandType.SAVE,
                "expected_params": {"title": "多个 空格 的 标题"}
            }
        ]
        
        for case in test_cases:
            command = self.parser.parse_command(case["input"])
            
            success = (
                command["type"] == case["expected_type"] and
                command["params"] == case["expected_params"]
            )
            
            self.test_results.append({
                "test": "save_command_parsing",
                "case": case["input"],
                "success": success,
                "actual": command
            })
            
    def test_search_command_parsing(self):
        """测试搜索命令解析"""
        test_cases = [
            {
                "input": "/search Python",
                "expected_type": CommandType.SEARCH,
                "expected_params": {"query": "Python"}
            },
            {
                "input": "/search 机器学习 深度学习",
                "expected_type": CommandType.SEARCH,
                "expected_params": {"query": "机器学习 深度学习"}
            },
            {
                "input": "/search",
                "expected_type": CommandType.UNKNOWN,
                "expected_params": {}
            }
        ]
        
        for case in test_cases:
            command = self.parser.parse_command(case["input"])
            
            success = (
                command["type"] == case["expected_type"] and
                command["params"] == case["expected_params"]
            )
            
            self.test_results.append({
                "test": "search_command_parsing",
                "case": case["input"],
                "success": success,
                "actual": command
            })
            
    def test_forget_command_parsing(self):
        """测试忘记命令解析"""
        test_cases = [
            {
                "input": "/forget",
                "expected_type": CommandType.FORGET,
                "expected_params": {"scope": "current"}
            },
            {
                "input": "/forget all",
                "expected_type": CommandType.FORGET,
                "expected_params": {"scope": "all"}
            },
            {
                "input": "/forget session_123",
                "expected_type": CommandType.FORGET,
                "expected_params": {"scope": "specific", "session_id": "session_123"}
            }
        ]
        
        for case in test_cases:
            command = self.parser.parse_command(case["input"])
            
            success = (
                command["type"] == case["expected_type"] and
                command["params"] == case["expected_params"]
            )
            
            self.test_results.append({
                "test": "forget_command_parsing",
                "case": case["input"],
                "success": success,
                "actual": command
            })
            
    def test_recall_command_parsing(self):
        """测试回忆命令解析"""
        test_cases = [
            {
                "input": "/recall",
                "expected_type": CommandType.RECALL,
                "expected_params": {"limit": 10}
            },
            {
                "input": "/recall 5",
                "expected_type": CommandType.RECALL,
                "expected_params": {"limit": 5}
            },
            {
                "input": "/recall session_456",
                "expected_type": CommandType.RECALL,
                "expected_params": {"session_id": "session_456"}
            },
            {
                "input": "/recall abc",
                "expected_type": CommandType.RECALL,
                "expected_params": {"limit": 10}  # 非数字默认为10
            }
        ]
        
        for case in test_cases:
            command = self.parser.parse_command(case["input"])
            
            success = (
                command["type"] == case["expected_type"] and
                command["params"] == case["expected_params"]
            )
            
            self.test_results.append({
                "test": "recall_command_parsing",
                "case": case["input"],
                "success": success,
                "actual": command
            })
            
    def test_status_command_parsing(self):
        """测试状态命令解析"""
        test_cases = [
            {
                "input": "/status",
                "expected_type": CommandType.STATUS,
                "expected_params": {}
            },
            {
                "input": "/STATUS",
                "expected_type": CommandType.STATUS,
                "expected_params": {}
            },
            {
                "input": "/status extra params",
                "expected_type": CommandType.STATUS,
                "expected_params": {}  # 忽略额外参数
            }
        ]
        
        for case in test_cases:
            command = self.parser.parse_command(case["input"])
            
            success = (
                command["type"] == case["expected_type"] and
                command["params"] == case["expected_params"]
            )
            
            self.test_results.append({
                "test": "status_command_parsing",
                "case": case["input"],
                "success": success,
                "actual": command
            })
            
    def test_mode_command_parsing(self):
        """测试模式命令解析"""
        test_cases = [
            {
                "input": "/mode on",
                "expected_type": CommandType.MODE,
                "expected_params": {"mode": "on"}
            },
            {
                "input": "/mode off",
                "expected_type": CommandType.MODE,
                "expected_params": {"mode": "off"}
            },
            {
                "input": "/mode",
                "expected_type": CommandType.MODE,
                "expected_params": {"mode": "status"}
            },
            {
                "input": "/mode invalid",
                "expected_type": CommandType.MODE,
                "expected_params": {"mode": "status"}
            }
        ]
        
        for case in test_cases:
            command = self.parser.parse_command(case["input"])
            
            success = (
                command["type"] == case["expected_type"] and
                command["params"] == case["expected_params"]
            )
            
            self.test_results.append({
                "test": "mode_command_parsing",
                "case": case["input"],
                "success": success,
                "actual": command
            })
            
    def test_help_command_parsing(self):
        """测试帮助命令解析"""
        test_cases = [
            {
                "input": "/help",
                "expected_type": CommandType.HELP,
                "expected_params": {}
            },
            {
                "input": "/HELP",
                "expected_type": CommandType.HELP,
                "expected_params": {}
            },
            {
                "input": "/help save",
                "expected_type": CommandType.HELP,
                "expected_params": {"command": "save"}
            }
        ]
        
        for case in test_cases:
            command = self.parser.parse_command(case["input"])
            
            success = (
                command["type"] == case["expected_type"] and
                command["params"] == case["expected_params"]
            )
            
            self.test_results.append({
                "test": "help_command_parsing",
                "case": case["input"],
                "success": success,
                "actual": command
            })
            
    def test_analyze_command_parsing(self):
        """测试分析命令解析"""
        test_cases = [
            {
                "input": "/analyze",
                "expected_type": CommandType.ANALYZE,
                "expected_params": {}
            },
            {
                "input": "/analyze topics",
                "expected_type": CommandType.ANALYZE,
                "expected_params": {"analysis_type": "topics"}
            },
            {
                "input": "/analyze trends 30",
                "expected_type": CommandType.ANALYZE,
                "expected_params": {"analysis_type": "trends", "days": 30}
            }
        ]
        
        for case in test_cases:
            command = self.parser.parse_command(case["input"])
            
            success = (
                command["type"] == case["expected_type"] and
                command["params"] == case["expected_params"]
            )
            
            self.test_results.append({
                "test": "analyze_command_parsing",
                "case": case["input"],
                "success": success,
                "actual": command
            })
            
    def test_edge_cases(self):
        """测试边缘情况"""
        test_cases = [
            {
                "input": "",
                "expected_type": CommandType.UNKNOWN,
                "expected_params": {}
            },
            {
                "input": "not a command",
                "expected_type": CommandType.UNKNOWN,
                "expected_params": {}
            },
            {
                "input": "/",
                "expected_type": CommandType.UNKNOWN,
                "expected_params": {}
            },
            {
                "input": "/unknown_command",
                "expected_type": CommandType.UNKNOWN,
                "expected_params": {}
            },
            {
                "input": "  /save  with spaces  ",
                "expected_type": CommandType.SAVE,
                "expected_params": {"title": "with spaces"}
            }
        ]
        
        for case in test_cases:
            command = self.parser.parse_command(case["input"])
            
            success = (
                command["type"] == case["expected_type"] and
                command["params"] == case["expected_params"]
            )
            
            self.test_results.append({
                "test": "edge_cases",
                "case": case["input"],
                "success": success,
                "actual": command
            })
            
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("单元测试：命令解析器")
        print("=" * 60)
        
        # 运行各个测试
        self.test_save_command_parsing()
        self.test_search_command_parsing()
        self.test_forget_command_parsing()
        self.test_recall_command_parsing()
        self.test_status_command_parsing()
        self.test_mode_command_parsing()
        self.test_help_command_parsing()
        self.test_analyze_command_parsing()
        self.test_edge_cases()
        
        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        
        # 显示结果
        print(f"\n总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {total_tests - passed_tests}")
        
        # 显示失败的测试
        failures = [r for r in self.test_results if not r["success"]]
        if failures:
            print("\n失败的测试:")
            for failure in failures:
                print(f"  - {failure['test']}: {failure['case']}")
                print(f"    实际结果: {failure['actual']}")
        else:
            print("\n✅ 所有测试通过！")
            
        print("=" * 60)
        
        return passed_tests == total_tests


if __name__ == "__main__":
    tester = TestCommandParser()
    success = tester.run_all_tests()
    
    if success:
        print("\n✨ 命令解析器单元测试完成！")