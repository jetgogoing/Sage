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
                # 从配置读取max_results值
                memory_fusion_config = self.config_manager.get_memory_fusion_config()
                max_results = memory_fusion_config.get('max_results', 10)
                
                # 验证配置值的有效性
                if not isinstance(max_results, int) or max_results < 1 or max_results > 100:
                    logger.warning(f"[RAG流程] SAGE_MAX_RESULTS配置值无效: {max_results}，使用默认值10")
                    max_results = 10
                
                logger.info(f"[RAG流程] 使用SAGE_MAX_RESULTS配置: {max_results}")
                
                relevant_context = await self.memory_manager.get_context(context, max_results=max_results)
                step1_time = time.time() - step1_start
                logger.info(f"[RAG流程] 步骤1-向量搜索完成: {len(relevant_context)} 字符 (限制{max_results}个结果), 耗时: {step1_time:.3f}秒")
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
        """直接调用AI压缩上下文 - 简化Memory Fusion逻辑"""
        import time
        start_time = time.time()
        
        try:
            if not relevant_context:
                logger.info(f"[AI压缩] 无相关上下文，直接返回查询内容")
                return query_context
            
            # 提取上下文片段用于AI压缩 - 提高质量过滤标准
            retrieved_chunks = [chunk.strip() for chunk in relevant_context.split('\n') if chunk.strip() and len(chunk.strip()) > 50]
            logger.info(f"[AI压缩] 准备压缩 {len(retrieved_chunks)} 个上下文片段 (>50字符过滤)")
            
            # 直接调用AI压缩，让TextGenerator处理模板逻辑
            compress_start = time.time()
            compressed_context = await self._compress_context_with_ai("", query_context, retrieved_chunks)
            compress_time = time.time() - compress_start
            total_time = time.time() - start_time
            
            logger.info(f"[AI压缩] 上下文压缩完成: {len(compressed_context)} 字符, 耗时: {compress_time:.3f}秒")
            logger.info(f"[AI压缩] 整个处理完成，总耗时: {total_time:.3f}秒")
            return compressed_context
                
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[AI压缩] 处理失败: {e}, 耗时: {total_time:.3f}秒")
            return relevant_context
    
    async def _compress_context_with_ai(self, template: str, query: str, retrieved_chunks: List[str] = None) -> str:
        """使用SiliconFlow QwenLong进行智能上下文压缩"""
        import time
        start_time = time.time()
        
        try:
            # 检查AI压缩是否启用
            ai_config = self.config_manager.get_ai_compression_config()
            if not ai_config.get('enable', True):
                logger.info(f"[AI压缩] AI压缩功能已禁用，使用降级逻辑")
                return await self._fallback_context_extraction(template, query)
            
            logger.info(f"[AI压缩] 开始调用SiliconFlow QwenLong-L1-32B")
            logger.info(f"[AI压缩] 输入模板长度: {len(template)} 字符，上下文片段: {len(retrieved_chunks or [])} 个")
            
            # 初始化TextGenerator
            from .memory.text_generator import TextGenerator
            
            text_generator = TextGenerator(model_name=ai_config.get('model', 'Tongyi-Zhiwen/QwenLong-L1-32B'))
            await text_generator.initialize()
            
            # 使用简化的内置模板，避免文件IO
            fusion_template = "请基于以下历史上下文和用户查询，生成简洁而相关的记忆背景"
            logger.info(f"[AI压缩] 使用内置模板进行上下文压缩")
            
            # 使用检索到的上下文片段，如果没有则解析template
            if not retrieved_chunks:
                # 从template中提取相关内容作为chunks
                retrieved_chunks = [line.strip() for line in template.split('\n') if line.strip() and len(line.strip()) > 10][:10]
            
            # 调用QwenLong进行压缩
            compression_result = await text_generator.compress_memory_context(
                fusion_template=fusion_template,
                user_query=query,
                retrieved_chunks=retrieved_chunks,
                max_tokens=ai_config.get('max_tokens', 2000),
                temperature=ai_config.get('temperature', 0.3),
                timeout=ai_config.get('timeout_seconds', 30)
            )
            
            total_time = time.time() - start_time
            logger.info(f"[AI压缩] QwenLong压缩完成: 生成 {len(compression_result)} 字符，耗时: {total_time:.3f}秒")
            
            # 验证结果质量
            if compression_result and len(compression_result.strip()) > 20:
                return compression_result
            else:
                logger.warning(f"[AI压缩] 压缩结果质量不佳，使用降级逻辑")
                return await self._fallback_context_extraction(template, query)
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[AI压缩] SiliconFlow调用失败: {e}，耗时: {total_time:.3f}秒")
            
            # 检查是否允许降级
            if ai_config.get('fallback_on_error', True):
                logger.info(f"[AI压缩] 启用降级策略")
                return await self._fallback_context_extraction(template, query)
            else:
                # 不允许降级时直接返回原查询
                return f"当前查询: {query}"
    
    async def _fallback_context_extraction(self, template: str, query: str) -> str:
        """智能降级处理：使用 Reranker 优化上下文选择"""
        import time
        start_time = time.time()
        
        try:
            logger.info(f"[AI压缩] 使用智能降级处理（Reranker 模式）")
            
            # 分割模板为记忆片段
            lines = template.split('\n')
            
            # 基础过滤：去除太短的无意义内容
            meaningful_chunks = []
            for line in lines:
                line_stripped = line.strip()
                if line_stripped and len(line_stripped) > 10:
                    # 解析记忆格式（如 "[记忆 1] ..."）
                    if line_stripped.startswith('[记忆'):
                        # 跳过记忆标记行
                        continue
                    meaningful_chunks.append(line_stripped)
            
            if not meaningful_chunks:
                logger.info(f"[AI压缩] 无有效记忆内容")
                return f"暂无相关历史记忆。当前查询：{query}"
            
            logger.info(f"[AI压缩] 初步筛选：{len(meaningful_chunks)} 个有效片段")
            
            # 尝试使用 Reranker 进行语义重排
            try:
                from .memory.reranker import TextReranker
                
                reranker = TextReranker()
                # 从环境变量读取候选数量配置
                import os
                reranker_candidates = int(os.getenv('SAGE_RERANKER_CANDIDATES', '100'))
                chunks_to_rerank = meaningful_chunks[:reranker_candidates]
                
                # 执行重排，获取最相关的 top_k 个
                reranker_top_k = int(os.getenv('SAGE_RERANKER_TOP_K', '10'))
                logger.info(f"[AI压缩] 开始 Reranker 重排：{len(chunks_to_rerank)} 个候选，返回 top {reranker_top_k}")
                ranked_chunks = await reranker.rerank(
                    query=query,
                    documents=chunks_to_rerank,
                    top_k=reranker_top_k,
                    return_scores=False
                )
                
                # 估算 token 数量（简单估计：1个中文字符≈1.5 tokens）
                max_output_tokens = int(os.getenv('SAGE_MAX_OUTPUT_TOKENS', '2000'))
                total_chars = sum(len(chunk) for chunk in ranked_chunks)
                estimated_tokens = int(total_chars * 1.5)
                
                # 如果超出 token 限制，进一步裁剪
                if estimated_tokens > max_output_tokens:
                    logger.warning(f"[AI压缩] 预估 {estimated_tokens} tokens 超出限制 {max_output_tokens}，进行裁剪")
                    # 逐个累加直到接近限制
                    trimmed_chunks = []
                    current_tokens = 0
                    for chunk in ranked_chunks:
                        chunk_tokens = int(len(chunk) * 1.5)
                        if current_tokens + chunk_tokens <= max_output_tokens:
                            trimmed_chunks.append(chunk)
                            current_tokens += chunk_tokens
                        else:
                            # 部分截取最后一个 chunk
                            remaining_tokens = max_output_tokens - current_tokens
                            remaining_chars = int(remaining_tokens / 1.5)
                            if remaining_chars > 50:  # 至少保留 50 字符才有意义
                                trimmed_chunks.append(chunk[:remaining_chars] + "...")
                            break
                    ranked_chunks = trimmed_chunks
                    estimated_tokens = current_tokens
                
                logger.info(f"[AI压缩] Reranker 完成：选出 {len(ranked_chunks)} 个最相关片段，"
                          f"约 {estimated_tokens} tokens（限制 {max_output_tokens}）")
                
                # 格式化输出
                formatted_memories = []
                for i, chunk in enumerate(ranked_chunks, 1):
                    formatted_memories.append(f"[相关记忆 {i}] {chunk}")
                
                result = f"""基于语义相关性筛选的历史记忆（共 {len(ranked_chunks)} 条）：

{chr(10).join(formatted_memories)}

当前查询：{query}

以上记忆已通过 AI 模型进行语义相关性排序，请基于这些上下文为用户提供帮助。"""
                
                total_time = time.time() - start_time
                logger.info(f"[AI压缩] 智能降级完成：输出 {len(result)} 字符，"
                          f"耗时 {total_time:.3f}秒")
                return result
                
            except Exception as e:
                logger.warning(f"[AI压缩] Reranker 处理失败：{e}，回退到简单模式")
                # 回退到简单截取
                return await self._simple_fallback(meaningful_chunks, query, start_time)
                
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[AI压缩] 降级处理失败: {e}，耗时: {total_time:.3f}秒")
            return f"我可以帮您分析技术问题。您的查询：{query}"
    
    async def _simple_fallback(self, chunks: List[str], query: str, start_time: float) -> str:
        """简单降级：基础的关键词匹配"""
        import time
        
        # 简单关键词匹配
        query_words = set(query.lower().split())
        scored_chunks = []
        
        for chunk in chunks[:50]:  # 最多处理 50 个
            chunk_lower = chunk.lower()
            score = sum(1 for word in query_words if word in chunk_lower)
            if score > 0:
                scored_chunks.append((chunk, score))
        
        # 按分数排序
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # 取前 10 个
        final_chunks = [chunk for chunk, _ in scored_chunks[:10]]
        
        if final_chunks:
            result = f"""基于关键词匹配的历史记忆（共 {len(final_chunks)} 条）：

{chr(10).join(f'- {chunk}' for chunk in final_chunks)}

当前查询：{query}"""
        else:
            result = f"暂无相关历史记忆。当前查询：{query}"
        
        total_time = time.time() - start_time
        logger.info(f"[AI压缩] 简单降级完成：{len(final_chunks)} 条记忆，"
                  f"耗时 {total_time:.3f}秒")
        return result
    
    async def _generate_contextual_prompt(self, context: str, style: str) -> str:
        """基于上下文和风格生成智能提示"""
        try:
            # 基于实际上下文内容生成智能提示
            if not context or "没有找到相关的历史记忆" in context:
                # 没有相关上下文时的通用提示
                return "我来为您提供帮助。请告诉我您需要了解什么。"
            
            # 检查是否是AI压缩生成的智能内容
            # AI压缩的内容通常较长且包含结构化信息
            if len(context) > 100 and ("记忆背景" in context or "当前" in context or "集成" in context or "执行计划" in context):
                logger.info(f"[RAG流程] 检测到AI压缩内容，直接返回: {len(context)} 字符")
                # 这是AI压缩生成的智能背景，直接返回
                return context
            
            # 对于较短或未经AI处理的上下文，使用原有的关键词匹配逻辑
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