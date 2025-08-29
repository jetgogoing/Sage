# Sage MCP Windows 部署指南

## 📋 部署方式选择

Sage MCP Server 在 Windows 10/11 上支持两种部署方式：

| 部署方式 | 适用场景 | 系统要求 | 性能 |
|---------|---------|---------|------|
| **方式A: WSL2 部署**（推荐） | 开发环境、日常使用 | Windows 10 2004+ 或 Windows 11（所有版本） | ⭐⭐⭐⭐⭐ 最佳性能 |
| **方式B: Hyper-V 部署** | 企业环境、无法使用WSL2 | Windows 10/11 Pro/Enterprise | ⭐⭐⭐ 性能适中 |

> 💡 **快速选择建议**：如果不确定选哪种，优先选择 WSL2 部署（方式A）

## 🚀 Claude Code CLI 用户快速部署

如果你在使用 Claude Code CLI，直接告诉 Claude：
```
"帮我在 Windows 上部署 Sage MCP Server，我的系统是 [选择: 支持WSL2 / 只能用Hyper-V]"
```

Claude 会自动识别并执行相应的部署步骤。

---

## 方式A: WSL2 部署（推荐）

### 前置要求

1. **检查 Windows 版本**
   ```powershell
   winver
   # 需要：Windows 10 版本 2004 (Build 19041) 或更高
   ```

2. **启用 WSL2**
   ```powershell
   # 以管理员身份运行 PowerShell
   wsl --install
   # 重启电脑后继续
   ```

3. **验证 WSL2 安装**
   ```powershell
   wsl --list --verbose
   # 应该看到默认的 Linux 发行版
   ```

### 部署步骤

#### 步骤 1: 安装 Docker Desktop
1. 下载 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. 安装时确保勾选 "Use WSL 2 instead of Hyper-V"
3. 重启 Docker Desktop

#### 步骤 2: 配置项目
```powershell
# 1. 进入项目目录
cd C:\Path\To\Sage

# 2. 复制配置文件
copy .env.example .env

# 3. 编辑配置（使用记事本或其他编辑器）
notepad .env
```

**必须修改的配置：**
```env
# 数据库密码（不要使用默认值）
DB_PASSWORD=your_secure_password_here

# API 密钥（从 https://siliconflow.cn 获取）
SILICONFLOW_API_KEY=your_api_key_here
```

#### 步骤 3: 启动服务
```powershell
# 使用 Python 启动器（推荐）
python start_sage.py

# 或使用批处理脚本
start_sage_mcp.bat
```

### WSL2 特定配置

#### 网络配置
- WSL2 自动处理 `localhost` 端口转发
- 数据库连接使用 `DB_HOST=localhost`

#### 路径映射
| Windows 路径 | WSL2 路径 | 说明 |
|-------------|-----------|------|
| `C:\Sage` | `/mnt/c/Sage` | 自动映射 |
| `localhost:5432` | `localhost:5432` | 端口共享 |

### 故障排查

**问题 1: WSL2 未正确安装**
```powershell
# 手动启用必需功能
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
# 重启后继续
wsl --set-default-version 2
```

**问题 2: Docker Desktop 无法启动**
- 确保在 BIOS 中启用了虚拟化
- 检查 Windows 功能中的 "Hyper-V" 是否被禁用

---

## 方式B: Hyper-V 部署（无需 WSL2）

### 前置要求

1. **系统版本要求**
   ```powershell
   # 检查 Windows 版本
   Get-WmiObject -Class Win32_OperatingSystem | Select Caption
   # 必须是 Pro、Enterprise 或 Education 版本
   ```

2. **启用 Hyper-V**
   ```powershell
   # 以管理员身份运行
   Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
   # 重启电脑
   ```

3. **验证 Hyper-V**
   ```powershell
   Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V
   # State 应该显示 "Enabled"
   ```

### 部署步骤

#### 步骤 1: 配置 Docker Desktop 使用 Hyper-V
1. 打开 Docker Desktop 设置
2. General → **取消勾选** "Use the WSL 2 based engine"
3. 重启 Docker Desktop（会自动切换到 Hyper-V 后端）

#### 步骤 2: 配置项目（同 WSL2）
```powershell
# 1. 进入项目目录
cd C:\Path\To\Sage

# 2. 复制并编辑配置
copy .env.example .env
notepad .env
```

#### 步骤 3: 启动服务
```powershell
# 启动数据库容器
docker-compose -f docker-compose-db.yml up -d

# 启动 Sage MCP Server
python start_sage.py
```

### Hyper-V 特定注意事项

#### 端口映射
Hyper-V 模式下，确保 `docker-compose-db.yml` 中的端口映射正确：
```yaml
ports:
  - "5432:5432"  # 如果端口冲突，改为 "5433:5432"
```

#### 连接配置
- 数据库连接同样使用 `localhost`
- 如果连接失败，尝试使用 `host.docker.internal`

### 性能优化
```powershell
# 为 Docker 分配更多资源
# Docker Desktop → Settings → Resources
# - Memory: 至少 4GB
# - CPU: 至少 2 核心
```

---

## 🔧 通用配置说明

### 配置文件结构
```
Sage/
├── .env.example          # 配置模板
├── .env                  # 实际配置（不要提交到 Git）
├── docker-compose-db.yml # 数据库配置
├── start_sage.py         # Python 启动器（跨平台）
└── start_sage_mcp.bat    # Windows 批处理脚本
```

### 环境变量配置
```env
# === 基础配置 ===
DB_HOST=localhost         # 两种部署方式都用 localhost
DB_PORT=5432             # 默认端口，冲突时改为其他
DB_PASSWORD=your_password # 必须修改
SILICONFLOW_API_KEY=key  # 必须配置

# === 高级配置 ===
SAGE_MAX_RESULTS=100     # 搜索结果数量
SAGE_LOG_LEVEL=INFO      # 日志级别
```

---

## 🐛 故障排查指南

### 通用问题

#### 端口被占用
```powershell
# 查找占用 5432 端口的进程
netstat -ano | findstr :5432

# 解决方案 1: 结束占用进程
taskkill /PID <PID> /F

# 解决方案 2: 使用其他端口
# 修改 .env 中的 DB_PORT=5433
```

#### Docker 连接问题
```powershell
# 检查 Docker 是否运行
docker version

# 检查容器状态
docker ps

# 查看容器日志
docker logs sage-db
```

### WSL2 特定问题

#### WSL2 网络问题
```powershell
# 重置 WSL2 网络
wsl --shutdown
netsh winsock reset
# 重启电脑
```

### Hyper-V 特定问题

#### 虚拟交换机问题
```powershell
# 检查 Hyper-V 虚拟交换机
Get-VMSwitch

# 重置 Docker 网络
docker network prune
```

---

## 📁 Claude 桌面应用配置

### 配置文件位置
```
%APPDATA%\Claude\claude_desktop_config.json
```

### 配置示例（两种方式通用）
```json
{
  "mcpServers": {
    "sage": {
      "command": "python",
      "args": ["C:\\Path\\To\\Sage\\start_sage.py"],
      "startupTimeout": 30000
    }
  }
}
```

**注意**：
- 使用双反斜杠 `\\`
- 路径必须是绝对路径
- 修改后重启 Claude 应用

---

## ✅ 验证部署成功

1. **检查服务状态**
   ```powershell
   # 数据库容器运行中
   docker ps | findstr sage-db
   ```

2. **在 Claude 中测试**
   ```
   @sage get_status
   ```
   
   应该返回类似：
   ```json
   {
     "status": "ok",
     "database": "connected",
     "version": "3.0.0"
   }
   ```

3. **查看日志**
   ```powershell
   type logs\sage_mcp_stdio.log
   ```

---

## 🔒 安全建议

1. **密码安全**
   - 不要使用默认密码
   - 使用强密码（至少 12 位，包含大小写字母、数字和特殊字符）

2. **文件权限**
   - 确保 `.env` 文件只有当前用户可读
   - 不要将 `.env` 提交到版本控制

3. **网络安全**
   - 生产环境中限制数据库端口访问
   - 定期更新 Docker 和依赖项

---

## 📞 获取帮助

遇到问题？

1. **查看详细日志**
   ```powershell
   Get-Content logs\sage_mcp_stdio.log -Tail 50
   ```

2. **运行健康检查**
   ```powershell
   python scripts\health_check.py
   ```

3. **参考主文档**
   - `docs/指南/Sage_MCP部署指南.md`
   - `docs/指南/数据库Docker部署指南.md`

---

## 🎉 部署完成！

恭喜！你已经成功在 Windows 上部署了 Sage MCP Server。

**下一步**：
1. 在 Claude 中开始使用 `@sage` 命令
2. 查看 `docs/指南/` 了解更多功能
3. 根据需要调整配置参数

**提示**：WSL2 部署通常性能更好，但 Hyper-V 部署在企业环境中可能更稳定。选择适合你的方式！