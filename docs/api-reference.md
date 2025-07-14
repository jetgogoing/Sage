# Sage MCP Server API 参考文档

## 概述

Sage MCP Server 是一个基于 Model Context Protocol (MCP) 的智能记忆系统，提供了对话管理、智能提示、记忆分析等功能。本文档覆盖了 V4 版本的所有功能。

## MCP工具

Sage MCP实现了以下MCP工具，可通过Claude Code自动调用：

### sage_memory

存储和管理对话记忆的核心工具。

**参数:**
- `action` (string, required): 操作类型
  - `save`: 保存当前对话
  - `search`: 搜索历史对话
  - `forget`: 忘记对话记忆
  - `recall`: 回忆历史对话
  - `status`: 显示系统状态
  - `analyze`: 分析记忆数据
  - `export`: 导出会话数据
- `query` (string, optional): 搜索查询或会话ID
- `title` (string, optional): 会话标题
- `limit` (number, optional): 结果数量限制

**示例:**
```json
{
  "name": "sage_memory",
  "arguments": {
    "action": "save",
    "title": "Python编程讨论"
  }
}
```

### save_conversation

保存对话到记忆系统。

**参数:**
- `user_prompt` (string, required): 用户的提问
- `assistant_response` (string, required): 助手的回复
- `metadata` (object, optional): 额外元数据

**示例:**
```json
{
  "name": "save_conversation",
  "arguments": {
    "user_prompt": "如何使用Python装饰器？",
    "assistant_response": "装饰器是Python中的一个强大特性...",
    "metadata": {
      "topic": "Python",
      "importance": "high"
    }
  }
}
```

### get_context

获取与查询相关的历史上下文。

**参数:**
- `query` (string, required): 查询文本
- `max_results` (integer, optional): 最大结果数，默认5
- `strategy` (string, optional): 检索策略
  - `HYBRID_ADVANCED` (默认)
  - `AGGRESSIVE`
  - `CONSERVATIVE`

**返回:**
```json
{
  "context": "相关上下文摘要...",
  "results": [
    {
      "content": "历史对话内容",
      "score": 0.89,
      "metadata": {...}
    }
  ],
  "strategy_used": "HYBRID_ADVANCED",
  "num_results": 5
}
```

### search_memory

搜索记忆库中的特定内容。

**参数:**
- `query` (string, required): 搜索查询
- `n` (integer, optional): 返回结果数，默认5
- `threshold` (float, optional): 相似度阈值，默认0.5

**返回:**
```json
[
  {
    "content": "匹配的对话内容",
    "role": "user",
    "score": 0.92,
    "metadata": {
      "session_id": "uuid",
      "turn_id": 1,
      "timestamp": "2025-07-14T10:00:00Z"
    }
  }
]
```

### get_memory_stats

获取记忆系统统计信息。

**参数:** 无

**返回:**
```json
{
  "total": 1234,
  "today": 56,
  "this_week": 342,
  "size": "45.2 MB",
  "size_mb": 45.2,
  "sessions": 89,
  "avg_turns_per_session": 13.8
}
```

### clear_session

清除当前会话的记忆。

**参数:**
- `session_id` (string, optional): 指定会话ID，默认当前会话

**返回:**
```json
{
  "cleared": true,
  "count": 24,
  "session_id": "uuid"
}
```

### sage_command

执行 Sage 命令的工具。

**参数:**
- `command` (string, required): 要执行的命令

**支持的命令:**
- `/save [标题]`: 保存当前对话
- `/search <查询>`: 搜索历史对话
- `/forget [all|session_id]`: 忘记对话记忆
- `/recall [数量|session_id]`: 回忆历史对话
- `/status`: 显示记忆系统状态
- `/mode [on|off]`: 切换 Sage 模式
- `/help [命令]`: 显示帮助信息
- `/analyze [类型] [天数]`: 分析记忆数据
- `/SAGE-STATUS`: 显示系统详细状态（V4新增）

### sage_auto

自动记忆管理操作工具。

**参数:**
- `action` (string, required): 操作类型
  - `inject_context`: 注入相关历史上下文
  - `check_save`: 检查是否需要自动保存
- `user_input` (string, optional): 用户输入内容
- `limit` (number, optional): 上下文数量限制

### sage_smart_prompt

智能提示系统工具（V4新增）。

**参数:**
- `user_input` (string, required): 用户输入内容
- `include_suggestions` (boolean, optional): 是否包含建议，默认true

**返回结构:**
```json
{
  "context": "coding",
  "intent": {
    "primary": "seeking_solution",
    "confidence": 0.85,
    "keywords": ["Python", "装饰器"],
    "question_type": "how_to"
  },
  "prompts": [
    {
      "type": "contextual",
      "text": "我来为您详细解释Python装饰器的工作原理",
      "priority": 0.9
    }
  ],
  "suggestions": ["查看相关的最佳实践", "了解常见的陷阱"],
  "related_topics": ["闭包", "高阶函数"],
  "learning_path": [
    {
      "step": 1,
      "topic": "函数基础",
      "duration": "1周"
    }
  ]
}
```

### sage_system_status

系统状态监控工具（V4新增）。

**参数:**
- `include_errors` (boolean, optional): 包含错误统计，默认true
- `include_performance` (boolean, optional): 包含性能指标，默认true
- `include_optimization` (boolean, optional): 包含优化建议，默认true

## HTTP API

除了MCP协议，系统还提供HTTP API用于管理和监控。

### 健康检查

```bash
GET /health
```

**响应:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-14T16:45:00.123456",
  "memory_count": 1234,
  "database": "connected",
  "cache_status": "active",
  "version": "1.0.0"
}
```

### MCP端点

```bash
POST /mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "search_memory",
    "arguments": {
      "query": "Docker"
    }
  }
}
```

## 提示模板 (Prompts)

### sage_memory_expert
启用 Sage 记忆专家模式，提供专业的记忆管理功能。

### sage_analysis_mode
启用 Sage 分析模式，提供深度记忆分析和洞察。

### sage_intelligent_mode
启用 Sage 智能助手模式（V4完整版），集成所有高级功能。

### sage_learning_mode
启用 Sage 学习辅导模式，提供个性化学习指导。

### sage_debug_mode
启用 Sage 调试助手模式，帮助解决技术问题。

## Python客户端

### 安装

```bash
pip install sage-mcp-client
```

### 使用示例

```python
from sage_mcp import SageClient

# 初始化客户端
client = SageClient(
    host="localhost",
    port=17800,
    api_key="optional-api-key"
)

# 保存对话
client.save_conversation(
    user="什么是容器化？",
    assistant="容器化是一种轻量级虚拟化技术..."
)

# 搜索记忆
results = client.search("Docker", limit=10)
for result in results:
    print(f"相似度: {result.score:.2f}")
    print(f"内容: {result.content[:100]}...")

# 获取统计
stats = client.get_stats()
print(f"总记忆数: {stats['total']}")

# 获取上下文
context = client.get_context(
    "如何优化Docker镜像？",
    strategy="AGGRESSIVE"
)
print(f"相关上下文: {context['context']}")
```

## 核心组件 API

### SageCommandParser

命令解析器，负责解析用户输入的命令。

```python
class SageCommandParser:
    def parse_command(self, text: str) -> Dict[str, Any]:
        """解析命令文本
        
        Args:
            text: 命令文本
            
        Returns:
            {
                "type": CommandType,
                "params": Dict[str, Any]
            }
        """
```

### EnhancedSessionManager

增强的会话管理器，提供会话的创建、保存、搜索等功能。

```python
class EnhancedSessionManager:
    def start_session(self, title: str = None) -> str:
        """开始新会话"""
        
    def add_message(self, role: str, content: str):
        """添加消息到当前会话"""
        
    def save_session(self) -> str:
        """保存当前会话"""
        
    def load_session(self, session_id: str) -> Dict[str, Any]:
        """加载指定会话"""
        
    def search_sessions(self, 
                       search_type: SessionSearchType, 
                       query: str) -> List[Dict]:
        """搜索会话
        
        搜索类型:
        - KEYWORD: 关键词搜索
        - DATE_RANGE: 日期范围搜索
        - TOPIC: 主题搜索
        - RECENT: 最近会话
        - SIMILARITY: 相似度搜索
        """
        
    def export_session(self, session_id: str, format: str) -> Dict:
        """导出会话
        
        支持格式: json, markdown, text
        """
```

### SmartPromptGenerator

智能提示生成器（V4新增）。

```python
class SmartPromptGenerator:
    async def generate_smart_prompt(
        self,
        user_input: str,
        conversation_history: List[Dict] = None,
        current_context: Dict = None
    ) -> Dict[str, Any]:
        """生成智能提示
        
        Returns:
            {
                "context": PromptContext,
                "intent": Dict,
                "prompts": List[Dict],
                "suggestions": List[str],
                "related_topics": List[str],
                "learning_path": List[Dict]
            }
        """
```

### MemoryAnalyzer

记忆分析器，提供多维度的记忆分析。

```python
class MemoryAnalyzer:
    async def analyze(
        self,
        analysis_type: AnalysisType,
        params: Dict = None
    ) -> Dict[str, Any]:
        """执行记忆分析
        
        分析类型:
        - TOPIC_CLUSTERING: 主题聚类
        - TEMPORAL_PATTERNS: 时间模式
        - INTERACTION_FLOW: 交互流程
        - KNOWLEDGE_GRAPH: 知识图谱
        - SENTIMENT_ANALYSIS: 情感分析
        """
```

### ErrorHandler

统一错误处理器（V4新增）。

```python
class ErrorHandler:
    def handle_error(
        self,
        error: Exception,
        context: Dict = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> Dict[str, Any]:
        """处理错误
        
        错误严重程度:
        - CRITICAL: 严重错误
        - HIGH: 高优先级
        - MEDIUM: 中等优先级
        - LOW: 低优先级
        - INFO: 信息级别
        """
```

## 装饰器

### @with_error_handling

错误处理装饰器。

```python
@with_error_handling(ErrorSeverity.HIGH)
async def risky_operation():
    # 自动处理错误
    pass
```

### @with_performance_monitoring

性能监控装饰器。

```python
@with_performance_monitoring("operation_name")
async def slow_operation():
    # 自动记录性能指标
    pass
```

### @with_circuit_breaker

熔断器装饰器。

```python
@with_circuit_breaker(failure_threshold=5, recovery_timeout=60)
async def unreliable_operation():
    # 自动熔断保护
    pass
```

## 数据库模式

### conversations 表

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    turn_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(4096),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_conversations_created ON conversations(created_at);
CREATE INDEX idx_conversations_embedding ON conversations 
  USING ivfflat (embedding vector_cosine_ops);
```

### 向量搜索查询

```sql
-- 余弦相似度搜索
SELECT 
    id,
    content,
    1 - (embedding <=> %s::vector) as similarity
FROM conversations
WHERE embedding IS NOT NULL
ORDER BY embedding <=> %s::vector
LIMIT %s;
```

## 配置参考

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| SILICONFLOW_API_KEY | SiliconFlow API密钥 | 必需 |
| DATABASE_URL | PostgreSQL连接字符串 | postgresql://mem:mem@localhost:5432/mem |
| DB_HOST | 数据库主机 | localhost |
| DB_PORT | 数据库端口 | 5432 |
| DB_NAME | 数据库名称 | mem |
| DB_USER | 数据库用户 | mem |
| DB_PASSWORD | 数据库密码 | mem |
| SAGE_MAX_RESULTS | 默认检索数量 | 5 |
| SAGE_CACHE_TTL | 缓存过期时间(秒) | 300 |
| SAGE_DEBUG | 启用调试日志 | false |

### 配置文件

`~/.sage/config.json`:

```json
{
  "retrieval": {
    "strategy": "HYBRID_ADVANCED",
    "max_results": 5,
    "similarity_threshold": 0.5,
    "enable_rerank": true,
    "enable_neural_rerank": true,
    "enable_llm_summary": true,
    "rerank_top_k": 20,
    "summary_max_tokens": 500
  },
  "embedding": {
    "model": "Qwen/Qwen3-Embedding-8B",
    "dimension": 4096,
    "batch_size": 100,
    "timeout": 30
  },
  "cache": {
    "enabled": true,
    "ttl_seconds": 300,
    "max_size": 1000,
    "eviction_policy": "lru"
  },
  "storage": {
    "compression": "gzip",
    "encryption": "aes-256-gcm",
    "backup_interval": "daily",
    "retention_days": 365
  }
}
```

## 错误代码

| 代码 | 描述 | 处理建议 |
|------|------|----------|
| -32600 | 无效请求 | 检查JSON格式 |
| -32601 | 方法不存在 | 检查方法名称 |
| -32602 | 无效参数 | 检查参数类型和必需字段 |
| -32603 | 内部错误 | 查看服务器日志 |
| -32700 | 解析错误 | 检查JSON语法 |
| 1001 | 数据库连接失败 | 检查数据库服务 |
| 1002 | 向量化失败 | 检查API密钥 |
| 1003 | 缓存错误 | 清理缓存 |

## 性能优化

### 数据库优化

```sql
-- 更新统计信息
ANALYZE conversations;

-- 重建索引
REINDEX INDEX idx_conversations_embedding;

-- 清理死元组
VACUUM ANALYZE conversations;
```

### 批量操作

```python
# 批量保存
conversations = [
    {"user": "...", "assistant": "..."},
    # ...
]
client.batch_save(conversations)

# 批量搜索
queries = ["Docker", "Kubernetes", "微服务"]
results = client.batch_search(queries)
```

### 连接池配置

```python
from sage_mcp import SageClient

client = SageClient(
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600
)
```

## 扩展开发

### 自定义嵌入模型

```python
from sage_mcp.embedding import BaseEmbedding

class MyEmbedding(BaseEmbedding):
    def embed(self, text: str) -> List[float]:
        # 实现自定义嵌入逻辑
        return vector
    
    @property
    def dimension(self) -> int:
        return 1536  # 你的向量维度
```

### 自定义检索策略

```python
from sage_mcp.retrieval import BaseStrategy

class MyStrategy(BaseStrategy):
    name = "MY_CUSTOM"
    
    def retrieve(self, query: str, limit: int) -> List[Dict]:
        # 实现自定义检索逻辑
        return results
```

### 插件系统

创建 `~/.sage/plugins/my_plugin.py`:

```python
from sage_mcp import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    version = "1.0.0"
    
    def on_save(self, conversation):
        # 保存前的钩子
        pass
    
    def on_retrieve(self, query, results):
        # 检索后的钩子
        return results
```

## 监控和日志

### Prometheus指标

```
# 记忆总数
sage_memory_total{type="conversation"} 1234

# API请求数
sage_api_requests_total{method="save_conversation"} 5678

# 响应时间
sage_response_time_seconds{quantile="0.99"} 0.15

# 缓存命中率
sage_cache_hit_ratio 0.82
```

### 日志格式

```json
{
  "timestamp": "2025-07-14T16:45:00.123Z",
  "level": "INFO",
  "service": "sage-mcp",
  "trace_id": "abc123",
  "message": "Conversation saved",
  "user_id": "anonymous",
  "session_id": "def456",
  "duration_ms": 45
}
```

## 数据结构

### Session
```python
{
    "session_id": str,
    "title": str,
    "created_at": str,  # ISO format
    "updated_at": str,  # ISO format
    "messages": List[Message],
    "tags": List[str],
    "metadata": Dict[str, Any]
}
```

### Message
```python
{
    "role": str,  # "user" | "assistant"
    "content": str,
    "timestamp": str,  # ISO format
    "metadata": Dict[str, Any]
}
```

### AnalysisResult
```python
{
    "analysis_type": str,
    "timestamp": str,
    "results": Dict[str, Any],
    "insights": List[str],
    "recommendations": List[str]
}
```

## 实验性功能

```python
experimental_capabilities = {
    "auto_context_injection": True,     # 自动上下文注入
    "auto_save": True,                  # 自动保存对话
    "conversation_tracking": True,       # 对话跟踪
    "advanced_session_management": True, # 高级会话管理
    "memory_analysis": True,            # 记忆分析
    "smart_prompts": True,              # 智能提示（V4）
    "error_handling": True,             # 错误处理（V4）
    "performance_optimization": True     # 性能优化（V4）
}
```

## 版本兼容性

| Sage版本 | MCP协议 | Python | PostgreSQL | pgvector |
|----------|---------|---------|------------|----------|
| 1.0.x | 1.0 | 3.11+ | 15+ | 0.5+ |
| 2.0.x | 1.0 | 3.11+ | 15+ | 0.5+ |
| 3.0.x | 1.0 | 3.11+ | 15+ | 0.5+ |
| 4.0.x | 1.0 | 3.11+ | 15+ | 0.5+ |

## 更多资源

- [MCP协议规范](https://modelcontextprotocol.io/docs)
- [pgvector文档](https://github.com/pgvector/pgvector)
- [SiliconFlow API](https://siliconflow.cn/docs)