#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sage Core Service Implementation - 核心服务实现
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .interfaces import (
    ISageService, 
    MemoryContent, 
    SearchOptions, 
    SessionInfo, 
    AnalysisResult
)
from .config import ConfigManager
from .database import DatabaseConnection
from .database.transaction import TransactionManager
from .memory import MemoryManager, TextVectorizer
from .analysis import MemoryAnalyzer
from .session import SessionManager

logger = logging.getLogger(__name__)


class SageCore(ISageService):
    """Sage 核心服务实现"""
    
    def __init__(self):
        """初始化核心服务"""
        self.config_manager: Optional[ConfigManager] = None
        self.db_connection: Optional[DatabaseConnection] = None
        self.transaction_manager: Optional[TransactionManager] = None
        self.memory_manager: Optional[MemoryManager] = None
        self.session_manager: Optional[SessionManager] = None
        self.analyzer: Optional[MemoryAnalyzer] = None
        self._initialized = False
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """初始化服务"""
        if self._initialized:
            return
        
        try:
            logger.info("正在初始化 Sage Core 服务...")
            
            # 初始化配置管理器
            self.config_manager = ConfigManager()
            if config:
                # 更新配置
                for key, value in config.items():
                    self.config_manager.set(key, value)
            
            # 初始化数据库连接
            db_config = self.config_manager.get_database_config()
            self.db_connection = DatabaseConnection(db_config)
            await self.db_connection.connect()
            
            # 初始化事务管理器
            if hasattr(self.db_connection, 'pool') and self.db_connection.pool:
                self.transaction_manager = TransactionManager(self.db_connection.pool)
                logger.info("事务管理器已初始化")
            else:
                logger.warning("数据库连接没有连接池，事务管理将被禁用")
                self.transaction_manager = None
            
            # 初始化向量化器
            embedding_config = self.config_manager.get_embedding_config()
            vectorizer = TextVectorizer(
                model_name=embedding_config.get('model', 'Qwen/Qwen3-Embedding-8B'),
                device=embedding_config.get('device', 'cpu')
            )
            
            # 初始化记忆管理器 - 传入事务管理器
            self.memory_manager = MemoryManager(self.db_connection, vectorizer, self.transaction_manager)
            await self.memory_manager.initialize()
            
            # 初始化会话管理器
            self.session_manager = SessionManager(self.memory_manager)
            
            # 初始化分析器
            self.analyzer = MemoryAnalyzer(self.memory_manager)
            
            self._initialized = True
            logger.info("Sage Core 服务初始化完成")
            
        except Exception as e:
            logger.error(f"初始化服务失败：{e}")
            raise
    
    async def save_memory(self, content: MemoryContent) -> str:
        """保存记忆"""
        self._ensure_initialized()
        return await self.memory_manager.save(content)
    
    async def search_memory(self, query: str, options: SearchOptions) -> List[Dict[str, Any]]:
        """搜索记忆"""
        self._ensure_initialized()
        return await self.memory_manager.search(query, options)
    
    async def get_context(self, query: str, max_results: int = 10) -> str:
        """获取相关上下文"""
        self._ensure_initialized()
        return await self.memory_manager.get_context(query, max_results)
    
    async def manage_session(self, action: str, session_id: Optional[str] = None) -> SessionInfo:
        """管理会话"""
        self._ensure_initialized()
        
        if action == "create":
            new_session_id = await self.session_manager.create_session()
            return await self._get_session_info(new_session_id)
        
        elif action == "switch":
            if not session_id:
                raise ValueError("切换会话需要提供 session_id")
            await self.session_manager.switch_session(session_id)
            return await self._get_session_info(session_id)
        
        elif action == "info":
            target_session = session_id or self.session_manager.current_session_id
            return await self._get_session_info(target_session)
        
        elif action == "list":
            sessions = await self.session_manager.list_sessions()
            # 返回当前会话信息，并附带会话列表
            current_info = await self._get_session_info(self.session_manager.current_session_id)
            current_info.metadata['all_sessions'] = sessions
            return current_info
        
        else:
            raise ValueError(f"未知的会话操作：{action}")
    
    async def analyze_memory(self, session_id: Optional[str] = None, 
                           analysis_type: str = "general") -> AnalysisResult:
        """分析记忆"""
        self._ensure_initialized()
        return await self.analyzer.analyze(session_id, analysis_type)
    
    async def generate_prompt(self, context: str, style: str = "default") -> str:
        """生成智能提示 - 使用完整RAG功能"""
        import time
        start_time = time.time()
        logger.info(f"[RAG流程] 开始生成智能提示，输入上下文长度: {len(context)} 字符")
        
        self._ensure_initialized()
        
        try:
            # 1. 获取相关历史记忆 - 激活RAG功能
            step1_start = time.time()
            if context and context.strip():
                relevant_context = await self.memory_manager.get_context(context, max_results=10)
                step1_time = time.time() - step1_start
                logger.info(f"[RAG流程] 步骤1-向量搜索完成: {len(relevant_context)} 字符, 耗时: {step1_time:.3f}秒")
            else:
                relevant_context = ""
                logger.info(f"[RAG流程] 步骤1-无输入上下文，跳过向量搜索")
            
            # 2. 使用Memory Fusion模板压缩上下文
            step2_start = time.time()
            fused_context = await self._apply_memory_fusion(relevant_context, context)
            step2_time = time.time() - step2_start
            logger.info(f"[RAG流程] 步骤2-Memory Fusion处理完成: 输出长度 {len(fused_context)} 字符, 耗时: {step2_time:.3f}秒")
            
            # 3. 基于风格和上下文生成智能提示
            step3_start = time.time()
            enhanced_prompt = await self._generate_contextual_prompt(fused_context, style)
            step3_time = time.time() - step3_start
            total_time = time.time() - start_time
            
            logger.info(f"[RAG流程] 步骤3-智能提示生成完成: {len(enhanced_prompt)} 字符, 耗时: {step3_time:.3f}秒")
            logger.info(f"[RAG流程] 整个流程完成，总耗时: {total_time:.3f}秒")
            return enhanced_prompt
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[RAG流程] 生成智能提示失败: {e}, 总耗时: {total_time:.3f}秒")
            # 降级到基础提示
            return await self._generate_fallback_prompt(style)
    
    async def _apply_memory_fusion(self, relevant_context: str, query_context: str) -> str:
        """应用Memory Fusion模板压缩上下文"""
        import time
        start_time = time.time()
        
        try:
            if not relevant_context:
                logger.info(f"[Memory Fusion] 无相关上下文，直接返回查询内容")
                return query_context
            
            # 读取Memory Fusion模板
            from pathlib import Path
            template_path = Path(__file__).parent.parent / "prompts" / "memory_fusion_prompt_programming.txt"
            
            template_read_start = time.time()
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    template = f.read()
                template_read_time = time.time() - template_read_start
                logger.info(f"[Memory Fusion] 模板读取完成: {len(template)} 字符, 耗时: {template_read_time:.3f}秒")
                
                # 替换模板中的retrieved_passages占位符
                fused_template = template.replace("{retrieved_passages}", relevant_context)
                logger.info(f"[Memory Fusion] 模板占位符替换完成: 融合后长度 {len(fused_template)} 字符")
                
                # 调用AI压缩（当前为简化实现）
                compress_start = time.time()
                compressed_context = await self._compress_context_with_ai(fused_template, query_context)
                compress_time = time.time() - compress_start
                total_time = time.time() - start_time
                logger.info(f"[Memory Fusion] 上下文压缩完成: {len(compressed_context)} 字符, 耗时: {compress_time:.3f}秒")
                logger.info(f"[Memory Fusion] 整个Memory Fusion处理完成，总耗时: {total_time:.3f}秒")
                return compressed_context
            else:
                logger.warning(f"[Memory Fusion] 模板文件不存在: {template_path}，使用原始上下文")
                return f"{relevant_context}\n\n当前查询: {query_context}"
                
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[Memory Fusion] 处理失败: {e}, 耗时: {total_time:.3f}秒")
            return relevant_context
    
    async def _compress_context_with_ai(self, template: str, query: str) -> str:
        """使用AI模型压缩上下文 - TODO: 集成DeepSeek v2.5 API"""
        import time
        start_time = time.time()
        
        try:
            logger.warning(f"[AI压缩] 注意：DeepSeek v2.5 API调用尚未实现，使用本地简化逻辑")
            logger.info(f"[AI压缩] 开始处理模板，输入长度: {len(template)} 字符")
            
            # TODO: 实现DeepSeek v2.5 API调用
            # 目前使用简化的上下文提取逻辑
            process_start = time.time()
            lines = template.split('\n')
            relevant_lines = []
            
            keywords = ['项目', '功能', '问题', '代码', '实现']
            logger.info(f"[AI压缩] 使用关键词匹配: {keywords}")
            
            for line in lines:
                if any(keyword in line.lower() for keyword in keywords):
                    relevant_lines.append(line.strip())
            
            process_time = time.time() - process_start
            
            if relevant_lines:
                compressed = '\n'.join(relevant_lines[:10])  # 限制为10行
                result = f"上下文摘要:\n{compressed}\n\n当前查询: {query}"
                total_time = time.time() - start_time
                logger.info(f"[AI压缩] 本地关键词匹配完成: 提取 {len(relevant_lines)} 行，输出 {len(result)} 字符，处理耗时: {process_time:.3f}秒，总耗时: {total_time:.3f}秒")
                return result
            else:
                total_time = time.time() - start_time
                logger.info(f"[AI压缩] 无匹配内容，返回原查询，总耗时: {total_time:.3f}秒")
                return f"当前查询: {query}"
                
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[AI压缩] 本地处理失败: {e}，总耗时: {total_time:.3f}秒")
            return query
    
    async def _generate_contextual_prompt(self, context: str, style: str) -> str:
        """基于上下文和风格生成智能提示"""
        try:
            # 基于实际上下文内容生成智能提示
            if not context or "没有找到相关的历史记忆" in context:
                # 没有相关上下文时的通用提示
                return "我来为您提供帮助。请告诉我您需要了解什么。"
            
            # 从上下文中提取关键信息生成个性化提示
            context_lower = context.lower()
            
            # 分析上下文中的主要话题
            topics = []
            if "hook" in context_lower or "钩子" in context_lower:
                topics.append("Hook功能")
            if "数据库" in context_lower or "database" in context_lower:
                topics.append("数据库")
            if "mcp" in context_lower or "服务器" in context_lower:
                topics.append("MCP服务")
            if "代码" in context_lower or "实现" in context_lower or "功能" in context_lower:
                topics.append("代码实现")
            if "错误" in context_lower or "问题" in context_lower or "bug" in context_lower:
                topics.append("问题排查")
            if "测试" in context_lower or "验证" in context_lower:
                topics.append("测试验证")
            if "配置" in context_lower or "设置" in context_lower:
                topics.append("配置管理")
            
            # 基于话题生成个性化提示
            if topics:
                topic_str = "、".join(topics[:2])  # 最多提及2个话题
                
                if style == "question":
                    return f"基于您之前关于{topic_str}的讨论，还有什么具体问题需要深入探讨？"
                elif style == "suggestion":
                    return f"建议我们可以进一步优化{topic_str}相关的实现。需要我提供具体的改进方案吗？"
                else:
                    return f"根据您之前的{topic_str}经验，我可以帮您分析相关技术细节或提供解决方案。"
            else:
                # 通用但更智能的提示
                if "时间：" in context:  # 说明有历史记忆
                    return "基于我们之前的对话历史，我可以为您提供更有针对性的建议和解决方案。"
                else:
                    return "根据上下文，我可以为您提供技术支持和专业建议。"
                    
        except Exception as e:
            logger.error(f"生成上下文提示失败: {e}")
            return await self._generate_fallback_prompt(style)
    
    async def _generate_fallback_prompt(self, style: str) -> str:
        """生成降级提示"""
        if style == "question":
            prompts = [
                "有什么具体问题需要深入探讨吗？",
                "您希望了解哪些技术细节？",
                "还有什么方面需要进一步分析？"
            ]
        elif style == "suggestion":
            prompts = [
                "建议提供更多具体信息，以便我给出精准建议。",
                "我可以帮您分析技术方案或提供最佳实践建议。",
                "建议我们深入讨论具体的实现细节。"
            ]
        else:  # default
            prompts = [
                "我可以帮您解决技术问题或提供专业建议。",
                "请告诉我更多具体信息，以便提供针对性帮助。",
                "让我们深入探讨您关心的技术话题。"
            ]
        
        import random
        return random.choice(prompts)
    
    async def export_session(self, session_id: str, format: str = "json") -> bytes:
        """导出会话"""
        self._ensure_initialized()
        
        data = await self.memory_manager.export_session(session_id, format)
        
        if format == "json":
            import json
            return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        elif format == "markdown":
            return data.encode('utf-8')
        else:
            raise ValueError(f"不支持的导出格式：{format}")
    
    async def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        status = {
            'initialized': self._initialized,
            'service': 'sage_core',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if self._initialized:
            # 添加各组件状态
            status['components'] = {
                'config_manager': self.config_manager is not None,
                'database': self.db_connection is not None,
                'memory_manager': self.memory_manager is not None,
                'session_manager': self.session_manager is not None,
                'analyzer': self.analyzer is not None
            }
            
            # 添加当前会话信息
            if self.session_manager:
                status['current_session'] = self.session_manager.current_session_id
            
            # 添加统计信息
            try:
                stats = await self.memory_manager.storage.get_statistics()
                status['statistics'] = stats
            except:
                pass
        
        return status
    
    async def cleanup(self) -> None:
        """清理资源"""
        # 等待所有事务完成
        if self.transaction_manager:
            try:
                await self.transaction_manager.wait_for_all_transactions(timeout=10.0)
            except TimeoutError:
                logger.warning("等待事务完成超时")
        
        if self.memory_manager:
            await self.memory_manager.cleanup()
        
        if self.db_connection:
            await self.db_connection.disconnect()
        
        self._initialized = False
        logger.info("Sage Core 服务已清理")
    
    def _ensure_initialized(self) -> None:
        """确保服务已初始化"""
        if not self._initialized:
            raise RuntimeError("服务未初始化，请先调用 initialize()")
    
    async def _get_session_info(self, session_id: str) -> SessionInfo:
        """获取会话信息并转换为 SessionInfo 对象"""
        info = await self.memory_manager.get_session_info(session_id)
        
        return SessionInfo(
            session_id=info['session_id'],
            created_at=datetime.fromisoformat(info['first_memory']) if info['first_memory'] else datetime.utcnow(),
            memory_count=info['memory_count'],
            last_active=datetime.fromisoformat(info['last_memory']) if info['last_memory'] else datetime.utcnow(),
            metadata={
                'is_current': info['is_current']
            }
        )