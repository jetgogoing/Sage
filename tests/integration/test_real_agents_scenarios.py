#!/usr/bin/env python3
"""
测试真实Agent场景的报告捕获
包括security_agent和perf_analyzer等
"""
import json
import tempfile
from pathlib import Path
import sys
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hooks.scripts.sage_stop_hook import SageStopHook

def test_security_agent_capture():
    """测试security_agent的安全审计报告捕获"""
    
    # 使用实际的安全审计报告格式
    report_content = """=== Security Audit Report by @security_agent ===
执行ID: sa-003-20250810
扫描时间: 5.2秒

检查结果：
✅ 无SQL注入漏洞
✅ XSS防护已启用
⚠️ 发现弱密码策略
❌ 缺少CSRF令牌

指标统计：
- 扫描文件: 100
- 发现问题: 2
- 严重程度: 中等

建议：
1. 更新密码策略要求
2. 实施CSRF保护
3. 定期安全审计

=== End of Report ==="""
    
    sample_transcript = [
        '{"type": "user", "message": {"text": "security audit"}}',
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": report_content}]}})
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-security-agent',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    # 验证
    assistant_msg = messages[1] if len(messages) > 1 else None
    assert assistant_msg is not None, "未找到assistant消息"
    assert assistant_msg.get('is_agent_report') == True, "未识别为agent报告"
    
    agent_metadata = assistant_msg.get('agent_metadata', {})
    assert agent_metadata.get('agent_name') == 'security_agent', f"Agent名称不匹配: {agent_metadata.get('agent_name')}"
    assert agent_metadata.get('report_type') == 'Security Audit', "报告类型不匹配"
    
    # 验证内容特征
    features = agent_metadata.get('content_features', {})
    assert features.get('has_success') == True, "未检测到成功标记"
    assert features.get('has_warnings') == True, "未检测到警告标记"
    assert features.get('has_errors') == True, "未检测到错误标记"
    
    Path(transcript_path).unlink()
    print(f"✅ security_agent测试通过 - 检测到{sum([features.get('has_errors', False), features.get('has_warnings', False)])}个安全问题")
    return True

def test_perf_analyzer_with_metadata():
    """测试perf_analyzer带嵌入元数据的报告捕获"""
    
    report_content = """=== Performance Analysis Report by @perf_analyzer ===
执行时间: 3.5秒
任务ID: pa-002-20250810

性能指标：
- CPU使用率: 45%
- 内存占用: 128MB
- 响应时间: 250ms

<!-- AGENT_METADATA
{
  "agent_id": "perf_analyzer",
  "task_id": "pa-002-20250810",
  "internal_metrics": {
    "files_analyzed": 5,
    "total_lines": 1500,
    "execution_time_ms": 3500
  }
}
-->

建议优化数据库查询
=== End of Report ==="""
    
    sample_transcript = [
        '{"type": "user", "message": {"text": "@perf_analyzer check performance"}}',
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": report_content}]}})
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-perf-analyzer',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    # 验证
    assistant_msg = messages[1] if len(messages) > 1 else None
    assert assistant_msg is not None, "未找到assistant消息"
    assert assistant_msg.get('is_agent_report') == True, "未识别为agent报告"
    
    agent_metadata = assistant_msg.get('agent_metadata', {})
    assert agent_metadata.get('agent_name') == 'perf_analyzer', f"Agent名称不匹配: {agent_metadata.get('agent_name')}"
    
    # 验证嵌入元数据
    embedded = agent_metadata.get('embedded_metadata', {})
    assert embedded.get('agent_id') == 'perf_analyzer', "嵌入元数据的agent_id不匹配"
    assert embedded.get('task_id') == 'pa-002-20250810', "任务ID不匹配"
    
    internal_metrics = embedded.get('internal_metrics', {})
    assert internal_metrics.get('files_analyzed') == 5, "分析文件数不匹配"
    assert internal_metrics.get('execution_time_ms') == 3500, "执行时间不匹配"
    
    Path(transcript_path).unlink()
    print(f"✅ perf_analyzer测试通过 - 分析了{internal_metrics.get('files_analyzed')}个文件，耗时{internal_metrics.get('execution_time_ms')}ms")
    return True

def test_mixed_conversation_with_agents():
    """测试混合对话中的agent报告识别"""
    
    sample_transcript = [
        '{"type": "user", "message": {"text": "分析一下系统的整体状况"}}',
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "我将协调多个专门的agents来为您进行全面分析。"}]}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "首先，让我运行性能分析..."}]}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "@perf_analyzer 正在分析...\n\n性能良好，响应时间正常"}]}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "接下来进行安全审计..."}]}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Agent Report: security_agent\n\n安全状态: 良好\n无严重漏洞\n建议: 更新依赖"}]}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "系统整体状况良好，性能和安全都在预期范围内。"}]}})
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-mixed-conversation',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    # 统计agent报告和普通消息
    agent_reports = [m for m in messages if m.get('is_agent_report', False)]
    normal_messages = [m for m in messages if not m.get('is_agent_report', False)]
    
    print(f"  总消息数: {len(messages)}")
    print(f"  Agent报告: {len(agent_reports)}")
    print(f"  普通消息: {len(normal_messages)}")
    
    # 验证识别的agents
    agent_names = [m.get('agent_metadata', {}).get('agent_name') for m in agent_reports]
    print(f"  识别的Agents: {', '.join(filter(None, agent_names))}")
    
    assert len(agent_reports) == 2, f"应该识别2个agent报告，实际: {len(agent_reports)}"
    assert 'perf_analyzer' in agent_names, "未识别perf_analyzer"
    assert 'security_agent' in agent_names, "未识别security_agent"
    
    Path(transcript_path).unlink()
    print(f"✅ 混合对话测试通过 - 正确区分了agent报告和普通消息")
    return True

def test_chinese_agent_report():
    """测试中文Agent报告的捕获"""
    
    report_content = """=== 代码质量报告 by @quality_inspector ===
检查时间: 2025-08-10 19:45:00
项目: Sage MCP系统

代码质量评分: 92/100

优秀方面：
✅ 良好的模块化设计
✅ 完善的错误处理
✅ 清晰的代码注释

待改进：
⚠️ 部分函数过长（>50行）
⚠️ 缺少单元测试
⚠️ 魔法数字未提取为常量

统计数据：
- 总代码行数: 5,234
- 测试覆盖率: 78%
- 技术债务: 12小时

<!-- AGENT_METADATA
{
  "agent_id": "quality_inspector",
  "language": "zh-CN",
  "score": 92,
  "tech_debt_hours": 12
}
-->

下一步建议：
1. 增加单元测试覆盖率至85%以上
2. 重构长函数，控制在30行以内
3. 提取所有魔法数字为命名常量

=== 报告结束 ==="""
    
    sample_transcript = [
        '{"type": "user", "message": {"text": "检查代码质量"}}',
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": report_content}]}})
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-chinese-agent',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    # 验证
    assistant_msg = messages[1] if len(messages) > 1 else None
    assert assistant_msg is not None, "未找到assistant消息"
    assert assistant_msg.get('is_agent_report') == True, "未识别为agent报告"
    
    agent_metadata = assistant_msg.get('agent_metadata', {})
    assert agent_metadata.get('agent_name') == 'quality_inspector', f"Agent名称不匹配: {agent_metadata.get('agent_name')}"
    
    # 验证中文内容的识别
    features = agent_metadata.get('content_features', {})
    assert features.get('has_success') == True, "未检测到成功标记（中文）"
    assert features.get('has_warnings') == True, "未检测到警告标记（中文）"
    
    # 验证嵌入元数据
    embedded = agent_metadata.get('embedded_metadata', {})
    assert embedded.get('language') == 'zh-CN', "语言标记不正确"
    assert embedded.get('score') == 92, "质量评分不匹配"
    
    Path(transcript_path).unlink()
    print(f"✅ 中文Agent报告测试通过 - 质量评分: {embedded.get('score')}/100")
    return True

def run_comprehensive_scenarios_test():
    """运行所有真实场景测试"""
    print("=== 真实Agent场景捕获测试 ===")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    tests = [
        ("1. Security Agent审计报告", test_security_agent_capture),
        ("2. Performance Analyzer嵌入元数据", test_perf_analyzer_with_metadata),
        ("3. 混合对话中的Agent识别", test_mixed_conversation_with_agents),
        ("4. 中文Agent报告", test_chinese_agent_report)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n测试 {test_name}:")
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"❌ 失败: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*50)
    print(f"测试结果汇总:")
    print(f"  通过: {passed}/{len(tests)}")
    print(f"  失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 完美！所有真实场景的Agent报告都能被正确捕获！")
        print("\n验证的场景：")
        print("  ✅ Security Agent安全审计报告")
        print("  ✅ Performance Analyzer性能分析报告")
        print("  ✅ 混合对话中的Agent报告识别")
        print("  ✅ 中文Agent报告处理")
        print("  ✅ 嵌入式元数据完整提取")
        print("\n系统已完全适配各种Agent报告格式！")
    else:
        print("\n⚠️ 部分测试失败，请检查具体错误信息")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = run_comprehensive_scenarios_test()
    sys.exit(0 if success else 1)