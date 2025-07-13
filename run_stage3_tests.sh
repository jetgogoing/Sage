#!/bin/bash
# 阶段3数据库兼容性与迁移工具集成测试脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 阶段3：数据库兼容性与迁移工具测试${NC}"
echo -e "${BLUE}===========================================${NC}"

# 创建测试结果目录
TEST_RESULTS_DIR="test_results/stage3_$(date '+%Y%m%d_%H%M%S')"
mkdir -p "$TEST_RESULTS_DIR"

echo -e "${YELLOW}📁 测试结果将保存到: $TEST_RESULTS_DIR${NC}"

# 检查环境变量
if [ -z "$SILICONFLOW_API_KEY" ]; then
    echo -e "${RED}❌ SILICONFLOW_API_KEY 环境变量未设置${NC}"
    echo -e "${YELLOW}💡 请设置 API 密钥: export SILICONFLOW_API_KEY=your-key${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 环境变量检查通过${NC}"

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

# 1. 数据库结构检查
echo -e "\n${BLUE}📊 1. 数据库结构检查${NC}"
run_test "database_structure" "python app/migration_tool.py check"

# 2. 数据库性能测试
echo -e "\n${BLUE}⚡ 2. 数据库性能测试${NC}"
run_test "database_performance" "python tests/test_database_performance.py --output /dev/stdout"

# 3. 向量化质量测试
echo -e "\n${BLUE}🎯 3. 向量化质量测试${NC}"
run_test "vectorization_quality" "python tests/test_vectorization_quality.py --output /dev/stdout"

# 4. 迁移工具测试
echo -e "\n${BLUE}🔄 4. 迁移工具测试${NC}"

# 4.1 创建测试备份
echo -e "${YELLOW}   📦 创建测试备份...${NC}"
if python app/migration_tool.py backup --name "stage3_test_backup" > "$TEST_RESULTS_DIR/backup_test.log" 2>&1; then
    echo -e "${GREEN}   ✅ 备份创建成功${NC}"
else
    echo -e "${RED}   ❌ 备份创建失败${NC}"
fi

# 4.2 验证迁移工具
echo -e "${YELLOW}   🔍 验证迁移完整性...${NC}"
run_test "migration_verification" "python app/migration_tool.py verify"

# 4.3 数据库优化测试
echo -e "${YELLOW}   ⚡ 数据库优化测试...${NC}"
if python app/migration_tool.py optimize > "$TEST_RESULTS_DIR/optimization_test.log" 2>&1; then
    echo -e "${GREEN}   ✅ 数据库优化完成${NC}"
else
    echo -e "${RED}   ❌ 数据库优化失败${NC}"
fi

# 5. 生成综合报告
echo -e "\n${BLUE}📋 5. 生成综合测试报告${NC}"

REPORT_FILE="$TEST_RESULTS_DIR/stage3_comprehensive_report.json"

cat > "$REPORT_FILE" << EOF
{
  "test_timestamp": "$(date -Iseconds)",
  "stage": "3",
  "stage_name": "数据库兼容性与迁移工具",
  "test_environment": {
    "os": "$(uname -s)",
    "python_version": "$(python --version 2>&1)",
    "database_host": "${DB_HOST:-localhost}",
    "api_configured": $([ -n "$SILICONFLOW_API_KEY" ] && echo "true" || echo "false")
  },
  "test_results": {
EOF

# 添加各个测试结果
first=true
for result_file in "$TEST_RESULTS_DIR"/*.json; do
    if [ -f "$result_file" ] && [ "$(basename "$result_file")" != "stage3_comprehensive_report.json" ]; then
        test_name=$(basename "$result_file" .json)
        
        if [ "$first" = true ]; then
            first=false
        else
            echo "    ," >> "$REPORT_FILE"
        fi
        
        echo "    \"$test_name\": " >> "$REPORT_FILE"
        
        # 检查文件是否包含有效JSON
        if python -c "import json; json.load(open('$result_file'))" 2>/dev/null; then
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
python << EOF
import json
import os

report_file = "$REPORT_FILE"
try:
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    passed = 0
    failed = 0
    
    for test_name, test_result in report.get('test_results', {}).items():
        if isinstance(test_result, dict):
            status = test_result.get('status', 'unknown')
            if status in ['success', 'completed']:
                passed += 1
            elif status in ['error', 'failed']:
                failed += 1
            elif status == 'warning':
                passed += 1  # Warning counts as passed but with issues
    
    total = passed + failed
    
    # 更新summary
    report['summary']['tests_passed'] = passed
    report['summary']['tests_failed'] = failed
    report['summary']['total_tests'] = total
    
    if failed == 0 and passed > 0:
        report['summary']['overall_status'] = 'success'
    elif failed > 0 and passed > 0:
        report['summary']['overall_status'] = 'partial'
    elif failed > 0:
        report['summary']['overall_status'] = 'failed'
    else:
        report['summary']['overall_status'] = 'unknown'
    
    # 保存更新的报告
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {failed}")
    print(f"Overall status: {report['summary']['overall_status']}")
    
except Exception as e:
    print(f"Error processing report: {e}")
    exit(1)
EOF

# 显示最终结果
echo -e "\n${BLUE}📊 测试完成！${NC}"
echo -e "${YELLOW}📋 详细报告: $REPORT_FILE${NC}"

# 读取最终状态
OVERALL_STATUS=$(python -c "import json; print(json.load(open('$REPORT_FILE'))['summary']['overall_status'])" 2>/dev/null || echo "unknown")
TESTS_PASSED=$(python -c "import json; print(json.load(open('$REPORT_FILE'))['summary']['tests_passed'])" 2>/dev/null || echo "0")
TESTS_FAILED=$(python -c "import json; print(json.load(open('$REPORT_FILE'))['summary']['tests_failed'])" 2>/dev/null || echo "0")

echo -e "\n${BLUE}📈 测试统计:${NC}"
echo -e "   ✅ 通过: $TESTS_PASSED"
echo -e "   ❌ 失败: $TESTS_FAILED"
echo -e "   📊 总体状态: $OVERALL_STATUS"

# 根据结果设置退出码
case "$OVERALL_STATUS" in
    "success")
        echo -e "\n${GREEN}🎉 所有测试通过！阶段3验证成功${NC}"
        exit 0
        ;;
    "partial")
        echo -e "\n${YELLOW}⚠️ 部分测试失败，请检查详细报告${NC}"
        exit 1
        ;;
    "failed")
        echo -e "\n${RED}❌ 测试失败，需要修复问题${NC}"
        exit 2
        ;;
    *)
        echo -e "\n${RED}❓ 无法确定测试状态${NC}"
        exit 3
        ;;
esac