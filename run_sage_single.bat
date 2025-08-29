@echo off
REM Sage MCP Single Container Launch Script
REM For Windows

REM Default image name
if "%SAGE_IMAGE%"=="" set SAGE_IMAGE=sage-mcp-single:latest

REM Check if Docker is installed
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Docker is not installed or not in PATH >&2
    exit /b 1
)

REM Check if Docker daemon is running
docker info >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Docker daemon is not running >&2
    exit /b 1
)

REM Run the container
REM -i: Keep STDIN open (required for MCP STDIO)
REM --rm: Remove container after exit
docker run --rm -i ^
    --name sage-mcp-stdio ^
    %SAGE_DOCKER_OPTS% ^
    "%SAGE_IMAGE%"