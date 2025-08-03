# Sage用户提示词增强全链路深度分析

**更新时间**：2025-08-03  
**版本**：v2.0（基于实际代码分析）  
**更新说明**：通过深度代码分析纠正了原始文档中的错误信息

## 一、架构概览（修正版）

### ❌ 原始文档中的错误信息（已纠正）

- ~~存在gRPC服务（端口50051）~~ → 实际为直接Python模块调用
- ~~使用FAISS分片集群（16分片）~~ → 实际采用PostgreSQL + pgvector
- ~~本地部署模型~~ → 全部通过SiliconFlow云API
- ~~独立Reranker模块~~ → 使用pgvector内置排序

### ✅ 实际架构

```
用户输入 → UserPromptSubmit Hook → sage_prompt_enhancer.py
    ↓
sage_core.generate_prompt()
    ├─ 文本向量化（Qwen3-Embedding-8B via SiliconFlow API）
    ├─ pgvector相似度搜索（PostgreSQL）
    ├─ AI上下文压缩（QwenLong-L1-32B via SiliconFlow API）
    └─ 返回增强提示词
```

**核心技术栈**：
- **向量化模型**：Qwen/Qwen3-Embedding-8B（4096维）
- **压缩模型**：Tongyi-Zhiwen/QwenLong-L1-32B（128k tokens）
- **存储引擎**：PostgreSQL + pgvector扩展
- **API服务**：SiliconFlow（https://api.siliconflow.cn/v1）

## 二、关键机制说明

### 1. "最近3轮"的真实含义

**重要澄清**：这不是记忆检索的限制！

- **初始上下文**：从transcript提取最近3轮仅作为当前对话的连续性背景
- **真正的检索**：通过向量搜索覆盖**整个历史数据库**
- **无限制搜索**：`session_id=None`确保跨会话、跨时间的完整检索

```python
# sage_core/memory/manager.py:238-239
options = SearchOptions(
    limit=max_results,
    strategy="default",
    session_id=None  # 关键：全库搜索，不限会话
)
```

### 2. 向量检索机制

- **向量生成**：通过SiliconFlow API调用Qwen3-Embedding-8B
- **存储方式**：pgvector扩展存储4096维向量
- **搜索算法**：余弦相似度 `1 - (embedding <=> query_vector)`
- **召回数量**：默认100个（通过`SAGE_MAX_RESULTS`可调）

```sql
-- sage_core/memory/storage.py:201
SELECT id, session_id, user_input, assistant_response, 
       metadata, created_at,
       1 - (embedding <=> $1::vector) as similarity
FROM memories
ORDER BY embedding <=> $1::vector
LIMIT $2
```

### 3. AI压缩流程

```python
# sage_core/core_service.py:204
# 质量过滤：只保留超过50字符的chunk
retrieved_chunks = [chunk.strip() for chunk in relevant_context.split('\n') 
                   if chunk.strip() and len(chunk.strip()) > 50]

# sage_core/memory/text_generator.py:253
compressed = await text_generator.compress_memory_context(
    fusion_template=template,
    user_query=query,
    retrieved_chunks=retrieved_chunks,
    max_tokens=128000,  # 超长文本支持
    temperature=0.3     # 保持稳定性
)
```

### 4. 容错机制

**多层防护设计**：

1. **重试策略**（retry_strategy.py）：
   ```python
   @retry(max_attempts=3, initial_delay=0.5)
   async def api_call():
       # 指数退避：delay = initial_delay × 2^(attempt-1)
       # 随机抖动：delay × (0.5 + random() × 0.5)
   ```

2. **断路器保护**（circuit_breaker.py）：
   ```python
   @circuit_breaker("memory_storage_save", 
                    failure_threshold=5,    # 5次失败触发
                    recovery_timeout=60)    # 60秒后尝试恢复
   ```

3. **降级策略**：
   - SiliconFlow API失败 → 本地关键词提取
   - 向量化失败 → 哈希向量化（降级方案）
   - 整体失败 → 返回基础提示模板

## 三、技术实现细节

### 1. 配置管理（ConfigManager）

```python
# sage_core/config/manager.py:66-101
{
    "embedding": {
        "model": os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
        "dimension": 4096,
        "device": "cpu"  # API调用，无需GPU
    },
    "ai_compression": {
        "model": "Tongyi-Zhiwen/QwenLong-L1-32B",
        "max_tokens": 128000,
        "temperature": 0.3,
        "timeout_seconds": 120,
        "enable": True,
        "fallback_on_error": True
    },
    "memory_fusion": {
        "max_results": int(os.getenv("SAGE_MAX_RESULTS", "100"))
    },
    "memory": {
        "default_limit": 10,
        "max_limit": 100,
        "similarity_threshold": 0.7
    }
}
```

### 2. 数据库架构

```sql
-- pgvector向量存储
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255),
    user_input TEXT,
    assistant_response TEXT,
    embedding vector(4096),  -- 4096维向量
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 向量索引（优化相似度搜索）
CREATE INDEX memories_embedding_idx 
ON memories USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### 3. 完整调用流程

```python
# 1. Hook接收输入
input_data = parse_input()  # session_id, prompt, transcript_path

# 2. 提取初始上下文
recent_context = extract_recent_context(transcript_path)  # 最近3轮

# 3. 调用核心生成函数
enhanced_prompt = await sage_core.generate_prompt(
    context=recent_context + "\n" + prompt,
    style="default"
)

# 4. 内部处理流程
# 4.1 向量化查询
query_embedding = await vectorizer.vectorize(context)

# 4.2 检索相关记忆
memories = await storage.search(
    query_embedding=query_embedding,
    limit=SAGE_MAX_RESULTS,
    session_id=None  # 全库搜索
)

# 4.3 AI压缩
compressed = await text_generator.compress_memory_context(
    retrieved_chunks=memories,
    user_query=context
)

# 4.4 返回增强结果
return compressed
```

## 四、优化建议

### 1. 参数调优

```bash
# 增加召回范围（适合长历史场景）
export SAGE_MAX_RESULTS=200

# 降低相似度阈值（提高召回率）
export SAGE_SIMILARITY_THRESHOLD=0.6

# 设置API密钥
export SILICONFLOW_API_KEY="your-api-key"

# 启用CUDA（如有GPU）
export USE_CUDA=true
```

### 2. 监控与日志

**关键日志路径**：
- 主日志：`/Users/jet/Sage/logs/sage_core.log`
- Hook日志：`/Users/jet/Sage/logs/Hooks/prompt_enhancer.log`
- 压缩失败：`/Users/jet/Sage/logs/Enhancer/compression_errors.log`
- 检索失败：`/Users/jet/Sage/logs/Retriever/search_failures.log`

**监控命令**：
```bash
# 实时监控RAG流程
tail -f /Users/jet/Sage/logs/sage_core.log | grep "RAG流程"

# 分析API调用性能
grep "SiliconFlow API调用" /Users/jet/Sage/logs/*.log | \
  awk -F'耗时: ' '{print $2}' | sort -n

# 检查向量检索效率
grep "步骤1-向量搜索完成" /Users/jet/Sage/logs/sage_core.log | \
  tail -20
```

### 3. 个人用户维护建议

1. **定期备份**：
   ```bash
   # 备份向量数据库
   pg_dump -U sage -d sage_memory -t memories > \
     backup_$(date +%Y%m%d).sql
   
   # 备份配置
   cp /Users/jet/Sage/config.json \
     /Users/jet/Sage/backups/config_$(date +%Y%m%d).json
   ```

2. **性能优化**：
   ```bash
   # 重建向量索引（当性能下降时）
   psql -U sage -d sage_memory -c \
     "REINDEX INDEX memories_embedding_idx;"
   
   # 清理过期数据（保留最近6个月）
   psql -U sage -d sage_memory -c \
     "DELETE FROM memories WHERE created_at < NOW() - INTERVAL '6 months';"
   ```

3. **故障排查**：
   ```bash
   # 检查API连接
   curl -H "Authorization: Bearer $SILICONFLOW_API_KEY" \
        https://api.siliconflow.cn/v1/models
   
   # 验证向量生成
   python3 -c "
   from sage_core.memory.vectorizer import TextVectorizer
   v = TextVectorizer()
   print(v.get_dimension())  # 应输出4096
   "
   
   # 测试数据库连接
   psql -U sage -d sage_memory -c \
     "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM memories;"
   ```

## 五、系统优势与局限

### 优势
1. **简单可靠**：无需企业级复杂度，适合个人使用
2. **完整记忆**：真正实现跨会话、跨时间的记忆检索
3. **高质量召回**：4096维向量提供精准语义匹配
4. **容错健壮**：多层降级确保服务可用性
5. **易于维护**：云API降低运维成本，配置灵活

### 局限
1. **网络依赖**：API调用增加延迟（200-500ms）
2. **成本考虑**：大量API调用可能产生费用
3. **扩展受限**：单机PostgreSQL有性能上限
4. **无Reranker**：召回精度可能不如专门的重排序模型

## 六、常见问题解答

**Q：为什么只提取最近3轮对话？**  
A：这只是初始上下文，提供对话连续性。真正的记忆检索通过向量搜索覆盖整个数据库，不受时间和会话限制。

**Q：如何提高召回质量？**  
A：
- 增加`SAGE_MAX_RESULTS`值（如200-500）
- 降低`similarity_threshold`（如0.5-0.6）
- 在prompt中明确引用历史项目名称或关键词
- 考虑实现轻量级Reranker

**Q：系统会"失忆"吗？**  
A：不会。所有对话永久保存在PostgreSQL中，向量检索无时间限制。即使跨越数月的对话也能被准确召回。

**Q：如何处理API失败？**  
A：系统有完善的降级机制：
- 向量化失败→哈希向量化
- 压缩失败→本地关键词提取
- 完全失败→返回基础提示

## 七、未来改进方向

1. **本地模型部署**：部署小型本地模型减少API依赖
2. **增加Reranker**：使用CrossEncoder或ColBERT提升排序精度
3. **向量数据库升级**：考虑Milvus或Weaviate获得更好的扩展性
4. **缓存层**：Redis缓存高频查询结果
5. **批处理优化**：聚合多个请求减少API调用次数

---

**文档维护者**：Claude Code Assistant  
**技术验证**：DeepSeek-R1 + OpenAI o3-mini-high + ChatGPT-4o  
**最后更新**：2025-08-03

> 注：本文档基于实际代码分析生成，修正了原始设计文档中的多处错误。如有疑问，请以代码实现为准。