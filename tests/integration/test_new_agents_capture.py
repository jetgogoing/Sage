#!/usr/bin/env python3
"""
测试新创建的3个Agents输出捕获能力
- coding-executor
- code-review  
- report-generator
"""
import json
import tempfile
from pathlib import Path
import sys
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hooks.scripts.sage_stop_hook import SageStopHook

def test_coding_executor_agent():
    """测试coding-executor agent的输出捕获"""
    
    # 模拟coding-executor的输出格式
    report_content = """=== Code Execution Report by @coding_executor ===
执行ID: ce-001-20250810-175600
任务类型: Python Script Execution

执行状态：
✅ 代码语法检查通过
✅ 运行环境准备完成
✅ 执行成功，无错误

执行结果：
- 输出行数: 42
- 执行时间: 1.23秒
- 内存使用: 15.6MB
- CPU时间: 0.98秒

输出摘要：
```
Hello World
Processing data...
Task completed successfully
```

<!-- AGENT_METADATA
{
  "agent_id": "coding_executor",
  "task_id": "ce-001-20250810-175600",
  "execution_metrics": {
    "lines_output": 42,
    "execution_time_ms": 1230,
    "memory_mb": 15.6,
    "cpu_time_s": 0.98,
    "exit_code": 0
  },
  "environment": {
    "python_version": "3.11.5",
    "platform": "darwin"
  }
}
-->

建议：
- 代码执行效率良好
- 考虑添加更多错误处理

=== End of Report ==="""
    
    sample_transcript = [
        '{"type": "user", "message": {"text": "@coding_executor run main.py"}}',
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": report_content}]}})
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-coding-executor',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    # 验证
    assistant_msg = messages[1] if len(messages) > 1 else None
    assert assistant_msg is not None, "未找到assistant消息"
    assert assistant_msg.get('is_agent_report') == True, "未识别为agent报告"
    
    agent_metadata = assistant_msg.get('agent_metadata', {})
    assert agent_metadata.get('agent_name') == 'coding_executor', f"Agent名称不匹配: {agent_metadata.get('agent_name')}"
    assert 'embedded_metadata' in agent_metadata, "未提取嵌入元数据"
    
    # 验证执行指标
    metrics = agent_metadata.get('embedded_metadata', {}).get('execution_metrics', {})
    assert metrics.get('exit_code') == 0, "退出码不正确"
    assert metrics.get('execution_time_ms') == 1230, "执行时间不正确"
    
    Path(transcript_path).unlink()
    print(f"✅ coding-executor测试通过 - 捕获了{len(messages)}条消息")
    return True

def test_code_review_agent():
    """测试code-review agent的输出捕获"""
    
    report_content = """=== Code Review Report by @code_review ===
审查ID: cr-002-20250810-175615
目标文件: /Users/jet/Sage/main.py
审查时间: 2.5秒

代码质量评分: 8.5/10

发现的问题：
🔴 严重 (1):
- 第156行: SQL注入风险 - 使用了字符串拼接构建查询

🟡 中等 (3):
- 第45行: 函数复杂度过高 (圈复杂度=12)
- 第89行: 缺少输入验证
- 第203行: 硬编码的配置值

🟢 建议 (5):
- 添加更多单元测试
- 改进变量命名
- 提取重复代码为函数
- 添加类型注解
- 更新文档字符串

代码覆盖率：
- 测试覆盖率: 76%
- 类型注解覆盖: 65%
- 文档覆盖率: 82%

<!-- AGENT_METADATA
{
  "agent_id": "code_review",
  "review_id": "cr-002-20250810-175615",
  "quality_score": 8.5,
  "issues": {
    "critical": 1,
    "medium": 3,
    "suggestions": 5
  },
  "coverage": {
    "test": 76,
    "type_hints": 65,
    "documentation": 82
  }
}
-->

优先修复建议：
1. 立即修复SQL注入漏洞
2. 降低高复杂度函数
3. 添加输入验证

=== End of Report ==="""
    
    sample_transcript = [
        '{"type": "user", "message": {"text": "@code_review analyze main.py"}}',
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": report_content}]}})
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-code-review',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    # 验证
    assistant_msg = messages[1] if len(messages) > 1 else None
    assert assistant_msg is not None, "未找到assistant消息"
    assert assistant_msg.get('is_agent_report') == True, "未识别为agent报告"
    
    agent_metadata = assistant_msg.get('agent_metadata', {})
    assert agent_metadata.get('agent_name') == 'code_review', f"Agent名称不匹配: {agent_metadata.get('agent_name')}"
    
    # 验证内容特征
    features = agent_metadata.get('content_features', {})
    # code-review报告使用问题标记（🔴）而不是"错误"，所以不会有has_errors
    # 验证有建议即可
    assert features.get('has_recommendations') == True, "未检测到建议"
    
    # 验证嵌入元数据中的issues计数
    embedded = agent_metadata.get('embedded_metadata', {})
    issues = embedded.get('issues', {})
    assert issues.get('critical') == 1, f"严重问题数量不匹配: {issues.get('critical')}"
    
    Path(transcript_path).unlink()
    print(f"✅ code-review测试通过 - 质量评分: {agent_metadata.get('embedded_metadata', {}).get('quality_score', 'N/A')}/10")
    return True

def test_report_generator_agent():
    """测试report-generator agent的输出捕获"""
    
    report_content = """=== Analysis Report by @report_generator ===
报告ID: rg-003-20250810-175630
生成时间: 2025-08-10 17:56:30
报告类型: 综合分析报告

📊 执行摘要：
本次分析涵盖了3个核心模块的性能评估和代码质量审查。

📈 关键指标：
• 总体代码质量: 85%
• 性能评分: 92/100
• 安全评分: 78/100
• 可维护性: B+

🔍 详细发现：

1. 性能分析
   - API响应时间: 平均 120ms
   - 数据库查询: 平均 45ms
   - 缓存命中率: 87%

2. 安全审计
   ✅ 已实施的安全措施:
   - HTTPS强制
   - XSS防护
   - CSRF令牌
   
   ⚠️ 需要改进:
   - 密码策略强度
   - API速率限制
   - 日志脱敏

3. 代码质量
   - 重复代码: 3.2%
   - 技术债务: 12小时
   - 代码异味: 15个

📝 建议优先级：
P0 - 紧急:
• 修复已识别的安全漏洞

P1 - 高:
• 优化慢查询
• 实施API速率限制

P2 - 中:
• 重构高复杂度模块
• 增加测试覆盖率

<!-- AGENT_METADATA
{
  "agent_id": "report_generator",
  "report_id": "rg-003-20250810-175630",
  "report_type": "comprehensive_analysis",
  "metrics": {
    "code_quality": 85,
    "performance_score": 92,
    "security_score": 78,
    "maintainability": "B+"
  },
  "summary": {
    "modules_analyzed": 3,
    "issues_found": 18,
    "recommendations": 12,
    "estimated_fix_time_hours": 36
  },
  "timestamp": "2025-08-10T17:56:30Z"
}
-->

📎 附录：
- 详细性能报告见附件A
- 安全审计详情见附件B
- 代码质量报告见附件C

=== End of Report ==="""
    
    sample_transcript = [
        '{"type": "user", "message": {"text": "@report_generator create comprehensive analysis"}}',
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": report_content}]}})
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-report-generator',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    # 验证
    assistant_msg = messages[1] if len(messages) > 1 else None
    assert assistant_msg is not None, "未找到assistant消息"
    assert assistant_msg.get('is_agent_report') == True, "未识别为agent报告"
    
    agent_metadata = assistant_msg.get('agent_metadata', {})
    assert agent_metadata.get('agent_name') == 'report_generator', f"Agent名称不匹配: {agent_metadata.get('agent_name')}"
    assert agent_metadata.get('report_type') == 'Analysis', "报告类型不匹配"
    
    # 验证完整性得分
    completeness = agent_metadata.get('completeness_score', 0)
    assert completeness > 0.5, f"报告完整性得分过低: {completeness}"
    
    Path(transcript_path).unlink()
    print(f"✅ report-generator测试通过 - 完整性得分: {completeness:.2%}")
    return True

def test_agent_interaction_capture():
    """测试多个agents交互的捕获"""
    
    sample_transcript = [
        '{"type": "user", "message": {"text": "analyze and execute the code"}}',
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "I'll coordinate multiple agents to help you. Let me start with code execution."}]}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "@coding_executor executing your code...\n\nExecution completed successfully. Output: Hello World"}]}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Now let me run a code review."}]}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Agent Report: code_review\n\nCode quality: Good\nNo critical issues found\nSuggestion: Add more comments"}]}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Finally, generating the comprehensive report."}]}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "@report_generator Summary\n\nAll tasks completed successfully:\n- Code executed without errors\n- Code review passed\n- Quality score: 8/10"}]}})
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-multi-agent',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    # 统计agent报告
    agent_reports = [m for m in messages if m.get('is_agent_report', False)]
    agent_names = [m.get('agent_metadata', {}).get('agent_name') for m in agent_reports]
    
    print(f"  发现 {len(agent_reports)} 个agent报告")
    print(f"  识别的agents: {', '.join(filter(None, agent_names))}")
    
    assert len(agent_reports) >= 2, f"应该识别至少2个agent报告，实际: {len(agent_reports)}"
    
    Path(transcript_path).unlink()
    print(f"✅ 多agent交互测试通过 - 捕获了{len(messages)}条消息，{len(agent_reports)}个agent报告")
    return True

def run_comprehensive_test():
    """运行所有新agents的综合测试"""
    print("=== 新创建Agents捕获能力测试 ===")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    tests = [
        ("1. coding-executor Agent", test_coding_executor_agent),
        ("2. code-review Agent", test_code_review_agent),
        ("3. report-generator Agent", test_report_generator_agent),
        ("4. 多Agent交互", test_agent_interaction_capture)
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
            failed += 1
    
    print("\n" + "="*50)
    print(f"测试结果汇总:")
    print(f"  通过: {passed}/{len(tests)}")
    print(f"  失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 完美！所有新创建的agents输出都能被正确捕获！")
        print("\n验证的能力：")
        print("  ✅ coding-executor的执行报告捕获")
        print("  ✅ code-review的审查报告捕获")
        print("  ✅ report-generator的分析报告捕获")
        print("  ✅ 多agent协作场景的报告捕获")
        print("  ✅ 嵌入式元数据的完整提取")
        print("  ✅ 报告质量评分计算")
        print("\nSage MCP系统已准备好捕获所有agents的输出！")
    else:
        print("\n⚠️ 部分测试失败，请检查具体错误信息")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)