#!/usr/bin/env python3
"""
Claude MCP 最小化版本 - 用于调试
"""

import sys
import os
import subprocess

print(f"[MINIMAL] 启动，参数: {sys.argv}", file=sys.stderr)

# 递归保护检查
if os.getenv('SAGE_RECURSION_GUARD') == '1':
    print("[MINIMAL] 检测到递归调用，直接传递给原始 Claude", file=sys.stderr)
    sys.exit(0)

print("[MINIMAL] 通过递归保护检查", file=sys.stderr)

# 简单参数解析
if '--version' in sys.argv:
    print("[MINIMAL] 版本检查模式", file=sys.stderr)
    # 直接调用原始claude
    claude_path = '/Users/jet/.claude/local/node_modules/.bin/claude'
    result = subprocess.run([claude_path, '--version'], capture_output=True, text=True)
    print(result.stdout)
    sys.exit(result.returncode)

if '-p' in sys.argv:
    print("[MINIMAL] 非交互模式", file=sys.stderr)
    try:
        prompt_index = sys.argv.index('-p') + 1
        if prompt_index < len(sys.argv):
            prompt = sys.argv[prompt_index]
            print(f"[MINIMAL] 提示词: {prompt}", file=sys.stderr)
            
            # 直接调用原始claude
            claude_path = '/Users/jet/.claude/local/node_modules/.bin/claude'
            env = os.environ.copy()
            env['SAGE_RECURSION_GUARD'] = '1'  # 设置递归保护
            
            print(f"[MINIMAL] 调用 {claude_path} -p", file=sys.stderr)
            result = subprocess.run(
                [claude_path, '-p'], 
                input=prompt,
                text=True,
                env=env,
                timeout=30
            )
            sys.exit(result.returncode)
        else:
            print("[MINIMAL] 错误：缺少提示词", file=sys.stderr)
            sys.exit(1)
    except subprocess.TimeoutExpired:
        print("[MINIMAL] 超时！", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[MINIMAL] 异常: {e}", file=sys.stderr)
        sys.exit(1)

print("[MINIMAL] 默认：启动交互模式", file=sys.stderr)
# 对于其他情况，直接传递给原始claude
claude_path = '/Users/jet/.claude/local/node_modules/.bin/claude'
env = os.environ.copy()
env['SAGE_RECURSION_GUARD'] = '1'  # 设置递归保护
os.execve(claude_path, ['claude'] + sys.argv[1:], env)