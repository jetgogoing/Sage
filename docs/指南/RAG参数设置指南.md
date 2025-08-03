# RAG参数设置指南

## 1. 系统概述和架构说明

Sage智能记忆系统利用RAG（检索增强生成）流程，实现从记忆检索到智能提示生成的全链路服务。系统主要采用以下关键组件：

- **核心模型**：采用 QwenLong-L1-32B 模型，通过 SiliconFlow API 进行模型调用
- **RAG流程**：
  1. **向量搜索**：使用 vectorizer.py 对输入上下文进行向量化并检索相似记忆
  2. **Memory Fusion**：融合检索到的记忆数据，参考 sage_core/config/manager.py 中的配置
  3. **AI压缩**：调用 sage_core/memory/text_generator.py 模块，对长文本进行AI智能压缩
  4. **智能提示生成**：在 sage_core/core_service.py 中，结合压缩后的文本生成最终提示

**三层降级策略**：SiliconFlow API → 本地压缩 → 基础提示

配置优先级遵循 **环境变量 > 代码默认值** 的原则，确保用户可以通过修改 .env 文件覆盖默认配置。

## 2. 详细的参数配置表格

| 参数名称 | 配置位置 | 默认值 | 推荐值 | 说明 |
|---------|---------|-------|-------|------|
| **环境变量参数** |
| SILICONFLOW_API_KEY | 环境变量 (.env) | N/A | 用户申请的实际API Key | SiliconFlow API调用密钥，必须配置 |
| SAGE_MAX_RESULTS | 环境变量 (.env) | 100 | 100~200 | 检索记忆条数，影响RAG质量和性能 |
| SAGE_SIMILARITY_THRESHOLD | 环境变量 (.env) | 0.3 | 0.3~0.5 | 向量搜索相似度阈值 |
| **AI压缩配置** |
| ai_compression.provider | sage_core/config/manager.py:85 | "siliconflow" | "siliconflow" | 压缩服务提供商 |
| ai_compression.model | sage_core/config/manager.py:86 | "Tongyi-Zhiwen/QwenLong-L1-32B" | "Tongyi-Zhiwen/QwenLong-L1-32B" | 使用的核心模型名称 |
| ai_compression.max_tokens | sage_core/config/manager.py:87 | 128000 | 128000 | AI压缩允许的最大token数 |
| ai_compression.temperature | sage_core/config/manager.py:88 | 0.3 | 0.3~0.5 | 生成内容的随机性控制 |
| ai_compression.timeout_seconds | sage_core/config/manager.py:89 | 120 | 120~180 | 压缩请求超时时间 |
| ai_compression.enable | sage_core/config/manager.py:90 | True | True | 是否启用AI压缩功能 |
| ai_compression.fallback_on_error | sage_core/config/manager.py:91 | True | True | 失败时是否启用降级策略 |
| **记忆融合配置** |
| memory_fusion.max_results | sage_core/config/manager.py:94 | 100 | 100~200 | 融合模块最大返回结果数 |
| **核心处理参数** |
| Chunk过滤阈值 | sage_core/core_service.py:204 | >50字符 | >50字符 | 过滤短文本片段，确保内容质量 |
| AI压缩max_tokens | sage_core/core_service.py:181 | 2000 | 2000~5000 | 实际压缩时的token限制 |
| API超时设置 | sage_core/core_service.py:259 | 30秒 | 30~60秒 | API调用超时时间 |
| 质量验证阈值 | sage_core/core_service.py:266 | >20字符 | >20字符 | 生成文本最小质量验证 |

## 3. 性能优化建议

### Token计算与文本长度控制
- **Token换算公式**：QwenLong中文约 1.5~1.8 字符/token
- **容量计算**：128K tokens ≈ 200K字符
- **输入控制**：单次压缩建议控制在3000字符以内（预留冗余）

### 超时与响应优化
- 统一超时设置：配置文件 timeout_seconds(120s) 应与核心服务 API timeout(30s) 保持合理比例
- 网络不稳定时适当提高超时时间
- 启用 fallback_on_error 保证服务连续性

### 内存与并发控制
- SAGE_MAX_RESULTS 影响内存使用，根据系统内存合理调整
- 大并发场景建议引入缓存和异步处理
- 监控API调用频率，避免超出限额

## 4. 故障排查指南

### API调用失败
**症状**：日志显示SiliconFlow API调用错误
```
解决步骤：
1. 检查 SILICONFLOW_API_KEY 是否正确配置
2. 验证网络连接和API服务状态
3. 确认超时设置是否合理
4. 查看是否触发降级策略
```

### 检索结果异常
**症状**：返回记忆条数不符合预期或相关性差
```
解决步骤：
1. 调整 SAGE_SIMILARITY_THRESHOLD (0.3~0.5)
2. 检查 SAGE_MAX_RESULTS 设置
3. 验证向量数据库状态
4. 查看chunk过滤是否过于严格
```

### 文本质量问题
**症状**：生成的文本过短或无意义
```
解决步骤：
1. 检查chunk过滤阈值(>50字符)
2. 调整质量验证标准(>20字符)
3. 验证AI压缩token限制
4. 查看temperature设置是否合适
```

### 配置覆盖问题
**症状**：环境变量修改未生效
```
解决步骤：
1. 确认.env文件加载正确
2. 检查配置优先级
3. 重启服务确保配置生效
4. 验证代码中os.getenv()调用
```

## 5. 配置示例和最佳实践

### 环境变量配置 (.env)
```bash
# SiliconFlow API配置
SILICONFLOW_API_KEY=sk-xtjxdvdwjfiiggwxkojmiryhcfjliywfzurbtsorwvgkimdg

# RAG检索配置
SAGE_MAX_RESULTS=100
SAGE_SIMILARITY_THRESHOLD=0.3

# 性能配置
SAGE_CACHE_SIZE=500
SAGE_CACHE_TTL=300
SAGE_MAX_MEMORY_MB=1024
SAGE_MAX_CONCURRENT_OPS=5
```

### 代码配置示例 (sage_core/config/manager.py)
```python
"ai_compression": {
    "provider": "siliconflow",
    "model": "Tongyi-Zhiwen/QwenLong-L1-32B",
    "max_tokens": 128000,
    "temperature": 0.3,
    "timeout_seconds": 120,
    "enable": True,
    "fallback_on_error": True
},
"memory_fusion": {
    "max_results": int(os.getenv("SAGE_MAX_RESULTS", "100"))
}
```

### 最佳实践建议

1. **配置一致性**
   - 保持环境变量与代码配置的一致性
   - 定期验证配置是否按预期生效

2. **性能监控**
   - 监控API调用成功率和响应时间
   - 跟踪内存使用和并发处理能力
   - 定期检查降级策略触发频率

3. **安全考虑**
   - API密钥使用环境变量存储
   - 定期轮换API密钥
   - 监控API使用量避免超限

## 6. Token计算和容量规划

### Token与字符换算
```
QwenLong-L1-32B 中文处理：
- 1 token ≈ 1.5~1.8 中文字符
- 128K tokens ≈ 200K 中文字符
- 2000 tokens ≈ 3000~3600 中文字符
```

### 容量规划公式
```
单次压缩容量：
- 输入文本：≤ 3000字符 (预留冗余)
- 输出文本：≤ 5000字符 (配置限制)
- 处理时间：30~120秒 (依网络情况)

并发处理能力：
- API限制：依SiliconFlow配额
- 本地处理：依服务器性能
- 内存需求：SAGE_MAX_RESULTS × 平均chunk大小
```

### 容量评估建议
1. **评估输入规模**：统计平均上下文长度和检索数量
2. **测试并发能力**：压测API调用和本地处理性能  
3. **监控资源使用**：跟踪内存、CPU和网络带宽
4. **规划扩容策略**：制定负载增长的应对方案

## 7. 版本兼容性和更新说明

### 当前版本配置
- **系统版本**：V2.03
- **核心模型**：QwenLong-L1-32B
- **API版本**：SiliconFlow v1
- **配置架构**：统一配置管理

### 升级注意事项
1. 新版本可能修改默认参数值
2. API接口变更需同步更新配置
3. 模型升级可能影响token计算
4. 建议测试环境验证后再部署生产

## 结语

本指南基于Sage智能记忆系统的实际架构和关键模块，详细说明了各配置参数的作用、推荐设置以及优化建议。务必结合实际业务需求和负载情况，进行适当的参数调优和容量规划，确保系统在各种场景下提供高性能、稳定的服务。

如有疑问或需要进一步支持，请参考项目文档或联系技术支持团队。