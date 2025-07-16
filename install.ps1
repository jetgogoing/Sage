# Sage MCP 高级安装脚本 (PowerShell)
# 要求: PowerShell 5.0+ (Windows 10/11 默认版本)
# 执行策略: 运行前可能需要执行 Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

param(
    [switch]$Silent = $false,
    [switch]$SkipDependencies = $false,
    [switch]$Force = $false
)

# 设置严格模式
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# 颜色定义
$Colors = @{
    Success = "Green"
    Error = "Red"
    Warning = "Yellow"
    Info = "Cyan"
    Header = "Magenta"
}

# 辅助函数
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White",
        [switch]$NoNewline
    )
    Write-Host $Message -ForegroundColor $Color -NoNewline:$NoNewline
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Show-Progress {
    param(
        [int]$Step,
        [int]$Total,
        [string]$Activity
    )
    $percent = ($Step / $Total) * 100
    Write-Progress -Activity "Sage MCP 安装进度" -Status $Activity -PercentComplete $percent
}

# 主安装流程
try {
    # 显示头部
    Clear-Host
    Write-ColorOutput "╔══════════════════════════════════════════════════╗" $Colors.Header
    Write-ColorOutput "║     Sage MCP Claude 记忆系统安装程序 (高级版)     ║" $Colors.Header
    Write-ColorOutput "╚══════════════════════════════════════════════════╝" $Colors.Header
    Write-Host ""
    Write-ColorOutput "版本: 2.0 | 平台: Windows | 模式: PowerShell" $Colors.Info
    Write-Host ""

    # 步骤计数
    $totalSteps = 10
    $currentStep = 0

    # 1. 检查管理员权限（可选）
    $currentStep++
    Show-Progress -Step $currentStep -Total $totalSteps -Activity "检查权限..."
    
    if (-not (Test-Administrator)) {
        Write-ColorOutput "[!] " $Colors.Warning -NoNewline
        Write-Host "当前未以管理员身份运行，某些功能可能受限"
        
        if (-not $Force) {
            $response = Read-Host "是否继续? (Y/N)"
            if ($response -ne 'Y' -and $response -ne 'y') {
                Write-ColorOutput "[X] 安装已取消" $Colors.Error
                exit 1
            }
        }
    } else {
        Write-ColorOutput "[✓] " $Colors.Success -NoNewline
        Write-Host "管理员权限已确认"
    }

    # 2. 检查 Python
    $currentStep++
    Show-Progress -Step $currentStep -Total $totalSteps -Activity "检查 Python 环境..."
    
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        throw "未找到 Python，请先安装 Python 3.7+"
    }
    
    $pythonVersion = & python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $majorVersion = [int]$matches[1]
        $minorVersion = [int]$matches[2]
        
        if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 7)) {
            throw "Python 版本过低 ($pythonVersion)，需要 3.7+"
        }
    }
    
    Write-ColorOutput "[✓] " $Colors.Success -NoNewline
    Write-Host "Python 环境: $pythonVersion"

    # 3. 检查 Claude CLI
    $currentStep++
    Show-Progress -Step $currentStep -Total $totalSteps -Activity "搜索 Claude CLI..."
    
    $claudePaths = @(
        "$env:LOCALAPPDATA\Claude\claude.exe",
        "$env:PROGRAMFILES\Claude\claude.exe",
        "${env:ProgramFiles(x86)}\Claude\claude.exe",
        "$env:USERPROFILE\AppData\Local\Programs\claude\claude.exe"
    )
    
    $claudePath = $null
    foreach ($path in $claudePaths) {
        if (Test-Path $path) {
            $claudePath = $path
            break
        }
    }
    
    if (-not $claudePath) {
        $claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
        if ($claudeCmd) {
            $claudePath = $claudeCmd.Source
        }
    }
    
    if (-not $claudePath) {
        Write-ColorOutput "[X] " $Colors.Error -NoNewline
        Write-Host "未找到 Claude CLI"
        Write-Host "请访问 https://claude.ai/download 安装 Claude Desktop"
        
        if (-not $Force) {
            exit 1
        }
    } else {
        Write-ColorOutput "[✓] " $Colors.Success -NoNewline
        Write-Host "Claude CLI: $claudePath"
    }

    # 4. 获取项目路径
    $currentStep++
    Show-Progress -Step $currentStep -Total $totalSteps -Activity "配置项目路径..."
    
    $sagePath = Split-Path -Parent $PSScriptRoot
    if ([string]::IsNullOrEmpty($sagePath)) {
        $sagePath = Get-Location
    }
    
    Write-ColorOutput "[✓] " $Colors.Success -NoNewline
    Write-Host "项目路径: $sagePath"

    # 5. 创建配置目录
    $currentStep++
    Show-Progress -Step $currentStep -Total $totalSteps -Activity "创建配置目录..."
    
    $configDir = "$env:USERPROFILE\.sage-mcp"
    $directories = @(
        $configDir,
        "$configDir\logs",
        "$configDir\bin",
        "$configDir\backups"
    )
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-ColorOutput "[+] " $Colors.Info -NoNewline
            Write-Host "创建目录: $dir"
        }
    }

    # 6. 生成配置文件
    $currentStep++
    Show-Progress -Step $currentStep -Total $totalSteps -Activity "生成配置文件..."
    
    $configFile = "$configDir\config.json"
    $config = @{
        claude_paths = @($claudePath -replace '\\', '\\')
        memory_enabled = $true
        debug_mode = $false
        platform = "windows"
        sage_home = $sagePath -replace '\\', '\\'
        install_date = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        version = "2.0"
    }
    
    $config | ConvertTo-Json -Depth 10 | Set-Content -Path $configFile -Encoding UTF8
    Write-ColorOutput "[✓] " $Colors.Success -NoNewline
    Write-Host "配置文件: $configFile"

    # 7. 创建包装脚本
    $currentStep++
    Show-Progress -Step $currentStep -Total $totalSteps -Activity "创建包装脚本..."
    
    # 创建主包装脚本
    $wrapperPath = "$configDir\bin\claude.ps1"
    @"
# Sage MCP Claude 包装器 (PowerShell)
# 生成时间: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

`$pythonPath = "python"
`$memoryScript = "$sagePath\claude_mem_crossplatform.py"

# 检查记忆脚本是否存在
if (Test-Path `$memoryScript) {
    & `$pythonPath `$memoryScript `$args
} else {
    Write-Host "[Sage MCP] 错误：记忆脚本未找到" -ForegroundColor Red
    Write-Host "预期路径: `$memoryScript" -ForegroundColor Red
    
    # 降级到原始 Claude
    if (Test-Path "$claudePath") {
        & "$claudePath" `$args
    } else {
        Write-Host "原始 Claude 也未找到，请重新安装" -ForegroundColor Red
        exit 1
    }
}
"@ | Set-Content -Path $wrapperPath -Encoding UTF8

    # 创建批处理包装器（兼容 CMD）
    $batchWrapper = "$configDir\bin\claude.cmd"
    @"
@echo off
:: Sage MCP Claude 包装器 (CMD)
powershell.exe -ExecutionPolicy Bypass -File "$wrapperPath" %*
"@ | Set-Content -Path $batchWrapper -Encoding ASCII

    Write-ColorOutput "[✓] " $Colors.Success -NoNewline
    Write-Host "包装脚本已创建"

    # 8. 配置环境变量
    $currentStep++
    Show-Progress -Step $currentStep -Total $totalSteps -Activity "配置环境变量..."
    
    $binPath = "$configDir\bin"
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    
    if ($currentPath -notlike "*$binPath*") {
        $newPath = "$currentPath;$binPath"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-ColorOutput "[✓] " $Colors.Success -NoNewline
        Write-Host "已添加到 PATH: $binPath"
    } else {
        Write-ColorOutput "[i] " $Colors.Info -NoNewline
        Write-Host "PATH 已包含: $binPath"
    }
    
    # 设置 Sage 环境变量
    [Environment]::SetEnvironmentVariable("SAGE_MCP_HOME", $sagePath, "User")
    [Environment]::SetEnvironmentVariable("SAGE_CONFIG_DIR", $configDir, "User")

    # 9. 安装 Python 依赖
    if (-not $SkipDependencies) {
        $currentStep++
        Show-Progress -Step $currentStep -Total $totalSteps -Activity "安装 Python 依赖..."
        
        Push-Location $sagePath
        try {
            Write-Host ""
            Write-ColorOutput "正在安装依赖包..." $Colors.Info
            
            $pipResult = & python -m pip install -r requirements.txt 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-ColorOutput "[✓] " $Colors.Success -NoNewline
                Write-Host "依赖安装成功"
            } else {
                Write-ColorOutput "[!] " $Colors.Warning -NoNewline
                Write-Host "依赖安装出现问题，请检查输出"
            }
        } finally {
            Pop-Location
        }
    }

    # 10. 创建控制命令
    $currentStep++
    Show-Progress -Step $currentStep -Total $totalSteps -Activity "创建控制命令..."
    
    # sage-mode 命令
    $sageModePath = "$configDir\bin\sage-mode.ps1"
    @'
param(
    [Parameter(Position=0)]
    [ValidateSet('on', 'off', 'silent', 'status')]
    [string]$Mode = 'status'
)

switch ($Mode) {
    'on' {
        [Environment]::SetEnvironmentVariable("SAGE_MEMORY_ENABLED", "1", "Process")
        Write-Host "Sage 记忆模式：已启用" -ForegroundColor Green
    }
    'off' {
        [Environment]::SetEnvironmentVariable("SAGE_MEMORY_ENABLED", "0", "Process")
        Write-Host "Sage 记忆模式：已禁用" -ForegroundColor Yellow
    }
    'silent' {
        [Environment]::SetEnvironmentVariable("SAGE_MEMORY_ENABLED", "1", "Process")
        [Environment]::SetEnvironmentVariable("SAGE_SILENT_MODE", "1", "Process")
        Write-Host "Sage 记忆模式：静默模式" -ForegroundColor Cyan
    }
    'status' {
        $enabled = $env:SAGE_MEMORY_ENABLED
        $silent = $env:SAGE_SILENT_MODE
        
        if ($enabled -eq "0") {
            Write-Host "Sage 记忆模式：禁用" -ForegroundColor Red
        } elseif ($silent -eq "1") {
            Write-Host "Sage 记忆模式：启用（静默）" -ForegroundColor Cyan
        } else {
            Write-Host "Sage 记忆模式：启用" -ForegroundColor Green
        }
    }
}
'@ | Set-Content -Path $sageModePath -Encoding UTF8

    # sage-mode.cmd 批处理版本
    $sageModeCmd = "$configDir\bin\sage-mode.cmd"
    @"
@echo off
powershell.exe -ExecutionPolicy Bypass -File "$sageModePath" %*
"@ | Set-Content -Path $sageModeCmd -Encoding ASCII

    Write-ColorOutput "[✓] " $Colors.Success -NoNewline
    Write-Host "控制命令已创建"

    # 完成
    Write-Progress -Completed -Activity "安装完成"
    
    Write-Host ""
    Write-ColorOutput "════════════════════════════════════════" $Colors.Header
    Write-ColorOutput "       安装成功完成！" $Colors.Success
    Write-ColorOutput "════════════════════════════════════════" $Colors.Header
    Write-Host ""
    
    Write-ColorOutput "使用说明：" $Colors.Info
    Write-Host "1. 重新打开 PowerShell 或命令提示符"
    Write-Host "2. 使用命令: claude `"你的问题`""
    Write-Host "3. 控制记忆模式:"
    Write-Host "   - sage-mode on     # 启用记忆"
    Write-Host "   - sage-mode off    # 禁用记忆"
    Write-Host "   - sage-mode silent # 静默模式"
    Write-Host "   - sage-mode status # 查看状态"
    Write-Host ""
    Write-ColorOutput "高级功能：" $Colors.Info
    Write-Host "- 配置文件: $configFile"
    Write-Host "- 日志目录: $configDir\logs"
    Write-Host "- 原始 Claude: $claudePath"
    Write-Host ""
    
    if (-not $Silent) {
        Write-Host "按任意键退出..." -NoNewline
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }

} catch {
    Write-Progress -Completed -Activity "安装失败"
    Write-ColorOutput "[X] 安装失败: $_" $Colors.Error
    Write-Host $_.Exception.StackTrace -ForegroundColor DarkGray
    
    if (-not $Silent) {
        Write-Host ""
        Write-Host "按任意键退出..." -NoNewline
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
    
    exit 1
}