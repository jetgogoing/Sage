#!/usr/bin/env python3
"""
测试Agent报告捕获功能的完整性
验证各种格式的Agent报告都能被正确识别和解析
"""
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hooks.scripts.sage_stop_hook import SageStopHook

def test_standard_format_report():
    """测试标准格式的Agent报告"""
    sample_transcript = [
        '{"type": "user", "message": {"text": "@code_reviewer analyze main.py"}}',
        '{"type": "assistant", "message": {"content": [{"type": "text", "text": "=== Code Review Report by @code_reviewer ===\\n执行ID: cr-001-20250810\\n文件: main.py\\n\\n✅ 语法检查通过\\n⚠️ 发现3个代码质量问题\\n\\n建议：优化函数复杂度\\n=== End of Report ==="}]}}'
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-standard-format',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    # 验证Agent报告被识别
    assistant_msg = messages[1] if len(messages) > 1 else None
    assert assistant_msg is not None
    assert assistant_msg.get('is_agent_report') == True
    
    # 验证元数据提取
    agent_metadata = assistant_msg.get('agent_metadata', {})
    assert agent_metadata.get('agent_name') == 'code_reviewer'
    assert agent_metadata.get('report_type') == 'Code Review'
    assert agent_metadata.get('format') == 'standard'
    
    Path(transcript_path).unlink()
    return True

def test_embedded_metadata_report():
    """测试包含嵌入元数据的Agent报告"""
    report_content = '''=== Performance Analysis Report by @perf_analyzer ===
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
=== End of Report ==='''
    
    sample_transcript = [
        '{"type": "user", "message": {"text": "@perf_analyzer check performance"}}',
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": report_content}]}})
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-embedded-metadata',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    assistant_msg = messages[1] if len(messages) > 1 else None
    assert assistant_msg is not None
    assert assistant_msg.get('is_agent_report') == True
    
    # 验证嵌入的元数据被提取
    agent_metadata = assistant_msg.get('agent_metadata', {})
    assert agent_metadata.get('agent_name') == 'perf_analyzer'
    assert 'embedded_metadata' in agent_metadata
    assert agent_metadata.get('task_id') == 'pa-002-20250810'
    assert agent_metadata.get('execution_time') == '3.5'
    
    # 验证内部指标
    embedded = agent_metadata.get('embedded_metadata', {})
    assert embedded.get('internal_metrics', {}).get('files_analyzed') == 5
    
    Path(transcript_path).unlink()
    return True

def test_simple_format_report():
    """测试简化格式的Agent报告"""
    sample_transcript = [
        '{"type": "user", "message": {"text": "run security check"}}',
        '{"type": "assistant", "message": {"content": [{"type": "text", "text": "Agent Report: security_scanner\\n\\n✅ No vulnerabilities found\\n✅ All dependencies up to date\\n⚠️ Consider enabling 2FA"}]}}'
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-simple-format',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    assistant_msg = messages[1] if len(messages) > 1 else None
    assert assistant_msg is not None
    assert assistant_msg.get('is_agent_report') == True
    
    agent_metadata = assistant_msg.get('agent_metadata', {})
    assert agent_metadata.get('agent_name') == 'security_scanner'
    assert agent_metadata.get('format') == 'simple'
    
    Path(transcript_path).unlink()
    return True

def test_mention_format_report():
    """测试@mention格式的Agent报告"""
    sample_transcript = [
        '{"type": "user", "message": {"text": "check tests"}}',
        '{"type": "assistant", "message": {"content": [{"type": "text", "text": "@test_runner completed\\n\\nTest Results:\\n- Total: 50\\n- Passed: 48\\n- Failed: 2\\n- Coverage: 85%"}]}}'
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-mention-format',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    assistant_msg = messages[1] if len(messages) > 1 else None
    assert assistant_msg is not None
    assert assistant_msg.get('is_agent_report') == True
    
    agent_metadata = assistant_msg.get('agent_metadata', {})
    assert agent_metadata.get('agent_name') == 'test_runner'
    assert agent_metadata.get('format') == 'mention'
    
    Path(transcript_path).unlink()
    return True

def test_generic_agent_detection():
    """测试通用Agent检测（低置信度）"""
    sample_transcript = [
        '{"type": "user", "message": {"text": "analyze this"}}',
        '{"type": "assistant", "message": {"content": [{"type": "text", "text": "The analysis agent has completed the report. Here are the findings: Issue A, Issue B, and Issue C need attention."}]}}'
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-generic-detection',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    assistant_msg = messages[1] if len(messages) > 1 else None
    assert assistant_msg is not None
    assert assistant_msg.get('is_agent_report') == True
    
    agent_metadata = assistant_msg.get('agent_metadata', {})
    assert agent_metadata.get('format') == 'generic'
    assert agent_metadata.get('confidence') == 'low'
    
    Path(transcript_path).unlink()
    return True

def test_non_agent_message():
    """测试非Agent消息不被误识别"""
    sample_transcript = [
        '{"type": "user", "message": {"text": "what is the weather?"}}',
        '{"type": "assistant", "message": {"content": [{"type": "text", "text": "I cannot provide real-time weather information. Please check a weather website."}]}}'
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-non-agent',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    assistant_msg = messages[1] if len(messages) > 1 else None
    assert assistant_msg is not None
    assert assistant_msg.get('is_agent_report') == False
    assert assistant_msg.get('agent_metadata') is None
    
    Path(transcript_path).unlink()
    return True

def test_content_features_detection():
    """测试报告内容特征检测"""
    report_content = '''=== Security Audit Report by @security_agent ===
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

=== End of Report ==='''
    
    sample_transcript = [
        '{"type": "user", "message": {"text": "security audit"}}',
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": report_content}]}})
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write('\n'.join(sample_transcript))
        transcript_path = f.name
    
    hook = SageStopHook()
    input_data = {
        'session_id': 'test-content-features',
        'transcript_path': transcript_path
    }
    
    result = hook.process_claude_cli_jsonl(input_data)
    messages = result.get('messages', [])
    
    assistant_msg = messages[1] if len(messages) > 1 else None
    agent_metadata = assistant_msg.get('agent_metadata', {})
    
    # 验证内容特征检测
    features = agent_metadata.get('content_features', {})
    assert features.get('has_execution_id') == True
    assert features.get('has_metrics') == True
    assert features.get('has_errors') == True
    assert features.get('has_warnings') == True
    assert features.get('has_success') == True
    assert features.get('has_recommendations') == True
    
    # 验证完整性得分
    assert agent_metadata.get('completeness_score') == 1.0  # 所有特征都存在
    
    Path(transcript_path).unlink()
    return True

def run_all_tests():
    """运行所有测试"""
    print("=== Agent报告捕获功能测试 ===\n")
    
    tests = [
        ("标准格式报告", test_standard_format_report),
        ("嵌入元数据报告", test_embedded_metadata_report),
        ("简化格式报告", test_simple_format_report),
        ("@mention格式报告", test_mention_format_report),
        ("通用Agent检测", test_generic_agent_detection),
        ("非Agent消息过滤", test_non_agent_message),
        ("内容特征检测", test_content_features_detection)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name}: 通过")
                passed += 1
        except Exception as e:
            print(f"❌ {test_name}: 失败 - {e}")
            failed += 1
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{len(tests)}")
    print(f"失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！Agent报告捕获功能配置成功！")
        print("\n支持的报告格式：")
        print("1. 标准格式: === [Type] Report by @agent_name ===")
        print("2. 简化格式: Agent Report: agent_name")
        print("3. @mention格式: @agent_name ...")
        print("4. 嵌入元数据: <!-- AGENT_METADATA {...} -->")
        print("5. 通用检测: 包含agent和report关键词的内容")
    else:
        print("\n⚠️ 部分测试失败，请检查配置")

if __name__ == "__main__":
    run_all_tests()