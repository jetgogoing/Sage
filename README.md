# Sage智能记忆管理系统

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-green.svg)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Required-blue.svg)](https://docker.com)
[![MCP](https://img.shields.io/badge/MCP-Protocol-orange.svg)](https://modelcontextprotocol.io)

Sage是一个智能记忆管理系统，通过MCP（Model Context Protocol）协议与Claude桌面应用集成，为AI对话提供长期记忆和上下文增强能力。系统采用先进的向量检索和AI压缩技术，实现跨会话、跨时间的智能记忆召回。

## 🚀 核心功能

### 1. 智能提示词增强系统
- **全链路记忆增强**：基于向量检索的智能上下文注入
- **跨会话记忆**：突破单次对话限制，实现历史记忆的无限召回
- **AI智能压缩**：通过QwenLong-L1-32B模型进行上下文压缩和重组

### 2. 断路器保护机制
- **自动熔断**：在系统故障时自动保护，防止级联故障
- **手动重置**：支持故障修复后的快速恢复
```bash
# 重置所有断路器
@sage reset_circuit_breaker all=true

# 重置指定服务
@sage reset_circuit_breaker breaker_name="database_connection"
```

### 3. MCP服务集成
- **标准协议**：完全符合MCP协议规范
- **多工具支持**：内置记忆管理、会话控制、状态监控等工具
- **Claude集成**：与Claude桌面应用无缝集成

### 4. 向量检索引擎
- **4096维向量**：使用Qwen3-Embedding-8B模型生成高质量向量
- **pgvector存储**：基于PostgreSQL的高效向量检索
- **余弦相似度**：精准的语义匹配算法

## 📋 系统架构

```
用户输入 → UserPromptSubmit Hook → sage_prompt_enhancer.py
    ↓
sage_core.generate_prompt()
    ├─ 文本向量化（Qwen3-Embedding-8B via SiliconFlow API）
    ├─ pgvector相似度搜索（PostgreSQL）
    ├─ AI上下文压缩（QwenLong-L1-32B via SiliconFlow API）
    └─ 返回增强提示词
```

**技术栈**：
- **向量化模型**：Qwen/Qwen3-Embedding-8B（4096维）
- **压缩模型**：Tongyi-Zhiwen/QwenLong-L1-32B（128k tokens）
- **存储引擎**：PostgreSQL + pgvector扩展
- **API服务**：SiliconFlow（https://api.siliconflow.cn/v1）
- **容错机制**：断路器 + 重试策略 + 降级处理

## 🛠️ 快速开始

### 环境要求
- **Python**: 3.9+
- **Docker Desktop**: 用于数据库容器
- **Claude 桌面应用**: MCP客户端

### 安装部署

1. **克隆项目**
```bash
git clone <repository-url>
cd Sage
```

2. **创建虚拟环境**
```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
# 创建 .env 文件
cat > .env << EOF
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sage_memory
DB_USER=sage
DB_PASSWORD=sage123

# API 密钥
SILICONFLOW_API_KEY=your-api-key-here

# Sage 配置
SAGE_MAX_RESULTS=100
SAGE_SIMILARITY_THRESHOLD=0.7
EOF
```

5. **启动服务**
```bash
bash start_sage_mcp.sh
```

6. **配置Claude应用**

编辑Claude配置文件（`~/Library/Application Support/Claude/claude_desktop_config.json`）：
```json
{
  "mcpServers": {
    "sage": {
      "command": "/bin/bash",
      "args": ["/path/to/your/Sage/start_sage_mcp.sh"],
      "startupTimeout": 30000
    }
  }
}
```

## 🎯 主要功能

### 记忆管理
```bash
# 保存对话
@sage S user_prompt="用户输入" assistant_response="助手回复"

# 获取相关上下文
@sage get_context query="查询内容" max_results=10

# 会话管理
@sage manage_session action="list"
```

### 系统监控
```bash
# 检查系统状态
@sage get_status

# 断路器状态查看
tail -f logs/circuit_breaker_reset.log
```

### 故障恢复
```bash
# 数据库修复后
@sage reset_circuit_breaker all=true

# API密钥更新后
@sage reset_circuit_breaker breaker_name="vectorizer"
```

## 📁 项目结构

```
Sage/
├── docs/                    # 完整文档系统
│   ├── 项目架构说明/        # 核心架构设计
│   ├── 指南/               # 部署运维指南
│   ├── 执行报告/            # 功能开发报告
│   └── 问题汇总/            # 问题分析报告
├── sage_core/              # 核心业务逻辑
│   ├── memory/             # 记忆管理模块
│   ├── resilience/         # 容错保护机制
│   ├── database/           # 数据库连接层
│   └── config/             # 配置管理
├── hooks/                  # Hook脚本集成
├── scripts/                # 工具脚本
├── tests/                  # 完整测试套件
└── logs/                   # 日志系统
```

## 🔧 高级配置

### 性能调优
```bash
# 增加召回范围
export SAGE_MAX_RESULTS=200

# 降低相似度阈值
export SAGE_SIMILARITY_THRESHOLD=0.6

# 启用详细日志
export SAGE_LOG_LEVEL=DEBUG
```

### 监控与维护
```bash
# 实时监控RAG流程
tail -f logs/sage_core.log | grep "RAG流程"

# 数据库性能检查
psql -U sage -d sage_memory -c "SELECT COUNT(*) FROM memories;"

# 向量索引重建
psql -U sage -d sage_memory -c "REINDEX INDEX memories_embedding_idx;"
```

## 🛟 故障排查

### 常见问题

1. **MCP连接失败**
   - 检查 Claude 配置文件路径
   - 确认 `start_sage_mcp.sh` 有执行权限
   - 查看服务器日志：`tail -f logs/sage_mcp_stdio.log`

2. **数据库连接错误**
   - 确保 Docker Desktop 运行中
   - 检查数据库容器：`docker ps | grep sage-db`
   - 重启数据库：`docker restart sage-db`

3. **API调用失败**
   - 验证 API 密钥：`curl -H "Authorization: Bearer $SILICONFLOW_API_KEY" https://api.siliconflow.cn/v1/models`
   - 检查网络连接和配额

4. **断路器阻塞**
   - 查看断路器状态日志
   - 确认底层问题已修复
   - 执行手动重置：`@sage reset_circuit_breaker all=true`

### 日志分析
- **主日志**：`logs/sage_mcp_stdio.log`
- **Hook日志**：`logs/Hooks/prompt_enhancer.log`
- **断路器日志**：`logs/circuit_breaker_reset.log`

## 🌟 核心优势

- **🧠 真正的长期记忆**：跨会话、跨时间的完整记忆召回
- **🔒 可靠的容错机制**：多层保护确保服务稳定性
- **⚡ 高效的向量检索**：4096维向量提供精准语义匹配
- **🔧 简单的运维管理**：完整的监控、日志、恢复机制
- **🚀 云端AI能力**：集成先进的语言模型和向量模型

## 📚 文档导航

- [**核心架构说明**](docs/项目架构说明/Sage用户提示词增强全链路深度分析.md) - 详细的技术架构和实现原理
- [**部署指南**](docs/指南/Sage_MCP部署指南.md) - 完整的环境搭建和配置指南
- [**RAG参数设置**](docs/指南/RAG参数设置指南.md) - 检索增强生成的参数优化
- [**数据库部署**](docs/指南/数据库Docker部署指南.md) - PostgreSQL + pgvector 部署指南

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m "Add your feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 创建 Pull Request

### 开发规范
- 遵循 PEP8 编码规范
- 新功能需要添加测试用例
- 重大变更需要更新文档
- 提交信息使用中文，格式清晰

## 📄 许可证

本项目基于 MIT 许可证开源 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Claude](https://claude.ai) - AI助手集成平台
- [PostgreSQL](https://postgresql.org) + [pgvector](https://github.com/pgvector/pgvector) - 向量数据库
- [SiliconFlow](https://siliconflow.cn) - AI模型API服务
- [MCP Protocol](https://modelcontextprotocol.io) - 模型上下文协议

---

**维护团队**：Sage Development Team  
**最后更新**：2025-08-03  
**版本**：v3.0.0

> 💡 **提示**：首次使用建议阅读[部署指南](docs/指南/Sage_MCP部署指南.md)，遇到问题可查看[执行报告](docs/执行报告/)中的相关解决方案。