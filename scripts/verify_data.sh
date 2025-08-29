#!/bin/bash
# Sage MCP 数据验证脚本
# 验证数据库完整性和数据一致性

set -euo pipefail

# 配置参数
CONTAINER_NAME="sage-mcp"
DB_NAME="${DB_NAME:-sage_memory}"
DB_USER="${DB_USER:-sage}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 错误处理函数
error_exit() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
    exit 1
}

# 成功信息
success_msg() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

# 警告信息
warning_msg() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
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
  -h, --help          显示此帮助信息
  -c, --container     指定容器名称 (默认: ${CONTAINER_NAME})
  -d, --database      指定数据库名称 (默认: ${DB_NAME})
  -u, --user          指定数据库用户 (默认: ${DB_USER})
  --quick            快速检查（跳过详细数据验证）
  --report           生成详细报告文件

验证项目:
  1. 容器和数据库连接状态
  2. 表结构完整性
  3. 索引状态
  4. 数据一致性
  5. pgvector扩展功能
  6. 权限配置
  7. 性能指标
EOF
}

# 解析命令行参数
parse_arguments() {
    QUICK_MODE=false
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
            -d|--database)
                DB_NAME="$2"
                shift 2
                ;;
            -u|--user)
                DB_USER="$2"
                shift 2
                ;;
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --report)
                GENERATE_REPORT=true
                shift
                ;;
            -*)
                error_exit "未知选项: $1"
                ;;
            *)
                error_exit "未知参数: $1"
                ;;
        esac
    done
}

# 检查Docker容器状态
check_container_status() {
    info_msg "检查容器状态..."
    
    if ! docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
        error_exit "容器 ${CONTAINER_NAME} 未运行"
    fi
    
    # 检查容器健康状态
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "none")
    if [ "$health_status" = "healthy" ]; then
        success_msg "容器健康状态: $health_status"
    elif [ "$health_status" = "none" ]; then
        warning_msg "容器未配置健康检查"
    else
        warning_msg "容器健康状态: $health_status"
    fi
    
    success_msg "容器 ${CONTAINER_NAME} 运行正常"
}

# 检查数据库连接
check_database_connection() {
    info_msg "检查数据库连接..."
    
    # 检查PostgreSQL进程
    if ! docker exec "${CONTAINER_NAME}" pgrep postgres >/dev/null 2>&1; then
        error_exit "PostgreSQL进程未运行"
    fi
    
    # 检查数据库连接
    if ! docker exec "${CONTAINER_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
        error_exit "数据库连接失败"
    fi
    
    # 测试实际查询
    local version=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT version();" 2>/dev/null | head -1 | tr -d ' \n' || echo "unknown")
    info_msg "PostgreSQL版本: ${version:0:50}..."
    
    success_msg "数据库连接正常"
}

# 检查pgvector扩展
check_pgvector_extension() {
    info_msg "检查pgvector扩展..."
    
    local extension_exists=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');
    " 2>/dev/null | tr -d ' \n' || echo "f")
    
    if [ "$extension_exists" = "t" ]; then
        success_msg "pgvector扩展已安装"
        
        # 测试向量操作
        local vector_test=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
            SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector as distance;
        " 2>/dev/null | tr -d ' \n' || echo "error")
        
        if [ "$vector_test" != "error" ] && [ -n "$vector_test" ]; then
            success_msg "向量操作测试通过 (距离: $vector_test)"
        else
            warning_msg "向量操作测试失败"
        fi
    else
        error_exit "pgvector扩展未安装"
    fi
}

# 检查表结构
check_table_structure() {
    info_msg "检查表结构..."
    
    # 检查必需的表
    local required_tables=("memories" "sessions")
    
    for table in "${required_tables[@]}"; do
        local table_exists=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = '$table'
            );
        " 2>/dev/null | tr -d ' \n' || echo "f")
        
        if [ "$table_exists" = "t" ]; then
            success_msg "表 '$table' 存在"
            
            # 检查表行数
            local row_count=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
                SELECT COUNT(*) FROM $table;
            " 2>/dev/null | tr -d ' \n' || echo "0")
            info_msg "表 '$table' 行数: $row_count"
            
        else
            error_exit "缺少必需的表: $table"
        fi
    done
    
    # 检查memories表的vector列
    local vector_column_exists=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'memories' 
            AND column_name = 'embedding'
            AND data_type = 'USER-DEFINED'
        );
    " 2>/dev/null | tr -d ' \n' || echo "f")
    
    if [ "$vector_column_exists" = "t" ]; then
        success_msg "memories表的embedding向量列存在"
    else
        error_exit "memories表缺少embedding向量列"
    fi
}

# 检查索引状态
check_indexes() {
    info_msg "检查索引状态..."
    
    # 获取所有索引信息
    local index_info=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
        SELECT 
            schemaname,
            tablename,
            indexname,
            indexdef
        FROM pg_indexes 
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname;
    " 2>/dev/null || echo "无法获取索引信息")
    
    echo "$index_info"
    
    # 检查必需的索引
    local required_indexes=(
        "idx_memories_session_id"
        "idx_memories_created_at"
        "idx_sessions_last_active"
    )
    
    for index in "${required_indexes[@]}"; do
        local index_exists=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
            SELECT EXISTS (
                SELECT FROM pg_indexes
                WHERE schemaname = 'public'
                AND indexname = '$index'
            );
        " 2>/dev/null | tr -d ' \n' || echo "f")
        
        if [ "$index_exists" = "t" ]; then
            success_msg "索引 '$index' 存在"
        else
            warning_msg "建议的索引 '$index' 不存在"
        fi
    done
}

# 检查数据一致性
check_data_consistency() {
    if [ "$QUICK_MODE" = true ]; then
        info_msg "快速模式：跳过数据一致性检查"
        return
    fi
    
    info_msg "检查数据一致性..."
    
    # 检查外键约束
    local fk_violations=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT COUNT(*) FROM memories m 
        WHERE m.session_id IS NOT NULL 
        AND NOT EXISTS (SELECT 1 FROM sessions s WHERE s.id = m.session_id);
    " 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$fk_violations" -eq 0 ]; then
        success_msg "外键约束检查通过"
    else
        warning_msg "发现 $fk_violations 个外键约束违反"
    fi
    
    # 检查NULL值
    local null_user_input=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT COUNT(*) FROM memories WHERE user_input IS NULL OR user_input = '';
    " 2>/dev/null | tr -d ' \n' || echo "0")
    
    local null_assistant_response=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT COUNT(*) FROM memories WHERE assistant_response IS NULL OR assistant_response = '';
    " 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$null_user_input" -eq 0 ] && [ "$null_assistant_response" -eq 0 ]; then
        success_msg "必填字段完整性检查通过"
    else
        warning_msg "发现空的必填字段: user_input($null_user_input), assistant_response($null_assistant_response)"
    fi
    
    # 检查向量数据完整性
    local vector_null_count=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT COUNT(*) FROM memories WHERE embedding IS NULL;
    " 2>/dev/null | tr -d ' \n' || echo "0")
    
    local total_memories=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT COUNT(*) FROM memories;
    " 2>/dev/null | tr -d ' \n' || echo "0")
    
    if [ "$total_memories" -gt 0 ]; then
        local vector_coverage=$((100 * (total_memories - vector_null_count) / total_memories))
        info_msg "向量化覆盖率: ${vector_coverage}% ($((total_memories - vector_null_count))/$total_memories)"
        
        if [ "$vector_coverage" -ge 90 ]; then
            success_msg "向量化覆盖率良好"
        elif [ "$vector_coverage" -ge 70 ]; then
            warning_msg "向量化覆盖率中等"
        else
            warning_msg "向量化覆盖率较低"
        fi
    fi
}

# 检查用户权限
check_user_permissions() {
    info_msg "检查用户权限..."
    
    # 检查表权限
    local table_privileges=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
        SELECT 
            table_name,
            privilege_type
        FROM information_schema.role_table_grants 
        WHERE grantee = '$DB_USER' 
        AND table_schema = 'public'
        ORDER BY table_name, privilege_type;
    " 2>/dev/null || echo "无法获取权限信息")
    
    if [ -n "$table_privileges" ] && [ "$table_privileges" != "无法获取权限信息" ]; then
        success_msg "用户权限配置正常"
        if [ "$GENERATE_REPORT" = true ]; then
            echo "用户权限详情:"
            echo "$table_privileges"
        fi
    else
        warning_msg "无法验证用户权限"
    fi
}

# 性能指标检查
check_performance_metrics() {
    info_msg "检查性能指标..."
    
    # 数据库大小
    local db_size=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT pg_size_pretty(pg_database_size('$DB_NAME'));
    " 2>/dev/null | tr -d ' \n' || echo "unknown")
    info_msg "数据库大小: $db_size"
    
    # 表大小
    local table_sizes=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
    " 2>/dev/null || echo "无法获取表大小信息")
    
    if [ -n "$table_sizes" ] && [ "$table_sizes" != "无法获取表大小信息" ]; then
        info_msg "表大小统计:"
        echo "$table_sizes"
    fi
    
    # 连接统计
    local connection_count=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "
        SELECT count(*) FROM pg_stat_activity WHERE datname = '$DB_NAME';
    " 2>/dev/null | tr -d ' \n' || echo "0")
    info_msg "当前连接数: $connection_count"
    
    success_msg "性能指标检查完成"
}

# 生成验证报告
generate_verification_report() {
    if [ "$GENERATE_REPORT" = false ]; then
        return
    fi
    
    info_msg "生成验证报告..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local report_file="./backups/verification_report_${timestamp}.txt"
    
    mkdir -p ./backups
    
    cat > "$report_file" << EOF
Sage MCP 数据验证报告
====================

验证时间: $(date)
容器名称: $CONTAINER_NAME
数据库名: $DB_NAME
数据库用户: $DB_USER
验证模式: $([ "$QUICK_MODE" = true ] && echo "快速模式" || echo "完整模式")

=== 基础信息 ===
PostgreSQL版本: $(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT version();" 2>/dev/null | head -1 || echo "unknown")
数据库大小: $(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" 2>/dev/null | tr -d ' \n' || echo "unknown")
当前连接数: $(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname = '$DB_NAME';" 2>/dev/null | tr -d ' \n' || echo "0")

=== 表统计 ===
$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
SELECT 
    schemaname,
    tablename,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_stat_user_tables 
ORDER BY n_live_tup DESC;" 2>/dev/null || echo "无法获取表统计信息")

=== 索引信息 ===
$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
ORDER BY idx_tup_read DESC;" 2>/dev/null || echo "无法获取索引信息")

=== 扩展信息 ===
$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
SELECT extname, extversion FROM pg_extension ORDER BY extname;" 2>/dev/null || echo "无法获取扩展信息")

验证状态: 完成
生成时间: $(date)
EOF
    
    success_msg "验证报告已生成: $report_file"
}

# 主执行流程
main() {
    echo "=========================================="
    echo "Sage MCP 数据验证工具"
    echo "=========================================="
    
    parse_arguments "$@"
    
    info_msg "开始验证 - 容器: $CONTAINER_NAME, 数据库: $DB_NAME"
    
    # 执行所有检查
    check_container_status
    check_database_connection
    check_pgvector_extension
    check_table_structure
    check_indexes
    check_data_consistency
    check_user_permissions
    check_performance_metrics
    
    generate_verification_report
    
    echo "=========================================="
    success_msg "数据验证完成!"
    echo "=========================================="
}

# 执行主流程
main "$@"