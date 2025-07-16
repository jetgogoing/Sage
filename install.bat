@echo off
:: Sage MCP Windows 安装脚本
:: 支持 Windows 10/11
:: 编码: UTF-8

setlocal enabledelayedexpansion

echo === Sage MCP Claude 记忆系统安装程序 (Windows) ===
echo.

:: 1. 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [错误] 请以管理员身份运行此脚本
    echo 右键点击脚本，选择"以管理员身份运行"
    pause
    exit /b 1
)

:: 2. 检查 Python 安装
echo [1/7] 检查 Python 环境...
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.7+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 获取 Python 版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo    找到 Python %PYTHON_VERSION%

:: 3. 检查 Claude CLI
echo [2/7] 检查 Claude CLI...
set CLAUDE_FOUND=0
set CLAUDE_PATH=

:: 检查常见位置
for %%p in (
    "%LOCALAPPDATA%\Claude\claude.exe"
    "%PROGRAMFILES%\Claude\claude.exe"
    "%PROGRAMFILES(x86)%\Claude\claude.exe"
    "%USERPROFILE%\AppData\Local\Programs\claude\claude.exe"
) do (
    if exist "%%~p" (
        set CLAUDE_PATH=%%~p
        set CLAUDE_FOUND=1
        goto :claude_found
    )
)

:: 检查 PATH
where claude.exe >nul 2>&1
if %errorLevel% equ 0 (
    for /f "delims=" %%i in ('where claude.exe') do set CLAUDE_PATH=%%i
    set CLAUDE_FOUND=1
)

:claude_found
if %CLAUDE_FOUND% equ 0 (
    echo [错误] 未找到 Claude CLI
    echo 请先安装 Claude Desktop: https://claude.ai/download
    pause
    exit /b 1
)

echo    找到 Claude: %CLAUDE_PATH%

:: 4. 获取 Sage 项目路径
set SAGE_PATH=%~dp0
:: 移除末尾的反斜杠
if "%SAGE_PATH:~-1%"=="\" set SAGE_PATH=%SAGE_PATH:~0,-1%
echo [3/7] Sage 项目路径: %SAGE_PATH%

:: 5. 创建配置目录
echo [4/7] 创建配置目录...
set CONFIG_DIR=%USERPROFILE%\.sage-mcp
if not exist "%CONFIG_DIR%" (
    mkdir "%CONFIG_DIR%"
    echo    创建目录: %CONFIG_DIR%
)

if not exist "%CONFIG_DIR%\logs" (
    mkdir "%CONFIG_DIR%\logs"
    echo    创建目录: %CONFIG_DIR%\logs
)

:: 6. 生成配置文件
echo [5/7] 生成配置文件...
set CONFIG_FILE=%CONFIG_DIR%\config.json

(
echo {
echo   "claude_paths": ["%CLAUDE_PATH:\=\\%"],
echo   "memory_enabled": true,
echo   "debug_mode": false,
echo   "platform": "windows"
echo }
) > "%CONFIG_FILE%"

echo    配置已保存: %CONFIG_FILE%

:: 7. 创建包装脚本
echo [6/7] 创建 Claude 包装器...
set WRAPPER_DIR=%USERPROFILE%\.sage-mcp\bin
if not exist "%WRAPPER_DIR%" mkdir "%WRAPPER_DIR%"

:: 创建 claude.bat
set WRAPPER_BAT=%WRAPPER_DIR%\claude.bat
(
echo @echo off
echo :: Sage MCP Claude 包装器 - Windows
echo :: 自动生成于 %date% %time%
echo.
echo :: Python 路径
echo set PYTHON_PATH=python
echo.
echo :: 记忆脚本路径
echo set MEMORY_SCRIPT=%SAGE_PATH%\claude_mem_crossplatform.py
echo.
echo :: 执行跨平台脚本
echo "%%PYTHON_PATH%%" "%%MEMORY_SCRIPT%%" %%*
) > "%WRAPPER_BAT%"

echo    包装器已创建: %WRAPPER_BAT%

:: 创建 PowerShell 包装器
set WRAPPER_PS1=%WRAPPER_DIR%\claude.ps1
(
echo # Sage MCP Claude 包装器 - PowerShell
echo # 自动生成于 %date% %time%
echo.
echo $pythonPath = "python"
echo $memoryScript = "%SAGE_PATH%\claude_mem_crossplatform.py"
echo.
echo ^& $pythonPath $memoryScript $args
) > "%WRAPPER_PS1%"

:: 8. 设置环境变量
echo [7/7] 配置环境变量...

:: 检查 PATH 中是否已包含包装器目录
echo %PATH% | findstr /C:"%WRAPPER_DIR%" >nul
if %errorLevel% neq 0 (
    :: 添加到用户 PATH
    setx PATH "%PATH%;%WRAPPER_DIR%"
    echo    已添加到 PATH: %WRAPPER_DIR%
) else (
    echo    PATH 已包含: %WRAPPER_DIR%
)

:: 设置 Sage 环境变量
setx SAGE_MCP_HOME "%SAGE_PATH%"
setx SAGE_CONFIG_DIR "%CONFIG_DIR%"

:: 9. 安装 Python 依赖
echo.
echo === 安装 Python 依赖 ===
cd /d "%SAGE_PATH%"
python -m pip install -r requirements.txt

if %errorLevel% neq 0 (
    echo [警告] 依赖安装失败，请手动运行:
    echo    cd /d "%SAGE_PATH%"
    echo    pip install -r requirements.txt
)

:: 10. 创建控制命令
echo.
echo === 创建控制命令 ===

:: sage-mode.bat
set SAGE_MODE_BAT=%WRAPPER_DIR%\sage-mode.bat
(
echo @echo off
echo :: Sage 模式控制命令
echo.
echo if "%%1"=="on" (
echo     set SAGE_MEMORY_ENABLED=1
echo     echo Sage 记忆模式：已启用
echo ^) else if "%%1"=="off" (
echo     set SAGE_MEMORY_ENABLED=0
echo     echo Sage 记忆模式：已禁用
echo ^) else if "%%1"=="status" (
echo     if "%%SAGE_MEMORY_ENABLED%%"=="0" (
echo         echo Sage 记忆模式：禁用
echo     ^) else (
echo         echo Sage 记忆模式：启用
echo     ^)
echo ^) else (
echo     echo 用法: sage-mode [on^|off^|status]
echo ^)
) > "%SAGE_MODE_BAT%"

:: 11. 完成安装
echo.
echo === 安装完成！===
echo.
echo 使用说明：
echo 1. 重新打开命令提示符或 PowerShell
echo 2. 使用命令: claude "你的问题"
echo 3. 控制记忆模式:
echo    - sage-mode on     # 启用记忆
echo    - sage-mode off    # 禁用记忆
echo    - sage-mode status # 查看状态
echo.
echo 4. 原始 Claude 路径:
echo    "%CLAUDE_PATH%"
echo.
echo 提示：如果 claude 命令不可用，请重启电脑或手动刷新环境变量
echo.
pause