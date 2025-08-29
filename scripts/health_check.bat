@echo off
REM Sage MCP Health Check Script - Windows版本
REM 检查Sage MCP服务和数据库的健康状态

setlocal enabledelayedexpansion

echo ====================================
echo Sage MCP 健康检查
echo ====================================

REM 检查Docker
echo [1/5] 检查Docker状态...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker未运行或未安装
    exit /b 1
) else (
    echo ✅ Docker运行正常
)

REM 检查数据库容器
echo [2/5] 检查数据库容器...
docker ps | findstr "sage-db.*Up" >nul
if %errorlevel% neq 0 (
    echo ❌ PostgreSQL容器未运行
    exit /b 1
) else (
    echo ✅ PostgreSQL容器运行正常
)

REM 检查数据库连接
echo [3/5] 检查数据库连接...
docker exec sage-db pg_isready -U sage -d sage_memory >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 数据库连接失败
    exit /b 1
) else (
    echo ✅ 数据库连接正常
)

REM 检查端口
echo [4/5] 检查端口占用...
netstat -an | findstr ":5432" >nul
if %errorlevel% neq 0 (
    echo ❌ 端口5432未监听
    exit /b 1
) else (
    echo ✅ 端口5432正常监听
)

REM 检查日志目录
echo [5/5] 检查日志目录...
set "PROJECT_ROOT=%~dp0.."
if not exist "%PROJECT_ROOT%\logs" (
    echo ❌ 日志目录不存在
    exit /b 1
) else (
    echo ✅ 日志目录存在
)

echo ====================================
echo 🎉 所有检查通过！Sage MCP服务健康
echo ====================================