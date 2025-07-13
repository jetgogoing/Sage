#!/bin/bash

# 自动化 commit message 更新脚本

echo "开始更新 commit messages..."

# 创建临时文件存储新的 commit messages
cat > /tmp/new-commits.txt << 'EOF'
pick cddf4db feat: initialize Sage MCP memory system with core infrastructure
pick 2a16dc6 refactor: reorganize project structure and add code documentation
pick f7d5c11 chore(security): remove API keys and sensitive data from codebase
pick 8828659 feat(mcp): implement Claude Code integration with auto-context injection
pick 90e155e docs: add comprehensive project documentation and test suites
pick 56be738 feat(core): add memory system components and test infrastructure
pick 1951fa3 docs: update README.md to reflect MCP architecture and features
pick 74cad6f docs: add comprehensive Sage MCP usage guide
pick b7e4b0f docs(contrib): add commit guidelines and improvement tools
EOF

# 创建编辑器脚本
cat > /tmp/rebase-editor.sh << 'EOF'
#!/bin/bash
# 将所有的 pick 改为 reword 以便修改 commit message
sed -i '' 's/^pick cddf4db/reword cddf4db/g' "$1"
sed -i '' 's/^pick 2a16dc6/reword 2a16dc6/g' "$1"
sed -i '' 's/^pick f7d5c11/reword f7d5c11/g' "$1"
sed -i '' 's/^pick 8828659/reword 8828659/g' "$1"
sed -i '' 's/^pick 90e155e/reword 90e155e/g' "$1"
sed -i '' 's/^pick 56be738/reword 56be738/g' "$1"
sed -i '' 's/^pick 1951fa3/reword 1951fa3/g' "$1"
sed -i '' 's/^pick 74cad6f/reword 74cad6f/g' "$1"
EOF

chmod +x /tmp/rebase-editor.sh

echo "准备执行 rebase..."
echo "这将修改以下 commits："
echo
echo "1. 初始化 Sage MCP 轻量化记忆系统 -> feat: initialize Sage MCP memory system with core infrastructure"
echo "2. 优化项目结构和代码注释 -> refactor: reorganize project structure and add code documentation"
echo "3. 清理敏感信息，准备GitHub推送 -> chore(security): remove API keys and sensitive data from codebase"
echo "4. 完成阶段4 -> feat(mcp): implement Claude Code integration with auto-context injection"
echo "5. 添加完整的项目文档和测试文件 -> docs: add comprehensive project documentation and test suites"
echo "6. 添加核心系统文件和完整测试套件 -> feat(core): add memory system components and test infrastructure"
echo "7. 全面更新 README.md -> docs: update README.md to reflect MCP architecture and features"
echo "8. 添加完整的 Sage MCP 使用指南 -> docs: add comprehensive Sage MCP usage guide"
echo
echo "注意: 由于需要交互式编辑，请手动执行以下命令："
echo
echo "git rebase -i HEAD~8"
echo
echo "然后将需要修改的行从 'pick' 改为 'reword'，保存后会让你逐个修改 commit message。"
echo
echo "建议的新 commit messages 已保存在 /tmp/new-commits.txt"