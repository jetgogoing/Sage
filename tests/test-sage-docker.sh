#!/bin/bash

# Sage Docker 测试验证脚本

echo "🧪 Sage Docker 测试验证"
echo "======================="
echo ""

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试函数
run_test() {
    local test_name=$1
    local test_command=$2
    local expected_result=$3
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "📋 测试: $test_name ... "
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ 通过${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ 失败${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# 1. 容器状态检查
echo "1️⃣ 容器状态检查"
echo "----------------"
run_test "应用容器运行状态" "docker ps | grep -q sage-docker-app"
run_test "数据库容器运行状态" "docker ps | grep -q sage-docker-db"
echo ""

# 2. 健康检查
echo "2️⃣ 服务健康检查"
echo "----------------"
run_test "MCP 健康检查端点" "curl -s http://localhost:17800/health | grep -q 'healthy'"
run_test "数据库健康状态" "[[ $(docker inspect --format='{{.State.Health.Status}}' sage-docker-db) == 'healthy' ]]"
echo ""

# 3. API 端点测试
echo "3️⃣ API 端点测试"
echo "----------------"

# 测试 .well-known 配置
run_test "MCP 配置端点" "curl -s http://localhost:17800/mcp/.well-known/mcp-configuration | grep -q 'mcp_version'"

# 测试 MCP 初始化
echo -n "📋 测试: MCP 初始化请求 ... "
INIT_RESPONSE=$(curl -s -X POST http://localhost:17800/mcp \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": "test-init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        }
    }')

if echo "$INIT_RESPONSE" | grep -q '"result"'; then
    echo -e "${GREEN}✅ 通过${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ 失败${NC}"
    echo "   响应: $INIT_RESPONSE"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# 测试工具列表
echo -n "📋 测试: 工具列表请求 ... "
TOOLS_RESPONSE=$(curl -s -X POST http://localhost:17800/mcp \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": "test-tools",
        "method": "tools/list",
        "params": {}
    }')

if echo "$TOOLS_RESPONSE" | grep -q 'save_conversation'; then
    echo -e "${GREEN}✅ 通过${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ 失败${NC}"
    echo "   响应: $TOOLS_RESPONSE"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo ""

# 4. 数据库连接测试
echo "4️⃣ 数据库连接测试"
echo "------------------"

# 测试数据库连接
echo -n "📋 测试: PostgreSQL 连接 ... "
if docker exec sage-docker-db psql -U sage_user -d sage_memory -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 通过${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ 失败${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# 测试 pgvector 扩展
echo -n "📋 测试: pgvector 扩展 ... "
if docker exec sage-docker-db psql -U sage_user -d sage_memory -c "SELECT * FROM pg_extension WHERE extname='vector';" | grep -q vector; then
    echo -e "${GREEN}✅ 通过${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ 失败${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo ""

# 5. 功能测试
echo "5️⃣ 功能测试"
echo "------------"

# 测试保存对话
echo -n "📋 测试: 保存对话功能 ... "
SAVE_RESPONSE=$(curl -s -X POST http://localhost:17800/mcp \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": "test-save",
        "method": "tools/call",
        "params": {
            "name": "save_conversation",
            "arguments": {
                "user_prompt": "测试用户输入",
                "assistant_response": "测试助手回复",
                "project_context": "test-docker",
                "metadata": {
                    "test": true,
                    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
                }
            }
        }
    }')

if echo "$SAVE_RESPONSE" | grep -q '"result"' && ! echo "$SAVE_RESPONSE" | grep -q '"error"'; then
    echo -e "${GREEN}✅ 通过${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ 失败${NC}"
    echo "   响应: $SAVE_RESPONSE"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# 测试获取记忆统计
echo -n "📋 测试: 获取记忆统计 ... "
STATS_RESPONSE=$(curl -s -X POST http://localhost:17800/mcp \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": "test-stats",
        "method": "tools/call",
        "params": {
            "name": "get_memory_stats",
            "arguments": {}
        }
    }')

if echo "$STATS_RESPONSE" | grep -q '"total_memories"'; then
    echo -e "${GREEN}✅ 通过${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ 失败${NC}"
    echo "   响应: $STATS_RESPONSE"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo ""

# 6. 性能测试
echo "6️⃣ 性能基准测试"
echo "----------------"

echo -n "📋 测试: API 响应时间 ... "
START_TIME=$(date +%s.%N)
curl -s http://localhost:17800/health > /dev/null
END_TIME=$(date +%s.%N)
RESPONSE_TIME=$(echo "$END_TIME - $START_TIME" | bc)

if (( $(echo "$RESPONSE_TIME < 1.0" | bc -l) )); then
    echo -e "${GREEN}✅ 通过${NC} (${RESPONSE_TIME}秒)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${YELLOW}⚠️  警告${NC} (${RESPONSE_TIME}秒 - 响应较慢)"
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo ""
echo "========================================"
echo "📊 测试结果汇总"
echo "========================================"
echo "总测试数: $TOTAL_TESTS"
echo -e "通过测试: ${GREEN}$PASSED_TESTS${NC}"
echo -e "失败测试: ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 所有测试通过！Sage Docker 部署成功！${NC}"
    exit 0
else
    echo -e "${RED}⚠️  有 $FAILED_TESTS 个测试失败，请检查日志${NC}"
    echo ""
    echo "调试命令:"
    echo "- 查看应用日志: docker logs sage-docker-app"
    echo "- 查看数据库日志: docker logs sage-docker-db"
    echo "- 检查容器状态: docker ps -a | grep sage-docker"
    exit 1
fi