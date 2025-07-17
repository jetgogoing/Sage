# Changelog

所有重要的变更都会记录在此文件中。

## [1.1.2] - 2025-01-17

### 修复
- 修复向量数据库 embedding 列类型不匹配问题
- 修复数据库表权限配置错误
- 解决对话保存时的 "column embedding is of type jsonb but expression is of type vector" 错误

### 改进
- 优化启动脚本，支持环境变量传递（SILICONFLOW_API_KEY 等）
- 清理项目中的无效启动脚本（删除 7 个过时脚本）
- 简化项目结构，只保留 `scripts/sage_mcp_stdio_wrapper.sh`

### 文档
- 更新环境配置说明
- 添加 API Key 设置指南
- 完善故障排除文档

### 技术细节
- 统一使用 `vector(4096)` 类型存储向量嵌入
- 修正表所有权为 sage 用户
- 改进数据库初始化流程

## [1.1.1] - 2025-01-17

### 修复
- 修复数据库连接问题
- 恢复 pgvector 扩展支持
- 解决 MCP Server 启动失败问题

### 改进
- 优化 Docker 镜像构建
- 改进错误处理机制

## [1.1.0] - 2025-01-16

### 新功能
- 实现 stdio 模式支持
- 单容器部署方案
- 智能启动包装脚本

### 改进
- 大规模架构简化
- 优化 Docker 部署流程
- 提升系统稳定性

## [1.0.0] - 2025-01-14

### 初始版本
- 核心记忆存储功能
- MCP 协议支持
- PostgreSQL + pgvector 集成
- Docker 容器化部署