@echo off
REM Sage MCP Database Backup Script - Windows版本
REM 备份PostgreSQL数据库

setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0.."
set "BACKUP_DIR=%PROJECT_ROOT%\backups"
set "TIMESTAMP=%date:~0,4%-%date:~5,2%-%date:~8,2%_%time:~0,2%-%time:~3,2%-%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"
set "BACKUP_FILE=%BACKUP_DIR%\sage_memory_backup_%TIMESTAMP%.sql"

echo ====================================
echo Sage MCP 数据库备份
echo ====================================

REM 创建备份目录
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM 检查数据库容器
echo 检查数据库容器状态...
docker ps | findstr "sage-db.*Up" >nul
if %errorlevel% neq 0 (
    echo ❌ PostgreSQL容器未运行，无法备份
    exit /b 1
)

REM 执行备份
echo 开始备份数据库...
docker exec sage-db pg_dump -U sage -d sage_memory > "%BACKUP_FILE%"
if %errorlevel% neq 0 (
    echo ❌ 备份失败
    exit /b 1
)

echo ✅ 备份完成
echo 备份文件: %BACKUP_FILE%

REM 显示备份文件大小
for %%i in ("%BACKUP_FILE%") do set "SIZE=%%~zi"
echo 文件大小: %SIZE% 字节

echo ====================================
echo 🎉 数据库备份成功完成
echo ====================================