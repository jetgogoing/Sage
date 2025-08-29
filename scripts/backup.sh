#!/bin/bash
# Sage MCP 数据备份脚本
# 创建PostgreSQL数据库备份并保存到backups目录

set -euo pipefail

# 配置参数
CONTAINER_NAME="sage-mcp"
DB_NAME="${DB_NAME:-sage_memory}"
DB_USER="${DB_USER:-sage}"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/sage_backup_${TIMESTAMP}.sql"

# 错误处理函数
error_exit() {
    echo "[ERROR] $1" >&2
    exit 1
}

# 检查Docker容器状态
check_container() {
    echo "[INFO] 检查容器状态..."
    if ! docker ps -q -f name="${CONTAINER_NAME}" | grep -q .; then
        error_exit "容器 ${CONTAINER_NAME} 未运行"
    fi
    echo "[INFO] 容器状态正常"
}

# 检查数据库连接
check_database() {
    echo "[INFO] 检查数据库连接..."
    docker exec "${CONTAINER_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" || \
        error_exit "数据库连接失败"
    echo "[INFO] 数据库连接正常"
}

# 创建备份目录
prepare_backup_dir() {
    echo "[INFO] 准备备份目录..."
    mkdir -p "${BACKUP_DIR}"
    if [ ! -w "${BACKUP_DIR}" ]; then
        error_exit "备份目录 ${BACKUP_DIR} 不可写"
    fi
    echo "[INFO] 备份目录准备完成"
}

# 执行数据库备份
perform_backup() {
    echo "[INFO] 开始数据库备份..."
    echo "[INFO] 备份文件: ${BACKUP_FILE}"
    
    # 使用pg_dump创建备份
    docker exec "${CONTAINER_NAME}" pg_dump \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=custom \
        --no-owner \
        --no-privileges \
        --verbose \
        > "${BACKUP_FILE}.custom" 2>/dev/null || error_exit "自定义格式备份失败"
    
    # 创建SQL格式备份（便于查看）
    docker exec "${CONTAINER_NAME}" pg_dump \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --no-owner \
        --no-privileges \
        > "${BACKUP_FILE}" 2>/dev/null || error_exit "SQL格式备份失败"
    
    echo "[INFO] 数据库备份完成"
}

# 验证备份文件
verify_backup() {
    echo "[INFO] 验证备份文件..."
    
    if [ ! -f "${BACKUP_FILE}" ] || [ ! -s "${BACKUP_FILE}" ]; then
        error_exit "SQL备份文件创建失败或为空"
    fi
    
    if [ ! -f "${BACKUP_FILE}.custom" ] || [ ! -s "${BACKUP_FILE}.custom" ]; then
        error_exit "自定义格式备份文件创建失败或为空"
    fi
    
    # 检查文件大小
    local sql_size=$(stat -c%s "${BACKUP_FILE}" 2>/dev/null || stat -f%z "${BACKUP_FILE}")
    local custom_size=$(stat -c%s "${BACKUP_FILE}.custom" 2>/dev/null || stat -f%z "${BACKUP_FILE}.custom")
    
    echo "[INFO] SQL备份文件大小: ${sql_size} bytes"
    echo "[INFO] 自定义备份文件大小: ${custom_size} bytes"
    
    # 备份文件应该至少包含基本的表结构
    if ! grep -q "CREATE TABLE" "${BACKUP_FILE}"; then
        error_exit "备份文件不包含表结构，可能损坏"
    fi
    
    echo "[INFO] 备份文件验证通过"
}

# 清理旧备份（保留最近7天）
cleanup_old_backups() {
    echo "[INFO] 清理旧备份文件..."
    find "${BACKUP_DIR}" -name "sage_backup_*.sql*" -mtime +7 -delete 2>/dev/null || true
    echo "[INFO] 旧备份清理完成"
}

# 生成备份报告
generate_report() {
    echo "[INFO] 生成备份报告..."
    
    local report_file="${BACKUP_DIR}/backup_report_${TIMESTAMP}.txt"
    
    cat > "${report_file}" << EOF
Sage MCP 数据备份报告
====================

备份时间: $(date)
容器名称: ${CONTAINER_NAME}
数据库名: ${DB_NAME}
数据库用户: ${DB_USER}

备份文件:
- SQL格式: ${BACKUP_FILE}
- 自定义格式: ${BACKUP_FILE}.custom

文件大小:
- SQL格式: $(stat -c%s "${BACKUP_FILE}" 2>/dev/null || stat -f%z "${BACKUP_FILE}") bytes
- 自定义格式: $(stat -c%s "${BACKUP_FILE}.custom" 2>/dev/null || stat -f%z "${BACKUP_FILE}.custom") bytes

数据库统计:
$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes
FROM pg_stat_user_tables;" 2>/dev/null || echo "无法获取统计信息")

备份状态: 成功
EOF
    
    echo "[INFO] 备份报告已生成: ${report_file}"
}

# 主执行流程
main() {
    echo "[INFO] Sage MCP 数据备份开始..."
    echo "[INFO] 时间戳: ${TIMESTAMP}"
    
    check_container
    check_database
    prepare_backup_dir
    perform_backup
    verify_backup
    cleanup_old_backups
    generate_report
    
    echo "[INFO] ====================================="
    echo "[INFO] 备份完成!"
    echo "[INFO] SQL备份文件: ${BACKUP_FILE}"
    echo "[INFO] 自定义备份文件: ${BACKUP_FILE}.custom"
    echo "[INFO] ====================================="
}

# 执行主流程
main "$@"