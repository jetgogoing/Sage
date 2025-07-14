#!/usr/bin/env python3
"""
Sage MCP 平台检测和迁移工具
用于从旧版本迁移到跨平台版本
"""

import os
import sys
import json
import shutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ANSI 颜色代码
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class MigrationTool:
    """迁移工具主类"""
    
    def __init__(self):
        self.platform = platform.system()
        self.sage_path = Path(__file__).parent.absolute()
        self.home_path = Path.home()
        self.config_dir = self.home_path / '.sage-mcp'
        self.backup_dir = self.config_dir / 'backups' / f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        
        # 检测结果
        self.detection_results = {
            'platform': self.platform,
            'python_version': sys.version,
            'old_installations': [],
            'current_config': None,
            'claude_locations': [],
            'shell_configs': [],
            'aliases': [],
            'env_vars': {}
        }
        
    def print_header(self):
        """打印头部信息"""
        print(f"\n{Colors.MAGENTA}╔══════════════════════════════════════════════════╗{Colors.RESET}")
        print(f"{Colors.MAGENTA}║     Sage MCP 平台检测和迁移工具 v2.0            ║{Colors.RESET}")
        print(f"{Colors.MAGENTA}╚══════════════════════════════════════════════════╝{Colors.RESET}")
        print(f"\n{Colors.CYAN}平台: {self.platform} | Python: {platform.python_version()}{Colors.RESET}\n")
    
    def detect_platform_details(self):
        """检测平台详细信息"""
        print(f"{Colors.BLUE}[1/6] 检测平台信息...{Colors.RESET}")
        
        details = {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_implementation': platform.python_implementation(),
            'python_version': platform.python_version(),
            'python_build': platform.python_build()
        }
        
        print(f"{Colors.GREEN}[✓] 平台: {details['system']} {details['release']}{Colors.RESET}")
        print(f"{Colors.GREEN}[✓] 架构: {details['machine']}{Colors.RESET}")
        
        return details
    
    def find_old_installations(self):
        """查找旧版本安装"""
        print(f"\n{Colors.BLUE}[2/6] 查找现有安装...{Colors.RESET}")
        
        installations = []
        
        # 1. 检查 shell 配置文件中的别名
        shell_configs = self._get_shell_configs()
        for config_file in shell_configs:
            if config_file.exists():
                content = config_file.read_text()
                
                # 查找 claude 别名
                if 'alias claude=' in content:
                    for line in content.splitlines():
                        if line.strip().startswith('alias claude='):
                            alias_def = line.split('=', 1)[1].strip().strip('"\'')
                            installations.append({
                                'type': 'alias',
                                'location': str(config_file),
                                'definition': alias_def,
                                'version': 'v1' if 'claude_mem.py' in alias_def else 'unknown'
                            })
                            print(f"{Colors.YELLOW}[!] 发现别名: {alias_def}{Colors.RESET}")
        
        # 2. 检查 PATH 中的包装脚本
        if self.platform != 'Windows':
            wrapper_locations = [
                self.home_path / '.local' / 'bin' / 'claude',
                Path('/usr/local/bin/claude-mem'),
                self.config_dir / 'bin' / 'claude'
            ]
        else:
            wrapper_locations = [
                self.home_path / '.sage-mcp' / 'bin' / 'claude.bat',
                self.home_path / '.sage-mcp' / 'bin' / 'claude.ps1',
                self.home_path / 'AppData' / 'Local' / 'sage-mcp' / 'claude.bat'
            ]
        
        for wrapper in wrapper_locations:
            if wrapper.exists():
                installations.append({
                    'type': 'wrapper',
                    'location': str(wrapper),
                    'version': self._detect_wrapper_version(wrapper)
                })
                print(f"{Colors.YELLOW}[!] 发现包装器: {wrapper}{Colors.RESET}")
        
        # 3. 检查配置文件
        old_config_locations = [
            self.sage_path / '.env',
            self.config_dir / 'config.json',
            self.home_path / '.claude_mem_config.json'
        ]
        
        for config in old_config_locations:
            if config.exists():
                installations.append({
                    'type': 'config',
                    'location': str(config),
                    'version': 'unknown'
                })
                print(f"{Colors.YELLOW}[!] 发现配置: {config}{Colors.RESET}")
        
        self.detection_results['old_installations'] = installations
        
        if not installations:
            print(f"{Colors.GREEN}[✓] 未发现旧版本安装{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}[!] 发现 {len(installations)} 个现有安装{Colors.RESET}")
        
        return installations
    
    def find_claude_executable(self):
        """查找 Claude 可执行文件"""
        print(f"\n{Colors.BLUE}[3/6] 查找 Claude CLI...{Colors.RESET}")
        
        claude_paths = []
        
        if self.platform == 'Windows':
            search_paths = [
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Claude' / 'claude.exe',
                Path(os.environ.get('PROGRAMFILES', '')) / 'Claude' / 'claude.exe',
                Path(os.environ.get('PROGRAMFILES(X86)', '')) / 'Claude' / 'claude.exe',
                self.home_path / 'AppData' / 'Local' / 'Programs' / 'claude' / 'claude.exe'
            ]
        else:
            search_paths = [
                Path('/usr/local/bin/claude'),
                Path('/usr/bin/claude'),
                self.home_path / '.local' / 'bin' / 'claude',
                self.home_path / '.claude' / 'local' / 'claude',
                Path('/opt/claude/bin/claude')
            ]
        
        # 检查预定义路径
        for path in search_paths:
            if path.exists() and path.is_file():
                # 验证是否是真正的 Claude 可执行文件
                if self._is_real_claude(path):
                    claude_paths.append(str(path))
                    print(f"{Colors.GREEN}[✓] 找到 Claude: {path}{Colors.RESET}")
        
        # 检查 PATH
        try:
            if self.platform == 'Windows':
                result = subprocess.run(['where', 'claude'], capture_output=True, text=True)
            else:
                result = subprocess.run(['which', 'claude'], capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line and self._is_real_claude(Path(line)):
                        if str(line) not in claude_paths:
                            claude_paths.append(str(line))
                            print(f"{Colors.GREEN}[✓] PATH 中找到: {line}{Colors.RESET}")
        except:
            pass
        
        self.detection_results['claude_locations'] = claude_paths
        
        if not claude_paths:
            print(f"{Colors.RED}[✗] 未找到 Claude CLI{Colors.RESET}")
        
        return claude_paths
    
    def backup_existing_config(self):
        """备份现有配置"""
        print(f"\n{Colors.BLUE}[4/6] 备份现有配置...{Colors.RESET}")
        
        # 创建备份目录
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        backed_up = []
        
        # 备份配置文件
        for installation in self.detection_results['old_installations']:
            if installation['type'] == 'config':
                src = Path(installation['location'])
                if src.exists():
                    dst = self.backup_dir / src.name
                    shutil.copy2(src, dst)
                    backed_up.append(str(src))
                    print(f"{Colors.GREEN}[✓] 备份: {src.name}{Colors.RESET}")
        
        # 备份 .env 文件
        env_file = self.sage_path / '.env'
        if env_file.exists():
            dst = self.backup_dir / '.env'
            shutil.copy2(env_file, dst)
            backed_up.append(str(env_file))
            print(f"{Colors.GREEN}[✓] 备份: .env{Colors.RESET}")
        
        # 备份 shell 配置
        for config_file in self._get_shell_configs():
            if config_file.exists():
                dst = self.backup_dir / f"{config_file.name}.backup"
                shutil.copy2(config_file, dst)
                backed_up.append(str(config_file))
                print(f"{Colors.GREEN}[✓] 备份: {config_file.name}{Colors.RESET}")
        
        print(f"{Colors.CYAN}[i] 备份位置: {self.backup_dir}{Colors.RESET}")
        
        return backed_up
    
    def migrate_configuration(self):
        """迁移配置到新版本"""
        print(f"\n{Colors.BLUE}[5/6] 迁移配置...{Colors.RESET}")
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 新配置
        new_config = {
            'claude_paths': self.detection_results['claude_locations'],
            'memory_enabled': True,
            'debug_mode': False,
            'platform': self.platform.lower(),
            'sage_home': str(self.sage_path),
            'migrated_from': 'v1',
            'migration_date': datetime.now().isoformat(),
            'version': '2.0'
        }
        
        # 尝试加载旧配置
        old_env_file = self.sage_path / '.env'
        if old_env_file.exists():
            from dotenv import dotenv_values
            old_env = dotenv_values(old_env_file)
            
            # 迁移 API 密钥
            if 'SILICONFLOW_API_KEY' in old_env:
                new_config['api_key'] = old_env['SILICONFLOW_API_KEY']
                print(f"{Colors.GREEN}[✓] 迁移 API 密钥{Colors.RESET}")
            
            # 迁移数据库配置
            db_config = {}
            for key in ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']:
                if key in old_env:
                    db_config[key.lower()] = old_env[key]
            
            if db_config:
                new_config['db_config'] = db_config
                print(f"{Colors.GREEN}[✓] 迁移数据库配置{Colors.RESET}")
            
            # 迁移 Claude 路径
            if 'CLAUDE_CLI_PATH' in old_env and old_env['CLAUDE_CLI_PATH'] not in new_config['claude_paths']:
                new_config['claude_paths'].append(old_env['CLAUDE_CLI_PATH'])
                print(f"{Colors.GREEN}[✓] 迁移 Claude 路径{Colors.RESET}")
        
        # 保存新配置
        config_file = self.config_dir / 'config.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=4, ensure_ascii=False)
        
        print(f"{Colors.GREEN}[✓] 新配置已保存: {config_file}{Colors.RESET}")
        
        return new_config
    
    def generate_migration_report(self):
        """生成迁移报告"""
        print(f"\n{Colors.BLUE}[6/6] 生成迁移报告...{Colors.RESET}")
        
        report_file = self.config_dir / 'migration_report.md'
        
        report_content = f"""# Sage MCP 迁移报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 平台信息
- 操作系统: {self.platform}
- Python 版本: {platform.python_version()}
- 项目路径: {self.sage_path}

## 发现的安装
"""
        
        for inst in self.detection_results['old_installations']:
            report_content += f"- **{inst['type']}**: {inst['location']} (版本: {inst['version']})\n"
        
        report_content += f"\n## Claude CLI 位置\n"
        for path in self.detection_results['claude_locations']:
            report_content += f"- {path}\n"
        
        report_content += f"""
## 迁移操作
- 备份目录: {self.backup_dir}
- 新配置文件: {self.config_dir / 'config.json'}

## 下一步操作
1. 运行对应平台的安装脚本:
   - Windows: `install.bat` 或 `install.ps1`
   - Unix/Linux/macOS: `./install-crossplatform.sh`

2. 验证安装:
   - 运行 `sage-doctor` 进行系统诊断
   - 测试 `claude "你好"` 命令

3. 如需回滚:
   - 配置备份在: {self.backup_dir}
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"{Colors.GREEN}[✓] 迁移报告: {report_file}{Colors.RESET}")
        
        return report_file
    
    def _get_shell_configs(self) -> List[Path]:
        """获取 shell 配置文件列表"""
        configs = []
        
        if self.platform != 'Windows':
            possible_configs = [
                self.home_path / '.zshrc',
                self.home_path / '.bashrc',
                self.home_path / '.bash_profile',
                self.home_path / '.profile',
                self.home_path / '.config' / 'fish' / 'config.fish'
            ]
            
            for config in possible_configs:
                if config.exists():
                    configs.append(config)
        
        return configs
    
    def _detect_wrapper_version(self, wrapper_path: Path) -> str:
        """检测包装器版本"""
        try:
            content = wrapper_path.read_text()
            if 'sage_crossplatform.py' in content:
                return 'v2.0'
            elif 'claude_mem_v2.py' in content:
                return 'v1.2'
            elif 'claude_mem.py' in content:
                return 'v1.0'
            else:
                return 'unknown'
        except:
            return 'unknown'
    
    def _is_real_claude(self, path: Path) -> bool:
        """验证是否是真正的 Claude 可执行文件"""
        if not path.exists() or not path.is_file():
            return False
        
        # 检查是否是脚本包装器
        try:
            content = path.read_text()
            if 'claude_mem' in content or 'sage-mcp' in content.lower():
                return False
        except:
            # 二进制文件，可能是真的 Claude
            pass
        
        # 检查文件大小（包装脚本通常很小）
        if path.stat().st_size < 1024:  # 小于 1KB
            return False
        
        return True
    
    def run(self):
        """运行迁移工具"""
        self.print_header()
        
        try:
            # 1. 检测平台
            platform_details = self.detect_platform_details()
            
            # 2. 查找旧安装
            old_installations = self.find_old_installations()
            
            # 3. 查找 Claude
            claude_paths = self.find_claude_executable()
            
            if not claude_paths:
                print(f"\n{Colors.RED}[错误] 未找到 Claude CLI，请先安装{Colors.RESET}")
                print(f"访问: https://claude.ai/download")
                return False
            
            # 4. 备份配置
            if old_installations:
                backed_up = self.backup_existing_config()
            
            # 5. 迁移配置
            new_config = self.migrate_configuration()
            
            # 6. 生成报告
            report = self.generate_migration_report()
            
            # 完成
            print(f"\n{Colors.GREEN}{'='*50}{Colors.RESET}")
            print(f"{Colors.GREEN}{Colors.BOLD}迁移完成！{Colors.RESET}")
            print(f"{Colors.GREEN}{'='*50}{Colors.RESET}")
            
            print(f"\n{Colors.CYAN}后续步骤:{Colors.RESET}")
            print(f"1. 运行安装脚本完成升级")
            print(f"2. 查看迁移报告: {report}")
            print(f"3. 测试新版本功能")
            
            return True
            
        except Exception as e:
            print(f"\n{Colors.RED}[错误] 迁移失败: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """主入口"""
    tool = MigrationTool()
    success = tool.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()