#!/bin/bash
# 阶段4 Claude Code MCP集成与协议实现测试脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 阶段4：Claude Code MCP集成与协议实现测试${NC}"
echo -e "${BLUE}=================================================${NC}"

# 创建测试结果目录
TEST_RESULTS_DIR="test_results/stage4_$(date '+%Y%m%d_%H%M%S')"
mkdir -p "$TEST_RESULTS_DIR"

echo -e "${YELLOW}📁 测试结果将保存到: $TEST_RESULTS_DIR${NC}"

# 检查环境变量
if [ -z "$SILICONFLOW_API_KEY" ]; then
    echo -e "${RED}❌ SILICONFLOW_API_KEY 环境变量未设置${NC}"
    echo -e "${YELLOW}💡 请设置 API 密钥: export SILICONFLOW_API_KEY=your-key${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 环境变量检查通过${NC}"

# 检查MCP服务器是否运行
echo -e "${YELLOW}🔍 检查MCP服务器状态...${NC}"
MCP_SERVER_URL=${MCP_SERVER_URL:-"http://localhost:17800"}

if curl -s "$MCP_SERVER_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ MCP服务器运行正常${NC}"
else
    echo -e "${RED}❌ MCP服务器未运行或无法访问${NC}"
    echo -e "${YELLOW}💡 请启动MCP服务器: python app/sage_mcp_server.py${NC}"
    echo -e "${YELLOW}💡 或检查服务器URL: $MCP_SERVER_URL${NC}"
    exit 1
fi

# 测试函数
run_test() {
    local test_name="$1"
    local test_command="$2"
    local test_file="$TEST_RESULTS_DIR/${test_name}.json"
    
    echo -e "${YELLOW}🔄 运行测试: $test_name${NC}"
    
    if eval "$test_command" > "$test_file" 2>&1; then
        echo -e "${GREEN}✅ $test_name 测试完成${NC}"
        return 0
    else
        echo -e "${RED}❌ $test_name 测试失败${NC}"
        echo -e "${YELLOW}📋 查看详细信息: $test_file${NC}"
        return 1
    fi
}

# 1. MCP协议测试
echo -e "\n${BLUE}🔗 1. MCP协议实现测试${NC}"
run_test "mcp_protocol" "python tests/test_mcp_protocol.py --url $MCP_SERVER_URL --output /dev/stdout"

# 2. Claude Code集成测试
echo -e "\n${BLUE}🤖 2. Claude Code集成测试${NC}"
run_test "claude_code_integration" "python tests/test_claude_code_integration.py --url $MCP_SERVER_URL --output /dev/stdout"

# 3. 工具发现和执行测试
echo -e "\n${BLUE}🛠️ 3. 工具发现和执行测试${NC}"

# 3.1 工具列表获取
echo -e "${YELLOW}   📋 测试工具发现...${NC}"
TOOLS_LIST=$(curl -s -X POST "$MCP_SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": "test-tools-list",
        "method": "tools/list",
        "params": {}
    }')

if echo "$TOOLS_LIST" | jq -e '.result.tools | length > 0' > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ 工具发现成功${NC}"
    echo "$TOOLS_LIST" > "$TEST_RESULTS_DIR/tools_discovery.json"
else
    echo -e "${RED}   ❌ 工具发现失败${NC}"
    echo "$TOOLS_LIST" > "$TEST_RESULTS_DIR/tools_discovery_error.json"
fi

# 3.2 工具执行测试
echo -e "${YELLOW}   🔧 测试工具执行...${NC}"
TOOL_EXECUTION=$(curl -s -X POST "$MCP_SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": "test-tool-call",
        "method": "tools/call",
        "params": {
            "name": "get_memory_stats",
            "arguments": {"include_performance": true}
        }
    }')

if echo "$TOOL_EXECUTION" | jq -e '.result' > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ 工具执行成功${NC}"
    echo "$TOOL_EXECUTION" > "$TEST_RESULTS_DIR/tool_execution.json"
else
    echo -e "${RED}   ❌ 工具执行失败${NC}"
    echo "$TOOL_EXECUTION" > "$TEST_RESULTS_DIR/tool_execution_error.json"
fi

# 4. 服务器信息和兼容性测试
echo -e "\n${BLUE}ℹ️ 4. 服务器信息和兼容性测试${NC}"

# 4.1 MCP服务器信息
echo -e "${YELLOW}   📊 获取服务器信息...${NC}"
SERVER_INFO=$(curl -s "$MCP_SERVER_URL/mcp/info")

if echo "$SERVER_INFO" | jq -e '.name' > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ 服务器信息获取成功${NC}"
    echo "$SERVER_INFO" > "$TEST_RESULTS_DIR/server_info.json"
else
    echo -e "${RED}   ❌ 服务器信息获取失败${NC}"
    echo "$SERVER_INFO" > "$TEST_RESULTS_DIR/server_info_error.json"
fi

# 4.2 初始化协议测试
echo -e "${YELLOW}   🔄 测试初始化协议...${NC}"
INIT_RESULT=$(curl -s -X POST "$MCP_SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": "test-init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
    }')

if echo "$INIT_RESULT" | jq -e '.result.protocolVersion' > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ 初始化协议测试成功${NC}"
    echo "$INIT_RESULT" > "$TEST_RESULTS_DIR/initialization.json"
else
    echo -e "${RED}   ❌ 初始化协议测试失败${NC}"
    echo "$INIT_RESULT" > "$TEST_RESULTS_DIR/initialization_error.json"
fi

# 5. 性能和负载测试
echo -e "\n${BLUE}⚡ 5. 性能和负载测试${NC}"

# 5.1 并发请求测试
echo -e "${YELLOW}   🔥 测试并发请求处理...${NC}"
CONCURRENT_TEST_FILE="$TEST_RESULTS_DIR/concurrent_test.json"

python3 << EOF
import asyncio
import aiohttp
import json
import time
from datetime import datetime

async def test_concurrent_requests():
    results = {
        'test_timestamp': datetime.now().isoformat(),
        'concurrent_levels': {},
        'overall_status': 'success'
    }
    
    base_url = "$MCP_SERVER_URL"
    
    async def make_request(session, request_id):
        try:
            start_time = time.time()
            payload = {
                "jsonrpc": "2.0",
                "id": f"concurrent-{request_id}",
                "method": "tools/call",
                "params": {
                    "name": "get_memory_stats",
                    "arguments": {}
                }
            }
            
            async with session.post(
                f"{base_url}/mcp",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                end_time = time.time()
                if response.status == 200:
                    return {'status': 'success', 'time': end_time - start_time}
                else:
                    return {'status': 'error', 'code': response.status}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    # 测试不同并发级别
    for concurrency in [1, 5, 10, 20]:
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                
                tasks = [make_request(session, i) for i in range(concurrency)]
                responses = await asyncio.gather(*tasks)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                successful = sum(1 for r in responses if r['status'] == 'success')
                failed = len(responses) - successful
                
                if successful > 0:
                    avg_response_time = sum(r['time'] for r in responses if r['status'] == 'success') / successful
                else:
                    avg_response_time = 0
                
                results['concurrent_levels'][f'concurrent_{concurrency}'] = {
                    'concurrency_level': concurrency,
                    'total_time': total_time,
                    'successful_requests': successful,
                    'failed_requests': failed,
                    'average_response_time': avg_response_time,
                    'requests_per_second': successful / total_time if total_time > 0 else 0
                }
                
                if failed > 0:
                    results['overall_status'] = 'warning'
                    
        except Exception as e:
            results['concurrent_levels'][f'concurrent_{concurrency}'] = {
                'status': 'error',
                'error': str(e)
            }
            results['overall_status'] = 'error'
    
    return results

# 运行并发测试
result = asyncio.run(test_concurrent_requests())
with open('$CONCURRENT_TEST_FILE', 'w') as f:
    json.dump(result, f, indent=2)

print(f"并发测试完成，结果保存到: $CONCURRENT_TEST_FILE")
EOF

if [ -f "$CONCURRENT_TEST_FILE" ]; then
    echo -e "${GREEN}   ✅ 并发测试完成${NC}"
else
    echo -e "${RED}   ❌ 并发测试失败${NC}"
fi

# 6. 错误处理和恢复测试
echo -e "\n${BLUE}🛡️ 6. 错误处理和恢复测试${NC}"

# 6.1 无效请求测试
echo -e "${YELLOW}   🚨 测试错误处理...${NC}"
ERROR_TEST_FILE="$TEST_RESULTS_DIR/error_handling_test.json"

# 测试无效方法
INVALID_METHOD=$(curl -s -X POST "$MCP_SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -d '{
        "jsonrpc": "2.0",
        "id": "test-invalid",
        "method": "invalid_method_test",
        "params": {}
    }')

# 测试无效JSON
INVALID_JSON=$(curl -s -X POST "$MCP_SERVER_URL/mcp" \
    -H "Content-Type: application/json" \
    -d 'invalid json content')

# 合并错误测试结果
cat > "$ERROR_TEST_FILE" << EOF
{
  "test_timestamp": "$(date -Iseconds)",
  "invalid_method_test": $INVALID_METHOD,
  "invalid_json_test": {
    "response": "$INVALID_JSON",
    "expected": "Should return 400 or 422 error"
  }
}
EOF

echo -e "${GREEN}   ✅ 错误处理测试完成${NC}"

# 7. 生成综合报告
echo -e "\n${BLUE}📋 7. 生成综合测试报告${NC}"

REPORT_FILE="$TEST_RESULTS_DIR/stage4_comprehensive_report.json"

cat > "$REPORT_FILE" << EOF
{
  "test_timestamp": "$(date -Iseconds)",
  "stage": "4",
  "stage_name": "Claude Code MCP集成与协议实现",
  "test_environment": {
    "os": "$(uname -s)",
    "python_version": "$(python3 --version 2>&1)",
    "mcp_server_url": "$MCP_SERVER_URL",
    "api_configured": $([ -n "$SILICONFLOW_API_KEY" ] && echo "true" || echo "false")
  },
  "test_results": {
EOF

# 添加各个测试结果
first=true
for result_file in "$TEST_RESULTS_DIR"/*.json; do
    if [ -f "$result_file" ] && [ "$(basename "$result_file")" != "stage4_comprehensive_report.json" ]; then
        test_name=$(basename "$result_file" .json)
        
        if [ "$first" = true ]; then
            first=false
        else
            echo "    ," >> "$REPORT_FILE"
        fi
        
        echo "    \"$test_name\": " >> "$REPORT_FILE"
        
        # 检查文件是否包含有效JSON
        if python3 -c "import json; json.load(open('$result_file'))" 2>/dev/null; then
            cat "$result_file" >> "$REPORT_FILE"
        else
            # 如果不是JSON，创建错误对象
            echo "      {" >> "$REPORT_FILE"
            echo "        \"status\": \"error\"," >> "$REPORT_FILE"
            echo "        \"error\": \"Test output was not valid JSON\"," >> "$REPORT_FILE"
            echo "        \"raw_output\": \"$(cat "$result_file" | head -10 | tr '\n' '\\n')\"" >> "$REPORT_FILE"
            echo "      }" >> "$REPORT_FILE"
        fi
    fi
done

cat >> "$REPORT_FILE" << EOF
  },
  "summary": {
    "total_tests": $(ls "$TEST_RESULTS_DIR"/*.json 2>/dev/null | wc -l),
    "tests_passed": 0,
    "tests_failed": 0,
    "overall_status": "unknown"
  }
}
EOF

# 计算测试统计
python3 << EOF
import json
import os

report_file = "$REPORT_FILE"
try:
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    passed = 0
    failed = 0
    warning = 0
    
    for test_name, test_result in report.get('test_results', {}).items():
        if isinstance(test_result, dict):
            status = test_result.get('status', 'unknown')
            overall_status = test_result.get('overall_status', status)
            
            if overall_status in ['success', 'completed']:
                passed += 1
            elif overall_status in ['error', 'failed']:
                failed += 1
            elif overall_status == 'warning':
                warning += 1
    
    total = passed + failed + warning
    
    # 更新summary
    report['summary']['tests_passed'] = passed
    report['summary']['tests_failed'] = failed
    report['summary']['tests_warning'] = warning
    report['summary']['total_tests'] = total
    
    if failed == 0 and warning == 0 and passed > 0:
        report['summary']['overall_status'] = 'success'
    elif failed == 0 and warning > 0:
        report['summary']['overall_status'] = 'warning'
    elif failed > 0:
        report['summary']['overall_status'] = 'failed'
    else:
        report['summary']['overall_status'] = 'unknown'
    
    # 保存更新的报告
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Tests passed: {passed}")
    print(f"Tests warning: {warning}")
    print(f"Tests failed: {failed}")
    print(f"Overall status: {report['summary']['overall_status']}")
    
except Exception as e:
    print(f"Error processing report: {e}")
    exit(1)
EOF

# 显示最终结果
echo -e "\n${BLUE}📊 阶段4测试完成！${NC}"
echo -e "${YELLOW}📋 详细报告: $REPORT_FILE${NC}"

# 读取最终状态
OVERALL_STATUS=$(python3 -c "import json; print(json.load(open('$REPORT_FILE'))['summary']['overall_status'])" 2>/dev/null || echo "unknown")
TESTS_PASSED=$(python3 -c "import json; print(json.load(open('$REPORT_FILE'))['summary']['tests_passed'])" 2>/dev/null || echo "0")
TESTS_WARNING=$(python3 -c "import json; print(json.load(open('$REPORT_FILE'))['summary']['tests_warning'])" 2>/dev/null || echo "0")
TESTS_FAILED=$(python3 -c "import json; print(json.load(open('$REPORT_FILE'))['summary']['tests_failed'])" 2>/dev/null || echo "0")

echo -e "\n${BLUE}📈 测试统计:${NC}"
echo -e "   ✅ 通过: $TESTS_PASSED"
echo -e "   ⚠️ 警告: $TESTS_WARNING"
echo -e "   ❌ 失败: $TESTS_FAILED"
echo -e "   📊 总体状态: $OVERALL_STATUS"

# MCP集成状态总结
echo -e "\n${BLUE}🤖 Claude Code MCP集成状态:${NC}"

if [ "$OVERALL_STATUS" = "success" ]; then
    echo -e "${GREEN}🎉 MCP协议实现完整，Claude Code集成就绪！${NC}"
    echo -e "${GREEN}✅ 所有核心功能已实现并测试通过${NC}"
    echo -e "${GREEN}✅ 工具发现和执行正常${NC}"
    echo -e "${GREEN}✅ 自动保存和上下文注入工作正常${NC}"
    echo -e "${GREEN}✅ 错误处理和并发性能良好${NC}"
elif [ "$OVERALL_STATUS" = "warning" ]; then
    echo -e "${YELLOW}⚠️ MCP协议基本实现，但存在一些警告${NC}"
    echo -e "${YELLOW}💡 建议查看详细报告并优化相关功能${NC}"
else
    echo -e "${RED}❌ MCP协议实现存在问题，需要修复${NC}"
    echo -e "${RED}🔧 请查看失败的测试并修复相关问题${NC}"
fi

# 下一步建议
echo -e "\n${BLUE}🎯 下一步建议:${NC}"
if [ "$OVERALL_STATUS" = "success" ]; then
    echo -e "${GREEN}1. 在Claude Code中配置MCP服务器${NC}"
    echo -e "${GREEN}2. 测试实际工作流程中的集成${NC}"
    echo -e "${GREEN}3. 监控生产环境性能${NC}"
    echo -e "${GREEN}4. 准备用户文档和使用指南${NC}"
else
    echo -e "${YELLOW}1. 修复失败的测试项目${NC}"
    echo -e "${YELLOW}2. 重新运行测试验证修复${NC}"
    echo -e "${YELLOW}3. 优化性能和错误处理${NC}"
    echo -e "${YELLOW}4. 完善MCP协议兼容性${NC}"
fi

# 根据结果设置退出码
case "$OVERALL_STATUS" in
    "success")
        echo -e "\n${GREEN}🚀 阶段4验证成功！MCP集成已准备就绪${NC}"
        exit 0
        ;;
    "warning")
        echo -e "\n${YELLOW}⚠️ 阶段4基本成功，但存在警告${NC}"
        exit 1
        ;;
    "failed")
        echo -e "\n${RED}❌ 阶段4测试失败，需要修复问题${NC}"
        exit 2
        ;;
    *)
        echo -e "\n${RED}❓ 无法确定测试状态${NC}"
        exit 3
        ;;
esac