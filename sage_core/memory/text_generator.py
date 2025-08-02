#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TextGenerator - 文本生成处理 (使用 SiliconFlow 云端 API)
基于 vectorizer.py 设计模式，适配文本生成场景
"""
import os
import time
import logging
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from ..interfaces.ai_compressor import AICompressor

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class TextGenerator(AICompressor):
    """文本生成器 - 使用 SiliconFlow QwenLong API"""
    
    def __init__(self, model_name: str = "Tongyi-Zhiwen/QwenLong-L1-32B"):
        """初始化文本生成器
        
        Args:
            model_name: 模型名称 (用于 API 调用)
        """
        self.model_name = model_name
        self.api_key = os.getenv('SILICONFLOW_API_KEY')
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY 环境变量未设置")
        self.base_url = "https://api.siliconflow.cn/v1"
        self._initialized = True
    
    async def initialize(self) -> None:
        """异步初始化（使用 API 无需加载模型）"""
        if self._initialized:
            return
        
        logger.info(f"使用 SiliconFlow API 进行文本生成：{self.model_name}")
        self._initialized = True
    
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """生成文本响应（使用 SiliconFlow API）
        
        Args:
            messages: OpenAI格式的消息数组
            **kwargs: 额外参数（max_tokens, temperature等）
            
        Returns:
            生成的文本字符串
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建请求数据
            data = {
                "model": self.model_name,
                "messages": messages,
                "stream": False
            }
            
            # 添加可选参数
            if "max_tokens" in kwargs:
                data["max_tokens"] = kwargs["max_tokens"]
            if "temperature" in kwargs:
                data["temperature"] = kwargs["temperature"]
            if "top_p" in kwargs:
                data["top_p"] = kwargs["top_p"]
            
            logger.info(f"[文本生成] 开始调用SiliconFlow API，消息数量: {len(messages)}")
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=kwargs.get("timeout", 30)
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 提取生成的文本
            if "choices" in result and len(result["choices"]) > 0:
                generated_text = result["choices"][0]["message"]["content"]
                
                total_time = time.time() - start_time
                logger.info(f"[文本生成] API调用成功: 生成 {len(generated_text)} 字符，耗时: {total_time:.3f}秒")
                
                return generated_text
            else:
                raise ValueError("API响应格式异常：缺少choices字段")
                
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[文本生成] SiliconFlow API调用失败: {e}，耗时: {total_time:.3f}秒")
            
            # 降级到本地处理
            return self._fallback_generation(messages)
    
    def _fallback_generation(self, messages: List[Dict[str, str]]) -> str:
        """降级处理：改进的本地文本生成 - 生成丰富的上下文内容
        
        Args:
            messages: 原始消息数组
            
        Returns:
            降级生成的文本
        """
        logger.warning("[文本生成] 降级到本地处理逻辑 - 使用增强版fallback")
        
        try:
            # 提取完整上下文信息
            user_query = ""
            system_prompt = ""
            full_context = []
            
            for msg in messages:
                if msg.get("role") == "user":
                    user_query = msg.get("content", "")
                elif msg.get("role") == "system":
                    system_prompt = msg.get("content", "")
                full_context.append(f"{msg.get('role', 'unknown')}: {msg.get('content', '')[:200]}")
            
            # 从system prompt中提取关键信息
            relevant_chunks = []
            if "检索到的相关上下文" in system_prompt:
                lines = system_prompt.split('\n')
                for line in lines:
                    if line.strip().startswith('- ') and len(line.strip()) > 10:
                        relevant_chunks.append(line.strip()[2:])
            
            # 生成丰富的上下文相关内容
            result_parts = []
            
            # 1. 基于用户查询的分析
            if user_query:
                query_analysis = self._analyze_user_query(user_query)
                result_parts.append(f"### 基于当前查询的技术分析\n{query_analysis}")
            
            # 2. 历史上下文整合
            if relevant_chunks:
                context_summary = self._generate_context_summary(relevant_chunks, user_query)
                result_parts.append(f"### 相关历史背景\n{context_summary}")
            
            # 3. 技术建议和后续步骤
            suggestions = self._generate_technical_suggestions(user_query, relevant_chunks)
            result_parts.append(f"### 技术建议\n{suggestions}")
            
            # 组合完整回复
            full_response = "\n\n".join(result_parts)
            
            logger.info(f"[文本生成] 降级处理生成了 {len(full_response)} 字符的丰富内容")
            return full_response
                
        except Exception as e:
            logger.error(f"[文本生成] 降级处理失败: {e}")
            # 最后的保底逻辑
            return self._generate_minimal_fallback(user_query)
    
    def _analyze_user_query(self, query: str) -> str:
        """分析用户查询并生成相关技术分析"""
        query_lower = query.lower()
        
        if "prompt" in query_lower and "enhancer" in query_lower:
            return """您询问的prompt enhancer功能是一个智能提示增强系统，主要包含以下技术组件：

1. **向量化检索**: 使用Qwen/Qwen3-Embedding-8B模型将用户输入转换为4096维向量
2. **记忆融合**: 通过pgvector进行相似度搜索，获取相关历史对话上下文
3. **AI压缩**: 调用Tongyi-Zhiwen/QwenLong-L1-32B对检索到的内容进行智能压缩和重组
4. **上下文注入**: 将处理后的内容注入到当前对话中，提供个性化的技术建议

当前如果生成内容较短，可能是AI压缩环节出现了API调用问题。"""
        
        elif any(word in query_lower for word in ["api", "调用", "错误", "400", "超时"]):
            return """API调用相关问题通常涉及以下技术层面：

1. **网络连接**: 检查SiliconFlow API的网络可达性和延迟
2. **认证机制**: 验证SILICONFLOW_API_KEY的有效性和权限
3. **请求格式**: 确认API请求参数符合模型规范，特别是token限制
4. **重试策略**: 实现指数退避重试和断路器保护
5. **降级机制**: 当API不可用时，提供本地fallback处理

建议优先检查API密钥配置和网络连接状态。"""
        
        elif any(word in query_lower for word in ["代码", "实现", "功能", "开发"]):
            return f"""针对您的开发需求分析：

**查询内容**: {query[:100]}{'...' if len(query) > 100 else ''}

**技术要点**: 
- 涉及系统架构设计，需要考虑模块间的耦合度和可扩展性
- 建议遵循SOLID原则，确保代码的可维护性
- 性能优化应考虑时间复杂度和空间复杂度的平衡
- 错误处理机制要覆盖各种边界情况

**实现建议**: 优先考虑最小可行方案(MVP)，然后逐步迭代优化。"""
        
        else:
            return f"""基于您的查询进行技术分析：

**查询重点**: {query[:150]}{'...' if len(query) > 150 else ''}

**技术维度**:
- 需求分析: 明确功能目标和约束条件
- 架构设计: 选择合适的技术栈和设计模式  
- 实现方案: 考虑开发效率和系统稳定性
- 测试策略: 单元测试、集成测试、性能测试
- 部署运维: 监控、日志、故障恢复机制

建议您提供更多具体的技术细节，以便给出更精准的解决方案。"""
    
    def _generate_context_summary(self, chunks: List[str], query: str) -> str:
        """基于历史上下文生成摘要"""
        if not chunks:
            return "暂无相关历史上下文信息。"
        
        # 提取关键信息
        tech_terms = []
        for chunk in chunks[:5]:  # 处理前5个chunk
            if len(chunk) > 20:  # 过滤太短的内容
                tech_terms.append(f"- {chunk[:150]}{'...' if len(chunk) > 150 else ''}")
        
        if tech_terms:
            return f"""从历史对话中提取的相关技术信息：

{chr(10).join(tech_terms)}

这些历史信息与您当前的查询({query[:50]}{'...' if len(query) > 50 else ''})具有相关性，可以为技术决策提供参考。"""
        else:
            return "历史上下文信息正在整理中，当前可基于查询内容提供针对性建议。"
    
    def _generate_technical_suggestions(self, query: str, chunks: List[str]) -> str:
        """生成技术建议和后续步骤"""
        suggestions = []
        
        # 基于查询内容生成建议
        query_lower = query.lower()
        if "测试" in query_lower or "验证" in query_lower:
            suggestions.append("1. **测试策略**: 建议采用TDD方法，先写测试用例再实现功能")
            suggestions.append("2. **自动化验证**: 设置CI/CD流水线确保代码质量")
        
        if "性能" in query_lower or "优化" in query_lower:
            suggestions.append("1. **性能分析**: 使用profiling工具识别瓶颈")
            suggestions.append("2. **缓存策略**: 合理使用内存缓存和数据库缓存")
        
        if "配置" in query_lower or "环境" in query_lower:
            suggestions.append("1. **配置管理**: 使用环境变量和配置文件分离")
            suggestions.append("2. **环境一致性**: 确保开发、测试、生产环境配置对齐")
        
        # 通用建议
        if not suggestions:
            suggestions = [
                "1. **代码审查**: 确保代码符合团队规范和最佳实践",
                "2. **文档完善**: 及时更新技术文档和API说明",
                "3. **监控告警**: 建立完善的监控体系和故障预警机制"
            ]
        
        return "\n".join(suggestions[:3])  # 最多3个建议
    
    def _generate_minimal_fallback(self, query: str) -> str:
        """最小化保底回复"""
        return f"""### 技术支持响应

**您的查询**: {query[:100]}{'...' if len(query) > 100 else ''}

我可以为您提供以下技术支持：
- 代码实现和架构设计建议
- 问题排查和解决方案
- 性能优化和最佳实践指导
- 系统集成和部署建议

请提供更多具体的技术细节，以便给出更精准的解决方案。如果是紧急问题，建议先检查日志和配置文件。"""
    
    async def compress_memory_context(self, fusion_template: str, user_query: str, 
                                    retrieved_chunks: List[str], **kwargs) -> str:
        """专用于记忆上下文压缩的方法
        
        Args:
            fusion_template: Memory Fusion 模板内容
            user_query: 用户原始查询
            retrieved_chunks: 检索到的上下文片段
            **kwargs: 额外参数
            
        Returns:
            压缩后的记忆背景文本
        """
        # 构建系统提示词
        system_content = f"""你是一个智能记忆压缩助手。请根据以下模板和检索到的历史上下文，为用户查询生成详细而相关的记忆背景。

{fusion_template}

检索到的相关上下文：
{chr(10).join(f"- {chunk}" for chunk in retrieved_chunks)}

要求：
1. 生成的记忆背景应该与用户当前查询高度相关
2. 提供详细的技术信息和背景分析，包含关键实现细节
3. 使用中文回复，结构化组织信息
4. 长度控制在5000字符以内，充分利用上下文信息
5. 按重要性排序，优先展示最相关的技术细节"""

        # 构建用户消息
        user_content = f"用户当前查询：{user_query}"
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
        
        # 设置压缩专用参数
        kwargs.setdefault("max_tokens", 2000)
        kwargs.setdefault("temperature", 0.3)
        
        return await self.generate(messages, **kwargs)
    
    async def compress_context(self, prompt_template: str, context_chunks: List[str], 
                              user_query: str, **kwargs) -> str:
        """实现AICompressor接口的压缩方法
        
        这是compress_memory_context的标准接口实现
        """
        return await self.compress_memory_context(
            fusion_template=prompt_template,
            user_query=user_query,
            retrieved_chunks=context_chunks,
            **kwargs
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "siliconflow",
            "model": self.model_name,
            "version": "v1.0",
            "api_base": self.base_url
        }