#!/usr/bin/env python3
"""
单元测试 - 会话管理器
测试 EnhancedSessionManager 的所有功能
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_session_manager_v2 import (
    EnhancedSessionManager, 
    SessionSearchType,
    EXPORT_FORMATS
)


class TestSessionManager:
    """测试会话管理器"""
    
    def __init__(self):
        # 使用临时目录进行测试
        self.temp_dir = tempfile.mkdtemp()
        self.test_results = []
        
    def cleanup(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
        
    def create_test_manager(self):
        """创建测试用的会话管理器"""
        return EnhancedSessionManager(data_dir=self.temp_dir)
        
    def test_session_creation(self):
        """测试会话创建"""
        manager = self.create_test_manager()
        
        # 测试创建会话
        session_id = manager.start_session("测试会话")
        
        success = (
            session_id is not None and
            manager.active_session is not None and
            manager.active_session["title"] == "测试会话"
        )
        
        self.test_results.append({
            "test": "session_creation",
            "success": success,
            "session_id": session_id
        })
        
        return session_id
        
    def test_add_message(self):
        """测试添加消息"""
        manager = self.create_test_manager()
        session_id = manager.start_session("测试消息")
        
        # 添加用户消息
        manager.add_message("user", "你好")
        
        # 添加助手消息
        manager.add_message("assistant", "你好！有什么可以帮助你的吗？")
        
        success = (
            len(manager.active_session["messages"]) == 2 and
            manager.active_session["messages"][0]["role"] == "user" and
            manager.active_session["messages"][1]["role"] == "assistant"
        )
        
        self.test_results.append({
            "test": "add_message",
            "success": success,
            "message_count": len(manager.active_session["messages"])
        })
        
    def test_save_session(self):
        """测试保存会话"""
        manager = self.create_test_manager()
        session_id = manager.start_session("测试保存")
        
        manager.add_message("user", "测试消息")
        manager.add_message("assistant", "收到测试消息")
        
        # 保存会话
        saved_path = manager.save_session()
        
        success = (
            saved_path is not None and
            Path(saved_path).exists() and
            manager.active_session is None  # 保存后清空活动会话
        )
        
        self.test_results.append({
            "test": "save_session",
            "success": success,
            "saved_path": saved_path
        })
        
        return session_id
        
    def test_load_session(self):
        """测试加载会话"""
        manager = self.create_test_manager()
        
        # 先创建并保存一个会话
        session_id = manager.start_session("测试加载")
        manager.add_message("user", "原始消息")
        manager.save_session()
        
        # 加载会话
        loaded = manager.load_session(session_id)
        
        success = (
            loaded is not None and
            loaded["title"] == "测试加载" and
            len(loaded["messages"]) == 1 and
            loaded["messages"][0]["content"] == "原始消息"
        )
        
        self.test_results.append({
            "test": "load_session",
            "success": success
        })
        
    def test_search_by_keyword(self):
        """测试关键词搜索"""
        manager = self.create_test_manager()
        
        # 创建多个会话
        session1 = manager.start_session("Python教程")
        manager.add_message("user", "如何学习Python装饰器？")
        manager.save_session()
        
        session2 = manager.start_session("机器学习")
        manager.add_message("user", "什么是神经网络？")
        manager.save_session()
        
        session3 = manager.start_session("Web开发")
        manager.add_message("user", "如何使用Python开发网站？")
        manager.save_session()
        
        # 搜索包含"Python"的会话
        results = manager.search_sessions(SessionSearchType.KEYWORD, "Python")
        
        success = (
            len(results) == 2 and  # 应该找到2个包含Python的会话
            any(r["session_id"] == session1 for r in results) and
            any(r["session_id"] == session3 for r in results)
        )
        
        self.test_results.append({
            "test": "search_by_keyword",
            "success": success,
            "found_count": len(results)
        })
        
    def test_search_by_date_range(self):
        """测试日期范围搜索"""
        manager = self.create_test_manager()
        
        # 创建会话
        session_id = manager.start_session("今天的会话")
        manager.add_message("user", "测试日期搜索")
        manager.save_session()
        
        # 搜索今天的会话
        today = datetime.now().strftime("%Y-%m-%d")
        results = manager.search_sessions(SessionSearchType.DATE_RANGE, f"{today},{today}")
        
        success = (
            len(results) >= 1 and
            any(r["session_id"] == session_id for r in results)
        )
        
        self.test_results.append({
            "test": "search_by_date_range",
            "success": success,
            "found_count": len(results)
        })
        
    def test_search_by_topic(self):
        """测试主题搜索"""
        manager = self.create_test_manager()
        
        # 创建带标签的会话
        session1 = manager.start_session("编程讨论")
        manager.active_session["tags"] = ["编程", "Python"]
        manager.save_session()
        
        session2 = manager.start_session("数据分析")
        manager.active_session["tags"] = ["数据", "分析"]
        manager.save_session()
        
        # 搜索编程相关主题
        results = manager.search_sessions(SessionSearchType.TOPIC, "编程")
        
        success = (
            len(results) >= 1 and
            any(r["session_id"] == session1 for r in results)
        )
        
        self.test_results.append({
            "test": "search_by_topic",
            "success": success,
            "found_count": len(results)
        })
        
    def test_search_recent(self):
        """测试最近会话搜索"""
        manager = self.create_test_manager()
        
        # 创建多个会话
        session_ids = []
        for i in range(5):
            session_id = manager.start_session(f"会话 {i+1}")
            manager.add_message("user", f"消息 {i+1}")
            manager.save_session()
            session_ids.append(session_id)
        
        # 搜索最近3个会话
        results = manager.search_sessions(SessionSearchType.RECENT, "3")
        
        success = (
            len(results) == 3 and
            results[0]["session_id"] == session_ids[-1]  # 最新的应该排第一
        )
        
        self.test_results.append({
            "test": "search_recent",
            "success": success,
            "found_count": len(results)
        })
        
    def test_export_json(self):
        """测试JSON导出"""
        manager = self.create_test_manager()
        
        # 创建会话
        session_id = manager.start_session("导出测试")
        manager.add_message("user", "测试导出")
        manager.add_message("assistant", "导出功能正常")
        manager.save_session()
        
        # 导出为JSON
        export_result = manager.export_session(session_id, "json")
        
        # 验证导出内容
        try:
            if "content" in export_result:
                data = json.loads(export_result["content"])
                success = (
                    data["title"] == "导出测试" and
                    len(data["messages"]) == 2
                )
            else:
                success = False
        except:
            success = False
            
        self.test_results.append({
            "test": "export_json",
            "success": success
        })
        
    def test_export_markdown(self):
        """测试Markdown导出"""
        manager = self.create_test_manager()
        
        # 创建会话
        session_id = manager.start_session("Markdown导出")
        manager.add_message("user", "如何使用Python？")
        manager.add_message("assistant", "Python是一门简单易学的编程语言")
        manager.save_session()
        
        # 导出为Markdown
        export_result = manager.export_session(session_id, "markdown")
        
        success = (
            "content" in export_result and
            "# Markdown导出" in export_result["content"] and
            "**用户**:" in export_result["content"] and
            "**助手**:" in export_result["content"]
        )
        
        self.test_results.append({
            "test": "export_markdown",
            "success": success
        })
        
    def test_session_analytics(self):
        """测试会话分析"""
        manager = self.create_test_manager()
        
        # 创建会话并添加消息
        session_id = manager.start_session("分析测试")
        
        messages = [
            ("user", "你好"),
            ("assistant", "你好！有什么可以帮助你的吗？"),
            ("user", "我想学习Python"),
            ("assistant", "Python是一门很好的编程语言，适合初学者"),
            ("user", "谢谢"),
            ("assistant", "不客气！")
        ]
        
        for role, content in messages:
            manager.add_message(role, content)
            
        # 获取分析数据
        analytics = manager.get_session_analytics(session_id)
        
        success = (
            analytics is not None and
            analytics["message_count"] == 6 and
            analytics["user_message_count"] == 3 and
            analytics["assistant_message_count"] == 3 and
            analytics["total_characters"] > 0 and
            analytics["average_message_length"] > 0
        )
        
        self.test_results.append({
            "test": "session_analytics",
            "success": success,
            "analytics": analytics
        })
        
    def test_delete_session(self):
        """测试删除会话"""
        manager = self.create_test_manager()
        
        # 创建并保存会话
        session_id = manager.start_session("待删除会话")
        manager.add_message("user", "这个会话将被删除")
        saved_path = manager.save_session()
        
        # 确认文件存在
        file_exists_before = Path(saved_path).exists()
        
        # 删除会话
        delete_success = manager.delete_session(session_id)
        
        # 确认文件已删除
        file_exists_after = Path(saved_path).exists()
        
        success = (
            file_exists_before and
            delete_success and
            not file_exists_after
        )
        
        self.test_results.append({
            "test": "delete_session",
            "success": success
        })
        
    def test_list_sessions(self):
        """测试列出会话"""
        manager = self.create_test_manager()
        
        # 创建多个会话
        session_count = 3
        for i in range(session_count):
            manager.start_session(f"会话 {i+1}")
            manager.add_message("user", f"消息 {i+1}")
            manager.save_session()
            
        # 列出所有会话
        sessions = manager.list_sessions()
        
        success = (
            len(sessions) == session_count and
            all("session_id" in s and "title" in s for s in sessions)
        )
        
        self.test_results.append({
            "test": "list_sessions",
            "success": success,
            "session_count": len(sessions)
        })
        
    def test_get_statistics(self):
        """测试获取统计信息"""
        manager = self.create_test_manager()
        
        # 创建多个会话
        for i in range(3):
            manager.start_session(f"统计测试 {i+1}")
            for j in range(i + 1):
                manager.add_message("user", f"消息 {j+1}")
                manager.add_message("assistant", f"回复 {j+1}")
            manager.save_session()
            
        # 获取统计信息
        stats = manager.get_statistics()
        
        success = (
            stats["total_sessions"] == 3 and
            stats["total_messages"] == 12 and  # 3 + 4 + 5 消息
            stats["total_characters"] > 0 and
            stats["avg_session_length"] == 4.0  # 平均每个会话4条消息
        )
        
        self.test_results.append({
            "test": "get_statistics",
            "success": success,
            "stats": stats
        })
        
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("单元测试：会话管理器")
        print("=" * 60)
        
        try:
            # 运行各个测试
            self.test_session_creation()
            self.test_add_message()
            self.test_save_session()
            self.test_load_session()
            self.test_search_by_keyword()
            self.test_search_by_date_range()
            self.test_search_by_topic()
            self.test_search_recent()
            self.test_export_json()
            self.test_export_markdown()
            self.test_session_analytics()
            self.test_delete_session()
            self.test_list_sessions()
            self.test_get_statistics()
            
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
                    print(f"  - {failure['test']}")
                    if "error" in failure:
                        print(f"    错误: {failure['error']}")
            else:
                print("\n✅ 所有测试通过！")
                
            print("=" * 60)
            
            return passed_tests == total_tests
            
        finally:
            # 清理测试环境
            self.cleanup()


if __name__ == "__main__":
    tester = TestSessionManager()
    success = tester.run_all_tests()
    
    if success:
        print("\n✨ 会话管理器单元测试完成！")