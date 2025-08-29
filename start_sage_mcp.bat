@echo off
REM Sage MCP Startup Script - Windows版本
REM 此脚本确保pgvector数据库运行并启动Sage MCP服务

setlocal enabledelayedexpansion

REM 动态检测项目根目录，支持跨平台部署
set "SAGE_HOME=%~dp0"
set "SAGE_HOME=%SAGE_HOME:~0,-1%"
set "DB_COMPOSE_FILE=%SAGE_HOME%\docker-compose-db.yml"
set "SAGE_LOGS=%SAGE_HOME%\logs"

REM 创建日志目录
if not exist "%SAGE_LOGS%" mkdir "%SAGE_LOGS%"

REM 检查Docker是否运行
echo 检查Docker环境... >&2
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker未运行，请先启动Docker Desktop >&2
    exit /b 1
)

REM 检查PostgreSQL容器是否存在
docker ps -a | findstr "sage-db" >nul
if %errorlevel% neq 0 (
    echo 创建PostgreSQL容器... >&2
    cd /d "%SAGE_HOME%"
    docker-compose -f "%DB_COMPOSE_FILE%" up -d
    timeout /t 5 >nul
) else (
    REM 检查容器是否运行中
    docker ps | findstr "sage-db.*Up" >nul
    if %errorlevel% neq 0 (
        echo 启动现有PostgreSQL容器... >&2
        docker start sage-db
        timeout /t 3 >nul
    )
)

REM 等待PostgreSQL就绪
echo 检查PostgreSQL就绪状态... >&2
for /l %%i in (1,1,30) do (
    docker exec sage-db pg_isready -U sage -d sage_memory >nul 2>&1
    if !errorlevel! equ 0 (
        echo PostgreSQL已就绪! >&2
        goto :database_ready
    )
    timeout /t 1 >nul
)
echo PostgreSQL在30秒内未就绪 >&2
exit /b 1

:database_ready

REM 导出环境变量（可以从.env文件或环境变量覆盖）
set "SAGE_LOG_DIR=%SAGE_LOGS%"
if "%DB_HOST%"=="" set "DB_HOST=localhost"
if "%DB_PORT%"=="" set "DB_PORT=5432"
if "%DB_NAME%"=="" set "DB_NAME=sage_memory"
if "%DB_USER%"=="" set "DB_USER=sage"
if "%DB_PASSWORD%"=="" set "DB_PASSWORD="
set "EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B"
set "EMBEDDING_DEVICE=cpu"
REM API密钥从环境变量或.env文件加载，移除明文密钥以提高安全性
if "%SILICONFLOW_API_KEY%"=="" set "SILICONFLOW_API_KEY="
set "PYTHONPATH=%SAGE_HOME%"

REM 安全地加载.env文件中的配置
if exist "%SAGE_HOME%\.env" (
    for /f "usebackq tokens=1,2 delims==" %%a in ("%SAGE_HOME%\.env") do (
        REM 跳过注释行和空行
        echo %%a | findstr /r "^[[:space:]]*#" >nul && goto :skip_line
        if "%%a"=="" goto :skip_line
        
        REM 安全地设置已知配置变量
        if /i "%%a"=="SAGE_MAX_RESULTS" set "SAGE_MAX_RESULTS=%%b"
        if /i "%%a"=="SAGE_SIMILARITY_THRESHOLD" set "SAGE_SIMILARITY_THRESHOLD=%%b"
        if /i "%%a"=="SILICONFLOW_API_KEY" set "SILICONFLOW_API_KEY=%%b"
        if /i "%%a"=="DB_PASSWORD" set "DB_PASSWORD=%%b"
        
        :skip_line
    )
)

REM 使用当前Python解释器或项目虚拟环境
set "PYTHON_EXE=%SAGE_HOME%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

REM 启动Sage MCP服务
"%PYTHON_EXE%" "%SAGE_HOME%\sage_mcp_stdio_single.py"