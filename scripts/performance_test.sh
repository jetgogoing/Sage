#!/bin/bash
# Sage MCP 性能测试脚本
# 测试容器性能和并发处理能力

set -euo pipefail

# 配置参数
CONTAINER_NAME="sage-mcp"
DB_NAME="${DB_NAME:-sage_memory}"
DB_USER="${DB_USER:-sage}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 性能测试参数
CONCURRENT_REQUESTS=5
TEST_DURATION=30
MEMORY_THRESHOLD_MB=512
CPU_THRESHOLD_PERCENT=70

# 错误处理函数
error_msg() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# 成功信息
success_msg() {
    echo -e "${GREEN}[PASS] $1${NC}"
}

# 警告信息
warning_msg() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

# 信息输出
info_msg() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# 显示使用说明
show_usage() {
    cat << EOF
用法: $0 [选项]

选项:
  -h, --help              显示此帮助信息
  -c, --container         指定容器名称 (默认: ${CONTAINER_NAME})
  --concurrent REQUESTS   并发请求数 (默认: ${CONCURRENT_REQUESTS})
  --duration SECONDS      测试持续时间 (默认: ${TEST_DURATION}秒)
  --memory-threshold MB   内存使用阈值 (默认: ${MEMORY_THRESHOLD_MB}MB)
  --cpu-threshold PERCENT CPU使用阈值 (默认: ${CPU_THRESHOLD_PERCENT}%)
  --report                生成详细性能报告

性能测试项目:
  1. 基准性能测试
  2. 内存使用监控
  3. CPU利用率测试
  4. 数据库查询性能
  5. MCP协议响应时间
  6. 并发处理能力
  7. 资源泄露检测
EOF
}

# 解析命令行参数
parse_arguments() {
    GENERATE_REPORT=false
    
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
            --concurrent)
                CONCURRENT_REQUESTS="$2"
                shift 2
                ;;
            --duration)
                TEST_DURATION="$2"
                shift 2
                ;;
            --memory-threshold)
                MEMORY_THRESHOLD_MB="$2"
                shift 2
                ;;
            --cpu-threshold)
                CPU_THRESHOLD_PERCENT="$2"
                shift 2
                ;;
            --report)
                GENERATE_REPORT=true
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

# 检查容器是否运行
check_container_running() {
    if ! docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
        error_msg "容器 ${CONTAINER_NAME} 未运行"
        exit 1
    fi
    
    success_msg "容器 ${CONTAINER_NAME} 运行正常"
}

# 获取容器资源使用情况
get_container_stats() {
    local stats=$(docker stats "${CONTAINER_NAME}" --no-stream --format "{{.CPUPerc}},{{.MemUsage}},{{.NetIO}},{{.BlockIO}}" 2>/dev/null || echo "0%,0B / 0B,0B / 0B,0B / 0B")
    echo "$stats"
}

# 解析内存使用 (返回MB)
parse_memory_usage() {
    local mem_usage="$1"
    local mem_value=$(echo "$mem_usage" | cut -d'/' -f1 | sed 's/[^0-9.]//g')
    local mem_unit=$(echo "$mem_usage" | cut -d'/' -f1 | sed 's/[0-9.]//g' | tr -d ' ')
    
    case "$mem_unit" in
        "GiB"|"GB")
            echo "$(echo "$mem_value * 1024" | bc 2>/dev/null || echo "0")"
            ;;
        "MiB"|"MB")
            echo "${mem_value%.*}"
            ;;
        "KiB"|"KB")
            echo "$(echo "$mem_value / 1024" | bc 2>/dev/null || echo "0")"
            ;;
        *)
            echo "0"
            ;;
    esac
}

# 基准性能测试
test_baseline_performance() {
    info_msg "执行基准性能测试..."
    
    # 获取初始资源使用情况
    local initial_stats=$(get_container_stats)
    IFS=',' read -r initial_cpu initial_mem initial_net initial_block <<< "$initial_stats"
    
    info_msg "初始状态 - CPU: $initial_cpu, 内存: $initial_mem"
    
    # 数据库查询性能测试
    info_msg "测试数据库查询性能..."
    local start_time=$(date +%s%N)
    
    for i in {1..10}; do
        docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) FROM memories;" >/dev/null 2>&1
    done
    
    local end_time=$(date +%s%N)
    local avg_query_time=$(((end_time - start_time) / 10000000))  # 平均查询时间(毫秒)
    
    info_msg "平均数据库查询时间: ${avg_query_time}ms"
    
    if [ "$avg_query_time" -gt 100 ]; then
        warning_msg "数据库查询性能较慢"
    else
        success_msg "数据库查询性能良好"
    fi
    
    return 0
}

# MCP协议响应时间测试
test_mcp_response_time() {
    info_msg "测试MCP协议响应时间..."
    
    local total_time=0
    local successful_requests=0
    local failed_requests=0
    
    for i in {1..10}; do
        local start_time=$(date +%s%N)
        
        local response=$(echo '{"jsonrpc": "2.0", "id": '$i', "method": "tools/call", "params": {"name": "get_status", "arguments": {}}}' | \
            timeout 5 docker exec -i "${CONTAINER_NAME}" python3 /app/sage_mcp_stdio_single.py 2>/dev/null || echo "")
        
        local end_time=$(date +%s%N)
        local request_time=$((end_time - start_time))
        
        if [ -n "$response" ] && echo "$response" | grep -q "jsonrpc"; then
            total_time=$((total_time + request_time))
            ((successful_requests++))
        else
            ((failed_requests++))
        fi
    done
    
    if [ $successful_requests -gt 0 ]; then
        local avg_response_time=$((total_time / successful_requests / 1000000))  # 转换为毫秒
        info_msg "MCP平均响应时间: ${avg_response_time}ms (成功: $successful_requests, 失败: $failed_requests)"
        
        if [ "$avg_response_time" -gt 1000 ]; then
            warning_msg "MCP响应时间较慢"
        else
            success_msg "MCP响应时间良好"
        fi
    else
        error_msg "所有MCP请求都失败了"
        return 1
    fi
    
    return 0
}

# 并发处理能力测试
test_concurrent_processing() {
    info_msg "测试并发处理能力 (${CONCURRENT_REQUESTS}个并发请求)..."
    
    # 创建临时脚本用于并发测试
    local temp_script="/tmp/mcp_concurrent_test.sh"
    
    cat > "$temp_script" << 'EOF'
#!/bin/bash
CONTAINER_NAME="$1"
REQUEST_ID="$2"

start_time=$(date +%s%N)
response=$(echo '{"jsonrpc": "2.0", "id": '$REQUEST_ID', "method": "tools/call", "params": {"name": "get_status", "arguments": {}}}' | \
    timeout 10 docker exec -i "${CONTAINER_NAME}" python3 /app/sage_mcp_stdio_single.py 2>/dev/null || echo "")
end_time=$(date +%s%N)

request_time=$((end_time - start_time))

if [ -n "$response" ] && echo "$response" | grep -q "jsonrpc"; then
    echo "SUCCESS:$request_time"
else
    echo "FAILED:$request_time"
fi
EOF
    
    chmod +x "$temp_script"
    
    # 启动并发请求
    local pids=()
    local results_file="/tmp/concurrent_results.txt"
    rm -f "$results_file"
    
    for i in $(seq 1 $CONCURRENT_REQUESTS); do
        "$temp_script" "$CONTAINER_NAME" "$i" >> "$results_file" &
        pids+=($!)
    done
    
    # 等待所有请求完成
    for pid in "${pids[@]}"; do
        wait "$pid"
    done
    
    # 分析结果
    local successful_concurrent=$(grep "SUCCESS" "$results_file" | wc -l)
    local failed_concurrent=$(grep "FAILED" "$results_file" | wc -l)
    
    if [ -f "$results_file" ] && [ $successful_concurrent -gt 0 ]; then
        local avg_concurrent_time=$(grep "SUCCESS" "$results_file" | cut -d':' -f2 | awk '{sum+=$1} END {print int(sum/NR/1000000)}')
        info_msg "并发测试结果: 成功 $successful_concurrent, 失败 $failed_concurrent, 平均响应时间 ${avg_concurrent_time}ms"
        
        local success_rate=$((successful_concurrent * 100 / CONCURRENT_REQUESTS))
        if [ $success_rate -ge 80 ]; then
            success_msg "并发处理能力良好 (成功率: ${success_rate}%)"
        else
            warning_msg "并发处理能力需要改进 (成功率: ${success_rate}%)"
        fi
    else
        error_msg "并发测试失败"
        return 1
    fi
    
    # 清理临时文件
    rm -f "$temp_script" "$results_file"
    
    return 0
}

# 资源使用监控
monitor_resource_usage() {
    info_msg "监控资源使用情况 (${TEST_DURATION}秒)..."
    
    local monitor_log="/tmp/resource_monitor.log"
    rm -f "$monitor_log"
    
    # 后台监控进程
    (
        for i in $(seq 1 $TEST_DURATION); do
            local stats=$(get_container_stats)
            echo "$(date +%s),$stats" >> "$monitor_log"
            sleep 1
        done
    ) &
    
    local monitor_pid=$!
    
    # 在监控期间执行一些操作
    info_msg "执行负载操作..."
    for i in {1..20}; do
        # 执行一些数据库操作
        docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -c "
            INSERT INTO memories (user_input, assistant_response, metadata) 
            VALUES ('性能测试输入$i', '性能测试响应$i', '{\"test\": true}');
        " >/dev/null 2>&1 || true
        
        # 执行MCP请求
        echo '{"jsonrpc": "2.0", "id": '$i', "method": "tools/call", "params": {"name": "get_status", "arguments": {}}}' | \
            docker exec -i "${CONTAINER_NAME}" python3 /app/sage_mcp_stdio_single.py >/dev/null 2>&1 || true
        
        sleep 1
    done
    
    # 等待监控完成
    wait "$monitor_pid"
    
    # 分析监控数据
    if [ -f "$monitor_log" ]; then
        local max_cpu=$(cut -d',' -f2 "$monitor_log" | sed 's/%//' | sort -nr | head -1 | cut -d'.' -f1)
        local max_mem_usage=$(cut -d',' -f3 "$monitor_log" | while read line; do parse_memory_usage "$line"; done | sort -nr | head -1)
        
        info_msg "峰值CPU使用率: ${max_cpu}%"
        info_msg "峰值内存使用: ${max_mem_usage}MB"
        
        # 检查是否超过阈值
        if [ "$max_cpu" -gt "$CPU_THRESHOLD_PERCENT" ]; then
            warning_msg "CPU使用率超过阈值 (${max_cpu}% > ${CPU_THRESHOLD_PERCENT}%)"
        else
            success_msg "CPU使用率在正常范围内"
        fi
        
        if [ "$max_mem_usage" -gt "$MEMORY_THRESHOLD_MB" ]; then
            warning_msg "内存使用超过阈值 (${max_mem_usage}MB > ${MEMORY_THRESHOLD_MB}MB)"
        else
            success_msg "内存使用在正常范围内"
        fi
    fi
    
    # 清理监控数据
    rm -f "$monitor_log"
    
    return 0
}

# 内存泄露检测
test_memory_leak() {
    info_msg "执行内存泄露检测..."
    
    # 获取初始内存使用
    local initial_stats=$(get_container_stats)
    local initial_mem=$(echo "$initial_stats" | cut -d',' -f2)
    local initial_mem_mb=$(parse_memory_usage "$initial_mem")
    
    info_msg "初始内存使用: ${initial_mem_mb}MB"
    
    # 执行大量操作
    info_msg "执行大量操作以检测内存泄露..."
    for i in {1..100}; do
        # 保存一些测试数据
        echo '{"jsonrpc": "2.0", "id": '$i', "method": "tools/call", "params": {"name": "S", "arguments": {"user_prompt": "泄露测试'$i'", "assistant_response": "响应'$i'"}}}' | \
            docker exec -i "${CONTAINER_NAME}" python3 /app/sage_mcp_stdio_single.py >/dev/null 2>&1 || true
        
        if [ $((i % 20)) -eq 0 ]; then
            info_msg "已完成 $i/100 操作..."
        fi
    done
    
    # 等待一段时间让系统稳定
    sleep 5
    
    # 获取最终内存使用
    local final_stats=$(get_container_stats)
    local final_mem=$(echo "$final_stats" | cut -d',' -f2)
    local final_mem_mb=$(parse_memory_usage "$final_mem")
    
    info_msg "最终内存使用: ${final_mem_mb}MB"
    
    local mem_increase=$((final_mem_mb - initial_mem_mb))
    info_msg "内存增长: ${mem_increase}MB"
    
    if [ "$mem_increase" -gt 100 ]; then
        warning_msg "可能存在内存泄露 (增长${mem_increase}MB)"
    else
        success_msg "未检测到明显的内存泄露"
    fi
    
    # 清理测试数据
    docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -c "
        DELETE FROM memories WHERE user_input LIKE '泄露测试%';
    " >/dev/null 2>&1 || true
    
    return 0
}

# 生成性能报告
generate_performance_report() {
    if [ "$GENERATE_REPORT" = false ]; then
        return
    fi
    
    info_msg "生成性能测试报告..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="$PROJECT_ROOT/backups/performance_report_${timestamp}.txt"
    
    mkdir -p "$PROJECT_ROOT/backups"
    
    local current_stats=$(get_container_stats)
    IFS=',' read -r cpu_usage mem_usage net_io block_io <<< "$current_stats"
    
    cat > "$report_file" << EOF
Sage MCP 性能测试报告
====================

测试时间: $(date)
容器名称: $CONTAINER_NAME
测试参数:
- 并发请求数: $CONCURRENT_REQUESTS
- 测试持续时间: ${TEST_DURATION}秒
- 内存阈值: ${MEMORY_THRESHOLD_MB}MB
- CPU阈值: ${CPU_THRESHOLD_PERCENT}%

=== 当前资源使用情况 ===
CPU使用率: $cpu_usage
内存使用: $mem_usage
网络IO: $net_io
磁盘IO: $block_io

=== 数据库性能指标 ===
$(docker exec "${CONTAINER_NAME}" psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_rows
FROM pg_stat_user_tables;" 2>/dev/null || echo "无法获取数据库统计信息")

=== 进程信息 ===
$(docker exec "${CONTAINER_NAME}" ps aux --sort=-%cpu | head -10 2>/dev/null || echo "无法获取进程信息")

=== 系统负载 ===
$(docker exec "${CONTAINER_NAME}" uptime 2>/dev/null || echo "无法获取系统负载")

=== 内存详情 ===
$(docker exec "${CONTAINER_NAME}" free -h 2>/dev/null || echo "无法获取内存信息")

=== 磁盘使用 ===
$(docker exec "${CONTAINER_NAME}" df -h 2>/dev/null || echo "无法获取磁盘信息")

测试完成时间: $(date)
EOF
    
    success_msg "性能报告已生成: $report_file"
}

# 主执行流程
main() {
    echo "=========================================="
    echo "Sage MCP 性能测试工具"
    echo "=========================================="
    
    parse_arguments "$@"
    
    info_msg "开始性能测试 - 容器: $CONTAINER_NAME"
    info_msg "测试参数: 并发${CONCURRENT_REQUESTS}, 持续${TEST_DURATION}秒"
    
    check_container_running
    
    # 执行所有性能测试
    test_baseline_performance
    test_mcp_response_time
    test_concurrent_processing
    monitor_resource_usage
    test_memory_leak
    
    generate_performance_report
    
    echo "=========================================="
    success_msg "性能测试完成"
    echo "=========================================="
}

# 执行主流程
main "$@"