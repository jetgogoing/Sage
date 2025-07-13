#!/usr/bin/env python3
"""
Sage 记忆系统管理命令行工具
提供用户友好的记忆管理接口
"""

import argparse
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
import humanize

from config_manager import get_config_manager, ConfigKey
from memory_interface import get_memory_provider
from exceptions import SageMemoryError, ConfigurationError, DatabaseError

console = Console()


class MemoryCLI:
    """记忆系统命令行接口"""
    
    def __init__(self):
        """初始化CLI"""
        self.config = get_config_manager()
        self.logger = logging.getLogger('MemoryCLI')
        try:
            self.memory_provider = get_memory_provider()
        except Exception as e:
            console.print(f"[red]初始化记忆系统失败: {e}[/red]")
            self.memory_provider = None
    
    def cmd_status(self, args):
        """显示记忆系统状态"""
        if not self.memory_provider:
            console.print("[red]记忆系统未初始化[/red]")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="获取系统状态...", total=None)
            
            try:
                stats = self.memory_provider.get_memory_stats()
                config = self.config.config
                
                # 创建状态表格
                table = Table(title="🧠 Sage 记忆系统状态", show_header=True, header_style="bold magenta")
                table.add_column("项目", style="cyan", width=20)
                table.add_column("值", style="green")
                
                # 基础统计
                table.add_row("总记忆数", str(stats.get('total', 0)))
                table.add_row("用户消息", str(str(stats.get('total', 0) // 2)))
                table.add_row("助手响应", str(str(stats.get('total', 0) // 2)))
                
                # 存储信息
                storage_mb = stats.get('size_mb', 0)
                table.add_row("存储大小", f"{storage_mb:.2f} MB")
                
                # 时间信息
                oldest = stats.get('oldest_memory', 'N/A')
                latest = stats.get('latest', 'N/A')
                if oldest != 'N/A':
                    try:
                        oldest_dt = datetime.fromisoformat(oldest.replace('Z', '+00:00'))
                        oldest = humanize.naturaltime(oldest_dt)
                    except:
                        pass
                
                if latest != 'N/A':
                    try:
                        latest_dt = datetime.fromisoformat(latest.replace('Z', '+00:00'))
                        latest = humanize.naturaltime(latest_dt)
                    except:
                        pass
                
                table.add_row("最早记忆", oldest)
                table.add_row("最新记忆", latest)
                
                # 配置信息
                table.add_section()
                table.add_row("记忆功能", "✅ 启用" if config.memory_enabled else "❌ 禁用")
                table.add_row("检索数量", str(config.retrieval_count))
                table.add_row("相似度阈值", f"{config.similarity_threshold:.2f}")
                table.add_row("时间衰减", "✅ 启用" if config.time_decay else "❌ 禁用")
                table.add_row("最大保存天数", f"{config.max_age_days} 天")
                table.add_row("异步保存", "✅ 启用" if config.async_save else "❌ 禁用")
                
                console.print(table)
                
                # 显示健康状态
                if stats.get('total', 0) == 0:
                    console.print("\n[yellow]提示: 记忆库为空，开始使用 Claude 来积累记忆吧！[/yellow]")
                
            except Exception as e:
                console.print(f"[red]获取状态失败: {e}[/red]")
    
    def cmd_clear(self, args):
        """清除记忆"""
        if not self.memory_provider:
            console.print("[red]记忆系统未初始化[/red]")
            return
        
        if args.days:
            # 清除N天前的记忆
            cutoff_date = datetime.now() - timedelta(days=args.days)
            console.print(f"[yellow]将清除 {args.days} 天前的记忆（{cutoff_date.strftime('%Y-%m-%d')} 之前）[/yellow]")
        else:
            # 清除所有记忆
            console.print("[red]将清除所有记忆！[/red]")
        
        if not args.force:
            confirm = console.input("确认操作？[y/N]: ")
            if confirm.lower() != 'y':
                console.print("[cyan]操作已取消[/cyan]")
                return
        
        try:
            if args.days:
                # 实现按日期清除
                cleared = self._clear_memories_by_date(cutoff_date)
                console.print(f"[green]已清除 {cleared} 条记忆[/green]")
            else:
                # 清除所有
                self.memory_provider.clear_all_memories()
                console.print("[green]所有记忆已清除[/green]")
                
        except Exception as e:
            console.print(f"[red]清除失败: {e}[/red]")
    
    def cmd_search(self, args):
        """搜索记忆"""
        if not self.memory_provider:
            console.print("[red]记忆系统未初始化[/red]")
            return
        
        query = " ".join(args.query)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="搜索记忆...", total=None)
            
            try:
                # 使用基本搜索
                results = self.memory_provider.search_memory(query, n=args.limit)
                
                if not results:
                    console.print("[yellow]未找到相关记忆[/yellow]")
                    return
                
                # 显示搜索结果
                console.print(f"\n[cyan]找到 {len(results)} 条相关记忆:[/cyan]\n")
                
                for i, result in enumerate(results, 1):
                    # 创建结果面板
                    content = Text(result.content[:200] + "..." if len(result.content) > 200 else result.content)
                    
                    # 添加元数据
                    metadata = []
                    if result.metadata.get('timestamp'):
                        try:
                            ts = datetime.fromisoformat(result.metadata['timestamp'].replace('Z', '+00:00'))
                            metadata.append(f"时间: {humanize.naturaltime(ts)}")
                        except:
                            pass
                    
                    metadata.append(f"角色: {result.role}")
                    
                    panel = Panel(
                        content,
                        title=f"[{i}] {' | '.join(metadata)}",
                        border_style="blue"
                    )
                    console.print(panel)
                    
            except Exception as e:
                console.print(f"[red]搜索失败: {e}[/red]")
    
    
    # 辅助方法
    def _clear_memories_by_date(self, cutoff_date: datetime) -> int:
        """按日期清除记忆（简化实现）"""
        # 简化：暂时不支持按日期清除，直接返回0
        console.print("[yellow]按日期清除功能暂未实现[/yellow]")
        return 0


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='Sage 记忆系统管理工具（精简版）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  sage-memory status                    # 查看记忆系统状态
  sage-memory search "Python错误"       # 搜索相关记忆
  sage-memory clear                    # 清除所有记忆
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # status - 查看状态
    subparsers.add_parser('status', help='查看记忆系统状态')
    
    # clear - 清除记忆
    clear_parser = subparsers.add_parser('clear', help='清除记忆')
    clear_parser.add_argument('--days', type=int, help='清除N天前的记忆（暂未实现）')
    clear_parser.add_argument('--force', '-f', action='store_true', help='跳过确认')
    
    # search - 搜索记忆
    search_parser = subparsers.add_parser('search', help='搜索记忆')
    search_parser.add_argument('query', nargs='+', help='搜索关键词')
    search_parser.add_argument('--limit', '-n', type=int, default=5, help='返回结果数量')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 创建CLI实例并执行命令
    cli = MemoryCLI()
    
    command_map = {
        'status': cli.cmd_status,
        'clear': cli.cmd_clear,
        'search': cli.cmd_search,
    }
    
    if args.command in command_map:
        try:
            command_map[args.command](args)
        except KeyboardInterrupt:
            console.print("\n[yellow]操作已取消[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()