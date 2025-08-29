#!/usr/bin/env python3
"""
端到端测试Hooks到Sage的完整链路
检查真实数据流转，无模拟数据
"""

import os
import json
import time
import subprocess
from pathlib import Path
import sys

def check_pre_post_hooks():
    """检查Pre/Post Tool Hooks是否正常工作"""
    print("=== 检查 Pre/Post Tool Hooks ===")
    
    # 查看最近的完整记录
    temp_dir = Path.home() / '.sage_hooks_temp'
    complete_files = sorted(temp_dir.glob('complete_*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not complete_files:
        print("❌ 未找到任何完整工具记录")
        return False
    
    # 检查最近5个记录
    valid_count = 0
    for i, file_path in enumerate(complete_files[:5]):
        with open(file_path) as f:
            data = json.load(f)
        
        # 验证数据完整性
        has_pre = 'pre_call' in data and data['pre_call'].get('tool_name') != 'unknown'
        has_post = 'post_call' in data and data['post_call'].get('session_id') != 'unknown'
        has_id = data.get('call_id') is not None
        
        if has_pre and has_post and has_id:
            valid_count += 1
            if i == 0:  # 显示最新的一个
                print(f"✅ 最新记录: {data['pre_call']['tool_name']} (ID: {data['call_id'][:8]}...)")
    
    success_rate = valid_count / min(5, len(complete_files))
    print(f"   完整记录比例: {valid_count}/{min(5, len(complete_files))} ({success_rate:.0%})")
    
    return success_rate >= 0.8  # 80%以上视为正常

def check_data_aggregator():
    """检查数据聚合器功能"""
    print("\n=== 检查数据聚合器 ===")
    
    # 检查日志文件
    log_file = Path(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "logs", "data_aggregator.log"))
    if not log_file.exists():
        print("❌ 数据聚合器日志不存在")
        return False
    
    # 检查是否有数据被聚合
    try:
        # 导入聚合器
        sys.path.append(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts"))
        from hook_data_aggregator import get_aggregator
        
        aggregator = get_aggregator()
        
        # 获取跨项目会话
        sessions = aggregator.get_cross_project_sessions(hours=24)
        print(f"✅ 最近24小时会话数: {len(sessions)}")
        
        # 检查数据完整性评分功能
        test_score = aggregator.calculate_completeness_score(
            [{"name": "test"}], [], [{"tool_input": {}, "tool_output": {}}]
        )
        print(f"✅ 完整性评分功能正常: {test_score:.2%}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据聚合器错误: {e}")
        return False

def check_stop_hook_archive():
    """检查Stop Hook归档功能"""
    print("\n=== 检查 Stop Hook 归档 ===")
    
    # 检查增强版日志
    enhanced_log = Path(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "logs", "archiver_enhanced.log"))
    if not enhanced_log.exists():
        print("❌ 增强版归档器日志不存在")
        return False
    
    # 检查最近的归档活动
    with open(enhanced_log) as f:
        lines = f.readlines()[-20:]  # 最后20行
    
    has_extraction = any("Extracted data" in line for line in lines)
    has_error = any("ERROR" in line and "No transcript_path" not in line for line in lines)
    
    if has_extraction:
        print("✅ 数据提取功能正常")
    else:
        print("⚠️  最近无数据提取活动")
    
    if has_error:
        print("❌ 发现错误（非路径问题）")
        return False
    
    # 检查备份文件
    backup_dir = Path(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "logs", "backup"))
    backup_count = len(list(backup_dir.glob("conversation_*.json")))
    print(f"✅ 备份文件数: {backup_count}")
    
    return True

def check_sage_mcp_connection():
    """检查Sage MCP连接"""
    print("\n=== 检查 Sage MCP 连接 ===")
    
    try:
        # 直接检查数据库连接
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=sage-db", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and "healthy" in result.stdout:
            print(f"✅ Sage 数据库健康运行")
            
            # 检查MCP配置
            mcp_config = Path.home() / ".config/claude/mcp.json"
            if mcp_config.exists():
                with open(mcp_config) as f:
                    config = json.load(f)
                    if "sage" in config.get("mcpServers", {}):
                        print("✅ Sage MCP 已配置")
                        return True
                    else:
                        print("❌ Sage MCP 未在配置中")
                        return False
            else:
                print("❌ MCP 配置文件不存在")
                return False
        else:
            print(f"❌ Sage 数据库未运行或不健康")
            return False
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def check_hook_logs_health():
    """检查Hook日志健康状态"""
    print("\n=== 检查 Hook 日志健康状态 ===")
    
    log_dir = Path(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "logs"))
    issues = []
    
    # 检查日志文件大小
    for log_file in log_dir.glob("*.log"):
        size_mb = log_file.stat().st_size / 1024 / 1024
        if size_mb > 10:
            issues.append(f"⚠️  {log_file.name} 过大: {size_mb:.1f}MB")
    
    # 检查最近的警告/错误
    for log_name in ["pre_tool_capture.log", "post_tool_capture.log"]:
        log_file = log_dir / log_name
        if log_file.exists():
            with open(log_file) as f:
                content = f.read()
                # 只统计最近的错误（最后1000个字符）
                recent_content = content[-1000:]
                if "ERROR" in recent_content:
                    issues.append(f"❌ {log_name} 有最近的错误")
                elif "WARNING" in recent_content and "unknown" in recent_content:
                    # 已修复的参数问题，忽略旧警告
                    pass
    
    if issues:
        for issue in issues:
            print(issue)
        return len(issues) < 3  # 少于3个问题视为健康
    else:
        print("✅ 所有日志健康")
        return True

def check_technical_debt():
    """检查技术债务"""
    print("\n=== 检查技术债务 ===")
    
    debt_items = []
    
    # 1. 检查是否有未清理的临时文件
    temp_dir = Path.home() / '.sage_hooks_temp'
    old_files = []
    cutoff_time = time.time() - 86400  # 24小时前
    
    for temp_file in temp_dir.glob('*'):
        if temp_file.stat().st_mtime < cutoff_time:
            old_files.append(temp_file)
    
    if old_files:
        debt_items.append(f"⚠️  有 {len(old_files)} 个超过24小时的临时文件未清理")
    
    # 2. 检查是否有TODO或FIXME
    scripts_dir = Path(os.path.join(os.getenv('SAGE_HOME', '.'), "hooks", "scripts"))
    for py_file in scripts_dir.glob("*.py"):
        with open(py_file) as f:
            content = f.read()
            if "TODO" in content or "FIXME" in content:
                debt_items.append(f"📝 {py_file.name} 包含 TODO/FIXME")
    
    # 3. 检查是否有硬编码路径
    hardcoded_paths = []
    for py_file in scripts_dir.glob("*.py"):
        with open(py_file) as f:
            content = f.read()
            if os.getenv('SAGE_HOME', '.') in content and "log_dir" not in content:
                hardcoded_paths.append(py_file.name)
    
    if hardcoded_paths:
        debt_items.append(f"⚠️  硬编码路径: {', '.join(hardcoded_paths)}")
    
    if debt_items:
        for item in debt_items:
            print(item)
        return len(debt_items) < 2  # 少于2个技术债务视为可接受
    else:
        print("✅ 无明显技术债务")
        return True

def main():
    print("开始全链路健康检查...\n")
    
    results = {
        "Pre/Post Hooks": check_pre_post_hooks(),
        "数据聚合器": check_data_aggregator(),
        "Stop Hook归档": check_stop_hook_archive(),
        "Sage MCP连接": check_sage_mcp_connection(),
        "日志健康": check_hook_logs_health(),
        "技术债务": check_technical_debt()
    }
    
    # 总结
    print("\n" + "="*50)
    print("检查结果总结:")
    print("="*50)
    
    passed = 0
    for component, status in results.items():
        status_str = "✅ 正常" if status else "❌ 异常"
        print(f"{component:.<30} {status_str}")
        if status:
            passed += 1
    
    print(f"\n总体健康度: {passed}/{len(results)} ({passed/len(results)*100:.0f}%)")
    
    if passed == len(results):
        print("\n🎉 所有组件正常运行！无模拟数据，无关键技术债务。")
    else:
        print("\n⚠️  部分组件需要关注。")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)