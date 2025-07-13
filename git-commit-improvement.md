# Git Commit 改进方案

## 当前 Commits 的问题和改进建议

### 原始 Commits 及改进方案

1. **原始**: `初始化 Sage MCP 轻量化记忆系统`
   **改进**: `feat: initialize Sage MCP memory system with core infrastructure`
   
2. **原始**: `优化项目结构和代码注释`
   **改进**: 应拆分为多个 commits：
   - `refactor(structure): reorganize project directory layout`
   - `docs(code): add inline documentation for core modules`
   
3. **原始**: `清理敏感信息，准备GitHub推送`
   **改进**: `chore(security): remove API keys and sensitive data from codebase`
   
4. **原始**: `feat: 完成阶段4 - Claude Code MCP集成与自动记忆注入`
   **改进**: `feat(mcp): implement Claude Code integration with auto-context injection`
   
5. **原始**: `docs: 添加完整的项目文档和测试文件`
   **改进**: 应拆分为：
   - `docs: add comprehensive project documentation`
   - `test: add unit and integration test suites`
   
6. **原始**: `feat: 添加核心系统文件和完整测试套件`
   **改进**: 应拆分为：
   - `feat(core): implement memory adapter and retrieval system`
   - `feat(mcp): add MCP server and interceptor modules`
   - `test: add comprehensive test coverage for core features`

## 推荐的 Commit 规范

### 1. 类型 (Type)
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更改
- `style`: 代码格式（不影响代码运行的变动）
- `refactor`: 重构（既不是新增功能，也不是修复bug）
- `test`: 增加测试
- `chore`: 构建过程或辅助工具的变动
- `perf`: 性能优化

### 2. 范围 (Scope) - 可选
- `mcp`: MCP 协议相关
- `memory`: 记忆系统
- `db`: 数据库相关
- `api`: API 接口
- `config`: 配置相关
- `docker`: Docker 相关

### 3. 格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

### 示例
```
feat(mcp): implement auto-context injection for Claude Code

- Add request interceptor to analyze user queries
- Implement intelligent context retrieval with Qwen3-Reranker
- Add caching mechanism for performance optimization
- Support transparent memory access across projects

Closes #123
```

## 使用 git rebase 修改历史

如果要修改已提交的 commits：

```bash
# 交互式 rebase 最近 8 个 commits
git rebase -i HEAD~8

# 在编辑器中，将需要修改的 commit 前的 'pick' 改为 'reword'
# 保存后会逐个让你修改 commit message

# 完成后强制推送（注意：只在个人分支上这样做）
git push --force-with-lease origin feature/stage4-stable-rollback
```

## 未来 Commit 最佳实践

1. **原子性提交**：每个 commit 只做一件事
2. **清晰描述**：说明"做了什么"和"为什么"
3. **使用英文**：保持国际化，便于开源协作
4. **遵循规范**：始终使用 type(scope): subject 格式
5. **添加详情**：重要改动在 body 中说明细节

## 配置 Commit 模板

创建 `.gitmessage` 文件：
```
# <type>(<scope>): <subject>
# 
# <body>
# 
# <footer>
# 
# Type: feat|fix|docs|style|refactor|test|chore|perf
# Scope: mcp|memory|db|api|config|docker
# Subject: imperative mood, lowercase, no period
# Body: explain what and why, not how
# Footer: closes #issue
```

配置使用：
```bash
git config commit.template .gitmessage
```