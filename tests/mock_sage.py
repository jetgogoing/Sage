#!/usr/bin/env python3
"""
模拟 Claude CLI 用于测试
"""
import sys
import time

def main():
    args = sys.argv[1:]
    
    # 解析参数
    verbose = False
    print_mode = False
    debug = False
    user_input = None
    
    i = 0
    while i < len(args):
        if args[i] in ['--verbose']:
            verbose = True
            i += 1
        elif args[i] in ['-p', '--print']:
            print_mode = True
            i += 1
        elif args[i] in ['-d', '--debug']:
            debug = True
            i += 1
        elif args[i] in ['-h', '--help']:
            print("Mock Claude CLI - 用于测试")
            print("用法: mock_claude [选项] <输入>")
            print("选项:")
            print("  --verbose              详细输出")
            print("  -p, --print           打印模式")
            print("  -d, --debug           调试模式")
            print("  -h, --help            显示帮助")
            sys.exit(0)
        elif not args[i].startswith('-'):
            user_input = args[i]
            i += 1
        else:
            # 忽略未知选项
            i += 1
    
    if not user_input:
        print("错误：需要提供输入", file=sys.stderr)
        sys.exit(1)
    
    # 模拟流式输出
    if verbose:
        print("[Mock Claude CLI - 详细模式]", file=sys.stderr)
    if debug:
        print(f"[调试] 收到参数: {args}", file=sys.stderr)
    
    # 模拟打字效果
    response = f"""这是对您查询的响应："{user_input[:50]}..."

我理解您的问题。这是一个模拟的 Claude 响应，用于测试 Sage MCP 系统。

主要要点：
1. 参数已正确接收
2. Verbose 模式: {verbose}
3. Debug 模式: {debug}

这个响应将被 Sage MCP 系统捕获并存储到记忆数据库中。"""
    
    # 分行输出，模拟流式效果
    for line in response.split('\n'):
        print(line)
        sys.stdout.flush()
        time.sleep(0.05)  # 50ms 延迟
    
    print("\n[响应完成]")

if __name__ == "__main__":
    main()