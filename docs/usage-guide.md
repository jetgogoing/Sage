# Sage MCP 用户指南

## 简介

Sage MCP 是一个智能记忆系统，它能够帮助您：
- 📚 自动保存和管理对话历史
- 🔍 智能搜索和回忆相关内容
- 💡 提供上下文感知的智能提示
- 📊 分析对话模式和知识结构
- 🛡️ 提供强大的错误处理和性能优化

## 快速开始

### 1. 安装 Claude Code

确保您已经安装了 Claude Code，这是使用 Sage MCP 的前提。

### 2. 启动 Sage MCP 服务

```bash
# 使用标准 stdio 模式启动
./start_sage_mcp_stdio.sh

# 或者直接运行
python sage_mcp_v4_final.py
```

### 3. 在 Claude Code 中启用 Sage

在 Claude Code 中，Sage MCP 会自动连接并提供智能记忆功能。

## 核心功能

### 1. 对话管理

#### 保存对话
```
/save [标题]
```
保存当前对话到记忆系统。如果不提供标题，系统会自动生成。

**示例：**
- `/save` - 自动保存当前对话
- `/save Python学习笔记` - 保存并命名为"Python学习笔记"

#### 搜索历史
```
/search <查询词>
```
搜索历史对话中的相关内容。

**示例：**
- `/search Python` - 搜索所有包含"Python"的对话
- `/search 机器学习 算法` - 搜索包含这些关键词的对话

#### 回忆对话
```
/recall [数量|会话ID]
```
回忆最近的对话或特定会话。

**示例：**
- `/recall` - 显示最近10条对话
- `/recall 5` - 显示最近5条对话
- `/recall session_20250714_120000` - 显示特定会话

#### 忘记对话
```
/forget [all|会话ID]
```
删除对话记忆。

**示例：**
- `/forget` - 忘记当前会话
- `/forget all` - 清空所有记忆（谨慎使用！）
- `/forget session_20250714_120000` - 忘记特定会话

### 2. 智能模式

#### 开启/关闭 Sage 模式
```
/mode [on|off]
```
切换 Sage 智能模式的开关状态。

#### 查看系统状态
```
/status
```
显示记忆系统的当前状态，包括：
- 总会话数
- 总消息数
- 存储空间使用
- 系统健康状态

#### 详细系统状态（V4新功能）
```
/SAGE-STATUS
```
显示更详细的系统状态，包括：
- 错误统计
- 性能指标
- 优化建议
- 资源使用情况

### 3. 记忆分析

```
/analyze [类型] [天数]
```
分析您的对话记忆，提供有价值的洞察。

**分析类型：**
- `topics` - 主题分析
- `trends` - 趋势分析
- `patterns` - 模式识别
- `summary` - 综合摘要

**示例：**
- `/analyze` - 执行默认分析
- `/analyze topics 30` - 分析最近30天的主题
- `/analyze trends 7` - 分析最近7天的趋势

### 4. 智能提示（V4新功能）

Sage 会根据您的输入自动提供智能提示：

- **上下文感知**：识别您当前的工作场景（编程、学习、调试等）
- **意图理解**：分析您的问题类型和需求
- **个性化建议**：基于您的历史对话提供定制化帮助
- **学习路径**：为学习者提供系统化的学习建议

### 5. 自动功能

#### 自动保存
系统会智能判断对话的完整性，在适当的时候自动保存重要对话。

#### 上下文注入
在新对话开始时，系统会自动注入相关的历史上下文，让对话更连贯。

#### 智能缓存
频繁访问的内容会被智能缓存，提高响应速度。

## 高级功能

### 会话导出

您可以将会话导出为不同格式：
- JSON格式（完整数据）
- Markdown格式（易读文档）
- 纯文本格式（简单备份）

### 会话分析

获取单个会话的详细分析：
- 消息统计
- 平均长度
- 话题分布
- 时间分布

### 错误恢复

系统具备智能错误恢复能力：
- 自动重试失败的操作
- 智能降级策略
- 熔断器保护
- 详细的错误日志

### 性能优化

系统会自动进行性能优化：
- 内存使用优化
- 查询性能优化
- 缓存策略调整
- 资源管理

## 使用场景

### 1. 学习助手

```
用户：我想学习Python编程
Sage：[检测到学习场景，提供个性化学习路径]

用户：/save Python学习第一天
Sage：✅ 已保存您的学习进度

用户：/recall
Sage：[显示您的学习历史，帮助复习]
```

### 2. 编程伙伴

```
用户：如何实现一个装饰器？
Sage：[基于您之前的Python学习历史，提供针对性讲解]

用户：/search 装饰器
Sage：[找到所有相关的历史讨论]
```

### 3. 调试助手

```
用户：TypeError: 'NoneType' object is not subscriptable
Sage：[检测到调试场景，提供调试建议和相关历史经验]

用户：/analyze patterns
Sage：[分析您常见的错误模式，提供预防建议]
```

### 4. 知识管理

```
用户：/analyze topics 30
Sage：[分析最近30天的学习主题，展示知识图谱]

用户：/status
Sage：[显示您的知识库统计信息]
```

## 配置选项

### 环境变量

```bash
# 调整检索数量（默认：5）
export SAGE_MAX_RESULTS=10

# 启用调试日志
export SAGE_DEBUG=true

# 设置数据目录
export SAGE_DATA_DIR=~/.sage

# 设置最大内存限制（MB）
export SAGE_MAX_MEMORY_MB=2048

# 设置最大并发操作数
export SAGE_MAX_CONCURRENT_OPS=10
```

### 配置文件

创建 `~/.sage/config.json`:

```json
{
  "retrieval": {
    "strategy": "HYBRID_ADVANCED",
    "max_results": 5,
    "similarity_threshold": 0.5,
    "enable_rerank": true,
    "enable_summary": true
  },
  "embedding": {
    "model": "default",
    "dimension": 768,
    "batch_size": 100
  },
  "cache": {
    "enabled": true,
    "ttl_seconds": 300,
    "max_size": 1000
  },
  "auto_save": {
    "enabled": true,
    "min_messages": 4,
    "idle_timeout": 300
  },
  "performance": {
    "enable_monitoring": true,
    "alert_thresholds": {
      "cpu_usage": 70,
      "memory_usage": 80,
      "response_time": 2.0
    }
  }
}
```

## 最佳实践

### 1. 定期保存重要对话
虽然系统有自动保存功能，但对于特别重要的对话，建议手动保存并添加描述性标题。

### 2. 使用描述性标题
保存时使用清晰的标题，方便日后搜索和回忆。

### 3. 善用搜索功能
搜索支持多个关键词，可以更精确地找到需要的内容。

### 4. 定期分析
定期使用分析功能，了解自己的学习和工作模式。

### 5. 合理管理存储
定期清理不需要的对话，保持系统运行效率。

## 隐私和安全

- 所有对话数据都存储在本地
- 支持加密存储（需配置）
- 可以随时删除任何对话
- 不会将数据发送到外部服务器（除了必要的嵌入向量化）

## 故障排除

### 连接问题
如果 Claude Code 无法连接到 Sage：
1. 确保 Sage MCP 服务正在运行
2. 检查是否使用了正确的启动脚本
3. 查看日志文件：`/tmp/sage_mcp_v4_final.log`

### 性能问题
如果系统响应缓慢：
1. 使用 `/SAGE-STATUS` 查看性能指标
2. 检查是否有过多的历史数据
3. 考虑清理旧的对话记录

### 错误处理
如果遇到错误：
1. 系统会自动尝试恢复
2. 查看错误统计：`/SAGE-STATUS`
3. 检查日志文件获取详细信息

## 命令快速参考

| 命令 | 描述 | 示例 |
|------|------|------|
| `/save [标题]` | 保存当前对话 | `/save 重要讨论` |
| `/search <查询>` | 搜索历史对话 | `/search Python` |
| `/recall [数量\|ID]` | 回忆历史对话 | `/recall 5` |
| `/forget [all\|ID]` | 删除对话记忆 | `/forget all` |
| `/status` | 查看系统状态 | `/status` |
| `/mode [on\|off]` | 切换智能模式 | `/mode on` |
| `/analyze [类型] [天数]` | 分析记忆数据 | `/analyze topics 30` |
| `/help [命令]` | 显示帮助信息 | `/help save` |
| `/SAGE-STATUS` | 详细系统状态 | `/SAGE-STATUS` |

## 更新日志

### V4.0.0 (当前版本)
- ✨ 新增智能提示系统
- 🛡️ 新增全面的错误处理机制
- 📊 新增性能监控和优化
- 🎯 新增多种工作模式
- 🔧 改进系统稳定性

### V3.0.0
- 📈 新增高级会话管理
- 🧠 新增记忆分析功能
- 📤 新增会话导出功能

### V2.0.0
- 🤖 新增自动保存机制
- 💉 新增智能上下文注入
- 🚀 性能优化

### V1.0.0
- 🎉 初始版本发布
- 📝 基础命令系统
- 💾 会话管理功能

## 获取帮助

- 使用 `/help` 查看命令帮助
- 使用 `/help <命令>` 查看特定命令的详细说明
- 查看项目文档：`docs/` 目录
- 查看[API文档](api-reference.md)了解技术细节
- 查看[部署指南](deployment-guide.md)了解安装配置

## 反馈和贡献

欢迎您的反馈和贡献！
- 报告问题：通过项目仓库的 Issues
- 功能建议：通过 Discussions
- 代码贡献：查看 CONTRIBUTING.md