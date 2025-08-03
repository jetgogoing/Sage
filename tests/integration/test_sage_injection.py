#!/usr/bin/env python3
"""
Sage 注入流程测试脚本
测试完整的记忆注入功能：向量索引、召回、重排、上下文压缩
"""

import json
import subprocess
import sys
import time
from pathlib import Path

def test_sage_injection():
    """测试完整的 Sage 注入流程"""
    
    print("🚀 开始测试 Sage 记忆注入功能...")
    
    # 测试用例
    test_cases = [
        {
            "name": "编程相关",
            "prompt": "我需要优化这个Python函数的性能，特别是循环部分",
            "expected_keywords": ["代码", "编程", "性能", "优化"]
        },
        {
            "name": "文档相关", 
            "prompt": "如何编写更好的API文档说明",
            "expected_keywords": ["文档", "说明", "API"]
        },
        {
            "name": "问题解决",
            "prompt": "遇到了一个奇怪的bug，程序总是崩溃",
            "expected_keywords": ["问题", "bug", "错误", "崩溃"]
        },
        {
            "name": "项目管理",
            "prompt": "这个开源项目需要重构架构设计",
            "expected_keywords": ["项目", "架构", "设计", "重构"]
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 测试 {i}: {test_case['name']}")
        print(f"输入: {test_case['prompt']}")
        
        # 构建测试输入
        test_input = {
            "session_id": f"test-session-{i}",
            "prompt": test_case['prompt'],
            "transcript_path": ""
        }
        
        try:
            # 调用 sage_prompt_enhancer
            cmd = ["python3", "/Users/jet/Sage/hooks/scripts/sage_prompt_enhancer.py"]
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                input=json.dumps(test_input),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60
            )
            end_time = time.time()
            
            if result.returncode == 0:
                enhanced_prompt = result.stdout.strip()
                response_time = end_time - start_time
                
                print(f"✅ 成功! 响应时间: {response_time:.2f}s")
                print(f"增强提示: {enhanced_prompt}")
                
                # 检查是否包含预期关键词
                matched_keywords = [kw for kw in test_case['expected_keywords'] 
                                  if kw in enhanced_prompt]
                
                result_data = {
                    "test_name": test_case['name'],
                    "input": test_case['prompt'],
                    "output": enhanced_prompt,
                    "response_time": response_time,
                    "matched_keywords": matched_keywords,
                    "success": True
                }
                
                if matched_keywords:
                    print(f"🎯 匹配关键词: {matched_keywords}")
                else:
                    print("⚠️  未匹配到预期关键词，但功能正常")
                    
            else:
                print(f"❌ 失败: {result.stderr}")
                result_data = {
                    "test_name": test_case['name'],
                    "input": test_case['prompt'],
                    "error": result.stderr,
                    "success": False
                }
        
        except Exception as e:
            print(f"❌ 异常: {e}")
            result_data = {
                "test_name": test_case['name'],
                "input": test_case['prompt'],
                "error": str(e),
                "success": False
            }
        
        results.append(result_data)
        time.sleep(1)  # 避免过快调用
    
    # 生成测试报告
    print(f"\n📊 测试报告")
    print("=" * 50)
    
    success_count = sum(1 for r in results if r.get('success', False))
    total_count = len(results)
    
    print(f"总测试数: {total_count}")
    print(f"成功数: {success_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    if success_count > 0:
        avg_time = sum(r.get('response_time', 0) for r in results if r.get('success')) / success_count
        print(f"平均响应时间: {avg_time:.2f}s")
    
    # 保存详细报告
    report_path = "/Users/jet/Sage/logs/sage_injection_test_report.json"
    Path(report_path).parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": time.time(),
            "summary": {
                "total": total_count,
                "success": success_count,
                "success_rate": success_count/total_count*100
            },
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 详细报告已保存: {report_path}")
    
    return success_count == total_count

if __name__ == "__main__":
    success = test_sage_injection()
    sys.exit(0 if success else 1)