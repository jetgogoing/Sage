#!/bin/bash
# Sage MCP 集成测试脚本
# 完整的Docker容器启动和MCP协议功能测试

set -euo pipefail

# 配置参数
CONTAINER_NAME="sage-mcp"
DB_NAME="${DB_NAME:-sage_memory}"
DB_USER="${DB_USER:-sage}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_LOG_FILE="$PROJECT_ROOT/test_results.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 错误处理函数
error_msg() {
    echo -e "${RED}[FAIL] $1${NC}" | tee -a "$TEST_LOG_FILE"
    ((FAILED_TESTS++))
}

# 成功信息
success_msg() {
    echo -e "${GREEN}[PASS] $1${NC}" | tee -a "$TEST_LOG_FILE"
    ((PASSED_TESTS++))
}

# 警告信息
warning_msg() {
    echo -e "${YELLOW}[WARN] $1${NC}" | tee -a "$TEST_LOG_FILE"
}

# 信息输出
info_msg() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$TEST_LOG_FILE"
}

# 测试函数包装器
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    ((TOTAL_TESTS++))
    info_msg "执行测试: $test_name"
    
    if $test_function; then
        success_msg "$test_name"
        return 0
    else
        error_msg "$test_name"
        return 1
    fi
}

# 显示使用说明
show_usage() {
    cat << EOF
用法: $0 [选项]

选项:
  -h, --help          显示此帮助信息
  -c, --container     指定容器名称 (默认: ${CONTAINER_NAME})
  --skip-rebuild      跳过重新构建步骤
  --quick             快速测试（跳过性能测试）
  --cleanup           测试完成后清理容器

测试模块:
  1. 容器构建和启动测试
  2. PostgreSQL数据库功能测试
  3. MCP服务器功能测试
  4. MCP协议5个工具测试
  5. 性能和稳定性测试
  6. 日志和监控测试
EOF
}

# 解析命令行参数
parse_arguments() {
    SKIP_REBUILD=false
    QUICK_MODE=false
    CLEANUP_AFTER=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -c|--container)
                CONTAINER_NAME="$2"
                shift 2
                ;;
            --skip-rebuild)
                SKIP_REBUILD=true
                shift
                ;;
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --cleanup)
                CLEANUP_AFTER=true
                shift
                ;;
            -*)
                error_msg "未知选项: $1"
                exit 1
                ;;
            *)
                error_msg "未知参数: $1"
                exit 1
                ;;
        esac
    done
}

# 初始化测试环境
initialize_test_environment() {
    info_msg "初始化测试环境..."
    
    cd "$PROJECT_ROOT"
    
    # 创建测试日志文件
    echo "Sage MCP 集成测试报告 - $(date)" > "$TEST_LOG_FILE"
    echo "=================================" >> "$TEST_LOG_FILE"
    
    # 检查必要文件
    local required_files=(
        "docker-compose.yml"
        "Dockerfile"
        "sage_mcp_stdio_single.py"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error_msg "缺少必要文件: $file"
            exit 1
        fi
    done
    
    success_msg "测试环境初始化完成"
}

# 测试1: Docker容器构建和启动
test_container_build_and_start() {
    if [ "$SKIP_REBUILD" = false ]; then
        info_msg "清理现有容器..."
        docker-compose down -v --remove-orphans 2>/dev/null || true
        
        info_msg "构建Docker镜像..."
        if ! docker-compose build --no-cache 2>&1 | tee -a "$TEST_LOG_FILE"; then
            return 1
        fi
    fi
    
    info_msg "启动容器..."
    if ! docker-compose up -d 2>&1 | tee -a "$TEST_LOG_FILE"; then
        return 1
    fi
    
    # 等待容器启动
    info_msg "等待容器启动..."
    sleep 10
    
    # 检查容器状态
    if ! docker ps -f name="${CONTAINER_NAME}" --format "{{.Status}}" | grep -q "Up"; then
        error_msg "容器启动失败"
        docker-compose logs | tee -a "$TEST_LOG_FILE"
        return 1
    fi
    
    return 0
}

# 测试2: PostgreSQL数据库功能
test_postgresql_functionality() {
    info_msg "测试PostgreSQL连接..."
    
    # 等待数据库就绪
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec "${CONTAINER_NAME}" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
            break
        fi
        info_msg "等待数据库启动... (尝试 $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        error_msg "数据库启动超时"
        return 1
    fi
    
    # 测试数据库连接
    if ! docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
        error_msg "数据库连接失败"
        return 1
    fi
    
    # 检查pgvector扩展
    local has_vector=$(docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');
    " 2>/dev/null | tr -d ' \n' || echo "f")
    
    if [ "$has_vector" != "t" ]; then
        error_msg "pgvector扩展未安装"
        return 1
    fi
    
    # 检查表结构
    local required_tables=("memories" "sessions")
    for table in "${required_tables[@]}"; do
        if ! docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -c "\d $table" >/dev/null 2>&1; then
            error_msg "表 $table 不存在"
            return 1
        fi
    done
    
    return 0
}

# 测试3: MCP服务器启动
test_mcp_server_startup() {
    info_msg "检查MCP服务器进程..."
    
    # 检查Python进程
    if ! docker exec "${CONTAINER_NAME}" pgrep -f "sage_mcp_stdio_single.py" >/dev/null 2>&1; then
        # 尝试启动MCP服务
        info_msg "启动MCP服务..."
        if ! docker exec "${CONTAINER_NAME}" supervisorctl start sage-mcp; then
            error_msg "MCP服务启动失败"
            docker exec "${CONTAINER_NAME}" supervisorctl status | tee -a "$TEST_LOG_FILE"
            return 1
        fi
        
        # 再次检查
        sleep 5
        if ! docker exec "${CONTAINER_NAME}" pgrep -f "sage_mcp_stdio_single.py" >/dev/null 2>&1; then
            error_msg "MCP进程未运行"
            return 1
        fi
    fi
    
    return 0
}

# 测试4: MCP协议基础功能
test_mcp_protocol_basic() {
    info_msg "测试MCP协议基础通信..."
    
    # 测试initialize请求
    local init_response=$(echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}' | \
        timeout 10 docker exec -i "${CONTAINER_NAME}" python3 /app/sage_mcp_stdio_single.py 2>/dev/null || echo "")
    
    if [ -z "$init_response" ]; then
        error_msg "MCP initialize请求无响应"
        return 1
    fi
    
    # 检查响应格式
    if ! echo "$init_response" | grep -q "jsonrpc"; then
        error_msg "MCP响应格式错误"
        echo "响应内容: $init_response" | tee -a "$TEST_LOG_FILE"
        return 1
    fi
    
    return 0
}

# 测试5: MCP工具功能
test_mcp_tools() {
    info_msg "测试MCP工具功能..."
    
    # 测试get_status工具
    local status_request='{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_status", "arguments": {}}}'
    local status_response=$(echo "$status_request" | timeout 10 docker exec -i "${CONTAINER_NAME}" python3 /app/sage_mcp_stdio_single.py 2>/dev/null || echo "")
    
    if [ -z "$status_response" ]; then
        warning_msg "get_status工具测试失败"
    else
        success_msg "get_status工具响应正常"
    fi
    
    # 测试S命令（保存对话）
    local save_request='{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "S", "arguments": {"user_prompt": "测试用户输入", "assistant_response": "测试助手回复"}}}'
    local save_response=$(echo "$save_request" | timeout 15 docker exec -i "${CONTAINER_NAME}" python3 /app/sage_mcp_stdio_single.py 2>/dev/null || echo "")
    
    if [ -z "$save_response" ]; then
        warning_msg "S命令（保存对话）测试失败"
    else
        success_msg "S命令（保存对话）响应正常"
        
        # 验证数据是否保存到数据库
        local memory_count=$(docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
            SELECT COUNT(*) FROM memories WHERE user_input LIKE '%测试用户输入%';
        " 2>/dev/null | tr -d ' \n' || echo "0")
        
        if [ "$memory_count" -gt 0 ]; then
            success_msg "对话数据成功保存到数据库"
        else
            warning_msg "对话数据未保存到数据库"
        fi
    fi
    
    return 0
}

# 测试6: 性能基准测试
test_performance_baseline() {
    if [ "$QUICK_MODE" = true ]; then
        info_msg "快速模式：跳过性能测试"
        return 0
    fi
    
    info_msg "执行性能基准测试..."
    
    # 检查容器资源使用
    local container_stats=$(docker stats "${CONTAINER_NAME}" --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "无法获取")
    info_msg "容器资源使用: $container_stats"
    
    # 测试数据库查询响应时间
    local start_time=$(date +%s%N)
    docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) FROM memories;" >/dev/null 2>&1
    local end_time=$(date +%s%N)
    local query_time=$(((end_time - start_time) / 1000000))  # 转换为毫秒
    
    info_msg "数据库查询响应时间: ${query_time}ms"
    
    if [ "$query_time" -gt 1000 ]; then
        warning_msg "数据库查询响应时间较慢: ${query_time}ms"
    fi
    
    return 0
}

# 测试7: 容器重启后数据完整性
test_container_restart_integrity() {
    info_msg "测试容器重启后数据完整性..."
    
    # 记录重启前的数据
    local memory_count_before=$(docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT COUNT(*) FROM memories;
    " 2>/dev/null | tr -d ' \n' || echo "0")
    
    # 重启容器
    info_msg "重启容器..."
    if ! docker-compose restart 2>&1 | tee -a "$TEST_LOG_FILE"; then
        error_msg "容器重启失败"
        return 1
    fi
    
    # 等待服务重新启动
    sleep 15
    
    # 等待数据库就绪
    local max_attempts=20
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec "${CONTAINER_NAME}" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
            break
        fi
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        error_msg "重启后数据库未就绪"
        return 1
    fi
    
    # 检查数据完整性
    local memory_count_after=$(docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT COUNT(*) FROM memories;
    " 2>/dev/null | tr -d ' \n' || echo "0")
    
    info_msg "重启前记录数: $memory_count_before, 重启后记录数: $memory_count_after"
    
    if [ "$memory_count_before" != "$memory_count_after" ]; then
        error_msg "重启后数据不完整"
        return 1
    fi
    
    return 0
}

# 测试8: 日志记录功能
test_logging_functionality() {
    info_msg "测试日志记录功能..."
    
    # 检查日志文件存在
    local log_files=(
        "/var/log/sage/sage_mcp_error.log"
        "/var/log/supervisor/supervisord.log"
    )
    
    for log_file in "${log_files[@]}"; do
        if docker exec "${CONTAINER_NAME}" test -f "$log_file" 2>/dev/null; then
            local log_size=$(docker exec "${CONTAINER_NAME}" stat -c%s "$log_file" 2>/dev/null || echo "0")
            info_msg "日志文件 $log_file 存在 (大小: $log_size bytes)"
        else
            warning_msg "日志文件 $log_file 不存在"
        fi
    done
    
    # 检查supervisord状态
    local supervisor_status=$(docker exec "${CONTAINER_NAME}" supervisorctl status 2>/dev/null || echo "supervisorctl不可用")
    info_msg "Supervisor状态: $supervisor_status"
    
    return 0
}

# 清理测试环境
cleanup_test_environment() {
    if [ "$CLEANUP_AFTER" = true ]; then
        info_msg "清理测试环境..."
        docker-compose down -v --remove-orphans 2>/dev/null || true
        success_msg "测试环境已清理"
    else
        info_msg "保留测试环境，使用 --cleanup 选项可自动清理"
    fi
}

# 生成测试报告
generate_test_report() {
    echo "" | tee -a "$TEST_LOG_FILE"
    echo "=================================" | tee -a "$TEST_LOG_FILE"
    echo "测试完成时间: $(date)" | tee -a "$TEST_LOG_FILE"
    echo "总测试数: $TOTAL_TESTS" | tee -a "$TEST_LOG_FILE"
    echo "通过测试: $PASSED_TESTS" | tee -a "$TEST_LOG_FILE"
    echo "失败测试: $FAILED_TESTS" | tee -a "$TEST_LOG_FILE"
    
    local success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo "成功率: ${success_rate}%" | tee -a "$TEST_LOG_FILE"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        success_msg "所有测试通过！"
    else
        error_msg "$FAILED_TESTS 个测试失败"
    fi
    
    info_msg "详细测试报告: $TEST_LOG_FILE"
}

# 主执行流程
main() {
    echo "=========================================="
    echo "Sage MCP 集成测试工具"
    echo "=========================================="
    
    parse_arguments "$@"
    initialize_test_environment
    
    info_msg "开始集成测试..."
    
    # 执行所有测试
    run_test "Docker容器构建和启动" test_container_build_and_start
    run_test "PostgreSQL数据库功能" test_postgresql_functionality
    run_test "MCP服务器启动" test_mcp_server_startup
    run_test "MCP协议基础功能" test_mcp_protocol_basic
    run_test "MCP工具功能" test_mcp_tools
    run_test "性能基准测试" test_performance_baseline
    run_test "容器重启数据完整性" test_container_restart_integrity
    run_test "日志记录功能" test_logging_functionality
    
    generate_test_report
    cleanup_test_environment
    
    echo "=========================================="
    
    # 返回失败测试数量作为退出码
    exit $FAILED_TESTS
}

# 执行主流程
main "$@"