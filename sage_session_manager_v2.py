#!/usr/bin/env python3
"""
Sage 会话管理器 V2 - 增强版
支持会话搜索、导出、分析等高级功能
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class SessionSearchType(Enum):
    """会话搜索类型"""
    BY_TOPIC = "topic"
    BY_DATE = "date"
    BY_KEYWORD = "keyword"
    BY_STATUS = "status"


class EnhancedSessionManager:
    """增强版会话管理器"""
    
    def __init__(self, memory_adapter=None):
        self.memory_adapter = memory_adapter
        self.active_session = None
        self.sessions = {}  # session_id -> session_data
        self.session_index = {
            "by_topic": defaultdict(list),
            "by_date": defaultdict(list),
            "by_status": defaultdict(list)
        }
        self.session_counter = 0
        
    def create_session(self, topic: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建新会话"""
        self.session_counter += 1
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.session_counter:03d}"
        
        session = {
            "id": session_id,
            "topic": topic,
            "status": SessionStatus.ACTIVE.value,
            "start_time": datetime.now(),
            "end_time": None,
            "duration": 0,
            "messages": [],
            "context_chain": [],  # 上下文链
            "metadata": metadata or {},
            "statistics": {
                "message_count": 0,
                "user_message_count": 0,
                "assistant_message_count": 0,
                "tool_call_count": 0,
                "context_injections": 0
            },
            "tags": [],
            "summary": None
        }
        
        # 保存会话
        self.sessions[session_id] = session
        
        # 更新索引
        self._update_index(session)
        
        # 设为活动会话
        if self.active_session:
            self.pause_session()
        self.active_session = session
        
        logger.info(f"Created session: {session_id} - Topic: {topic}")
        return session
        
    def pause_session(self) -> Optional[Dict[str, Any]]:
        """暂停当前会话"""
        if not self.active_session:
            return None
            
        session = self.active_session
        session["status"] = SessionStatus.PAUSED.value
        
        # 更新持续时间
        if session["start_time"]:
            duration = (datetime.now() - session["start_time"]).total_seconds()
            session["duration"] += duration
            
        self._update_index(session)
        self.active_session = None
        
        logger.info(f"Paused session: {session['id']}")
        return session
        
    def resume_session(self, session_id: str = None) -> Optional[Dict[str, Any]]:
        """恢复会话"""
        if session_id:
            session = self.sessions.get(session_id)
        else:
            # 获取最近暂停的会话
            paused_sessions = self.search_sessions(SessionSearchType.BY_STATUS, "paused")
            session = paused_sessions[0] if paused_sessions else None
            
        if not session:
            return None
            
        if session["status"] == SessionStatus.COMPLETED.value:
            logger.warning(f"Cannot resume completed session: {session['id']}")
            return None
            
        # 暂停当前活动会话
        if self.active_session:
            self.pause_session()
            
        # 恢复目标会话
        session["status"] = SessionStatus.ACTIVE.value
        session["start_time"] = datetime.now()  # 重置开始时间
        self.active_session = session
        
        self._update_index(session)
        logger.info(f"Resumed session: {session['id']}")
        return session
        
    def complete_session(self, generate_summary: bool = True) -> Optional[Dict[str, Any]]:
        """完成会话"""
        if not self.active_session:
            return None
            
        session = self.active_session
        session["status"] = SessionStatus.COMPLETED.value
        session["end_time"] = datetime.now()
        
        # 更新最终持续时间
        if session["start_time"]:
            duration = (session["end_time"] - session["start_time"]).total_seconds()
            session["duration"] += duration
            
        # 生成摘要
        if generate_summary:
            session["summary"] = self._generate_session_summary(session)
            
        self._update_index(session)
        self.active_session = None
        
        # 如果有记忆适配器，保存会话元数据
        if self.memory_adapter:
            self._save_session_metadata(session)
            
        logger.info(f"Completed session: {session['id']}")
        return session
        
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """向当前会话添加消息"""
        if not self.active_session:
            logger.warning("No active session to add message")
            return
            
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        
        self.active_session["messages"].append(message)
        
        # 更新统计
        stats = self.active_session["statistics"]
        stats["message_count"] += 1
        if role == "user":
            stats["user_message_count"] += 1
        elif role == "assistant":
            stats["assistant_message_count"] += 1
            
        # 检查工具调用
        if metadata and metadata.get("tool_calls"):
            stats["tool_call_count"] += len(metadata["tool_calls"])
            
    def add_context_injection(self, context: str, query: str):
        """记录上下文注入"""
        if not self.active_session:
            return
            
        self.active_session["context_chain"].append({
            "query": query,
            "context": context,
            "timestamp": datetime.now()
        })
        
        self.active_session["statistics"]["context_injections"] += 1
        
    def search_sessions(self, search_type: SessionSearchType, 
                       query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索会话"""
        results = []
        
        if search_type == SessionSearchType.BY_TOPIC:
            # 按主题搜索
            for session in self.sessions.values():
                if query.lower() in session["topic"].lower():
                    results.append(session)
                    
        elif search_type == SessionSearchType.BY_DATE:
            # 按日期搜索
            try:
                target_date = datetime.strptime(query, "%Y-%m-%d").date()
                for session in self.sessions.values():
                    if session["start_time"].date() == target_date:
                        results.append(session)
            except ValueError:
                logger.error(f"Invalid date format: {query}")
                
        elif search_type == SessionSearchType.BY_KEYWORD:
            # 按关键词搜索消息内容
            for session in self.sessions.values():
                for msg in session["messages"]:
                    if query.lower() in msg["content"].lower():
                        results.append(session)
                        break
                        
        elif search_type == SessionSearchType.BY_STATUS:
            # 按状态搜索
            session_ids = self.session_index["by_status"].get(query, [])
            results = [self.sessions[sid] for sid in session_ids if sid in self.sessions]
            
        # 按时间排序并限制结果数
        results.sort(key=lambda s: s["start_time"], reverse=True)
        return results[:limit]
        
    def get_session_analytics(self, session_id: str = None) -> Dict[str, Any]:
        """获取会话分析"""
        if session_id:
            session = self.sessions.get(session_id)
            if not session:
                return {}
            sessions = [session]
        else:
            sessions = list(self.sessions.values())
            
        if not sessions:
            return {
                "total_sessions": 0,
                "message": "No sessions found"
            }
            
        # 基础统计
        total_messages = sum(s["statistics"]["message_count"] for s in sessions)
        total_duration = sum(s["duration"] for s in sessions)
        
        # 状态分布
        status_distribution = defaultdict(int)
        for s in sessions:
            status_distribution[s["status"]] += 1
            
        # 话题分析
        topic_frequency = defaultdict(int)
        for s in sessions:
            # 简单的话题词频分析
            words = s["topic"].lower().split()
            for word in words:
                if len(word) > 3:  # 忽略短词
                    topic_frequency[word] += 1
                    
        # 时间模式分析
        hour_distribution = defaultdict(int)
        for s in sessions:
            if s["start_time"]:
                hour = s["start_time"].hour
                hour_distribution[hour] += 1
                
        analytics = {
            "total_sessions": len(sessions),
            "total_messages": total_messages,
            "total_duration_seconds": total_duration,
            "average_messages_per_session": total_messages / len(sessions) if sessions else 0,
            "average_duration_seconds": total_duration / len(sessions) if sessions else 0,
            "status_distribution": dict(status_distribution),
            "top_topics": sorted(topic_frequency.items(), key=lambda x: x[1], reverse=True)[:10],
            "activity_by_hour": dict(hour_distribution),
            "sessions_with_context": sum(1 for s in sessions if s["context_chain"]),
            "total_context_injections": sum(s["statistics"]["context_injections"] for s in sessions)
        }
        
        return analytics
        
    def export_session(self, session_id: str, format: str = "json") -> str:
        """导出会话"""
        session = self.sessions.get(session_id)
        if not session:
            return ""
            
        if format == "json":
            # JSON 格式导出
            export_data = {
                "session": self._serialize_session(session),
                "export_time": datetime.now().isoformat(),
                "version": "2.0"
            }
            return json.dumps(export_data, indent=2, ensure_ascii=False)
            
        elif format == "markdown":
            # Markdown 格式导出
            lines = [
                f"# 会话记录：{session['topic']}",
                f"",
                f"**会话ID**: {session['id']}  ",
                f"**开始时间**: {session['start_time'].strftime('%Y-%m-%d %H:%M:%S')}  ",
                f"**持续时间**: {session['duration']:.1f} 秒  ",
                f"**消息数量**: {session['statistics']['message_count']}  ",
                f"",
                "## 对话内容",
                ""
            ]
            
            for msg in session["messages"]:
                # 处理时间戳（可能是字符串或datetime对象）
                if isinstance(msg["timestamp"], str):
                    timestamp = msg["timestamp"]
                else:
                    timestamp = msg["timestamp"].strftime("%H:%M:%S")
                role_emoji = "👤" if msg["role"] == "user" else "🤖"
                lines.append(f"### {role_emoji} {msg['role'].title()} ({timestamp})")
                lines.append("")
                lines.append(msg["content"])
                lines.append("")
                
                # 如果有工具调用
                if msg["metadata"].get("tool_calls"):
                    lines.append("**工具调用**:")
                    for tool in msg["metadata"]["tool_calls"]:
                        lines.append(f"- {tool['tool']}: {tool.get('arguments', {})}")
                    lines.append("")
                    
            # 添加摘要
            if session.get("summary"):
                lines.extend([
                    "## 会话摘要",
                    "",
                    session["summary"],
                    ""
                ])
                
            # 添加统计
            stats = session["statistics"]
            lines.extend([
                "## 统计信息",
                "",
                f"- 用户消息: {stats['user_message_count']}",
                f"- 助手消息: {stats['assistant_message_count']}",
                f"- 工具调用: {stats['tool_call_count']}",
                f"- 上下文注入: {stats['context_injections']}",
                ""
            ])
            
            return "\n".join(lines)
            
        else:
            return f"Unsupported format: {format}"
            
    def archive_old_sessions(self, days: int = 30):
        """归档旧会话"""
        cutoff_date = datetime.now() - timedelta(days=days)
        archived_count = 0
        
        for session in self.sessions.values():
            if (session["status"] == SessionStatus.COMPLETED.value and
                session.get("end_time") and 
                session["end_time"] < cutoff_date):
                
                session["status"] = SessionStatus.ARCHIVED.value
                self._update_index(session)
                archived_count += 1
                
        logger.info(f"Archived {archived_count} sessions older than {days} days")
        return archived_count
        
    def _update_index(self, session: Dict[str, Any]):
        """更新会话索引"""
        session_id = session["id"]
        
        # 清理旧索引
        for index_type in self.session_index.values():
            for key, session_list in index_type.items():
                if session_id in session_list:
                    session_list.remove(session_id)
                    
        # 更新新索引
        self.session_index["by_topic"][session["topic"]].append(session_id)
        self.session_index["by_status"][session["status"]].append(session_id)
        
        if session["start_time"]:
            date_key = session["start_time"].strftime("%Y-%m-%d")
            self.session_index["by_date"][date_key].append(session_id)
            
    def _generate_session_summary(self, session: Dict[str, Any]) -> str:
        """生成会话摘要"""
        summary_parts = [
            f"会话主题：{session['topic']}",
            f"持续时间：{session['duration']:.1f} 秒",
            f"消息交流：{session['statistics']['message_count']} 条",
            f"开始时间：{session['start_time'].strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        
        # 添加关键讨论点
        if session["messages"]:
            summary_parts.append("\n关键讨论点：")
            
            # 提取用户的主要问题
            user_questions = [
                msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                for msg in session["messages"]
                if msg["role"] == "user"
            ][:3]  # 最多3个
            
            for i, question in enumerate(user_questions, 1):
                summary_parts.append(f"{i}. {question}")
                
        # 添加统计信息
        stats = session["statistics"]
        summary_parts.extend([
            "",
            "会话统计：",
            f"- 上下文注入次数：{stats['context_injections']}",
            f"- 工具调用次数：{stats['tool_call_count']}"
        ])
        
        return "\n".join(summary_parts)
        
    def _serialize_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """序列化会话数据"""
        serialized = session.copy()
        
        # 转换 datetime 对象
        if serialized.get("start_time"):
            serialized["start_time"] = serialized["start_time"].isoformat()
        if serialized.get("end_time"):
            serialized["end_time"] = serialized["end_time"].isoformat()
            
        # 序列化消息中的时间戳
        for msg in serialized.get("messages", []):
            if isinstance(msg.get("timestamp"), datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
                
        # 序列化上下文链中的时间戳
        for ctx in serialized.get("context_chain", []):
            if isinstance(ctx.get("timestamp"), datetime):
                ctx["timestamp"] = ctx["timestamp"].isoformat()
                
        return serialized
        
    def _save_session_metadata(self, session: Dict[str, Any]):
        """保存会话元数据到记忆系统"""
        if not self.memory_adapter:
            return
            
        try:
            # 保存会话摘要作为记忆
            metadata = {
                "type": "session_summary",
                "session_id": session["id"],
                "topic": session["topic"],
                "duration": session["duration"],
                "message_count": session["statistics"]["message_count"]
            }
            
            self.memory_adapter.save_conversation(
                user_prompt=f"[会话] {session['topic']}",
                assistant_response=session.get("summary", "会话无摘要"),
                metadata=metadata
            )
            
            logger.info(f"Saved session metadata: {session['id']}")
        except Exception as e:
            logger.error(f"Failed to save session metadata: {e}")


# 测试函数
def test_enhanced_session_manager():
    """测试增强版会话管理器"""
    print("测试增强版会话管理器...")
    
    manager = EnhancedSessionManager()
    
    # 创建会话
    session1 = manager.create_session("Python编程学习")
    print(f"✓ 创建会话: {session1['id']}")
    
    # 添加消息
    manager.add_message("user", "什么是装饰器？")
    manager.add_message("assistant", "装饰器是Python中的高级特性...")
    manager.add_context_injection("之前讨论过函数式编程", "装饰器")
    
    # 暂停会话
    manager.pause_session()
    
    # 创建另一个会话
    session2 = manager.create_session("机器学习基础")
    manager.add_message("user", "什么是神经网络？")
    manager.add_message("assistant", "神经网络是一种模仿生物神经网络的计算模型...")
    
    # 完成会话
    completed = manager.complete_session()
    print(f"✓ 完成会话: {completed['id']}")
    
    # 搜索会话
    results = manager.search_sessions(SessionSearchType.BY_TOPIC, "Python")
    print(f"✓ 搜索结果: 找到 {len(results)} 个会话")
    
    # 获取分析
    analytics = manager.get_session_analytics()
    print(f"✓ 会话分析: {analytics['total_sessions']} 个会话，{analytics['total_messages']} 条消息")
    
    # 导出会话
    markdown_export = manager.export_session(session1['id'], "markdown")
    print(f"✓ 导出会话（Markdown格式）: {len(markdown_export)} 字符")
    
    print("\n测试完成！")


if __name__ == "__main__":
    test_enhanced_session_manager()