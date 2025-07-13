#!/usr/bin/env python3
"""
Sage 全局记忆系统 - 精简包装器
目标：稳定、高可用的"全局聊天记忆系统"
"""

import os
import sys
import subprocess

# 递归保护（包装器最顶部）
if os.environ.get("SAGE_CLAUDE_WRAPPER_ACTIVE") == "1":
    real = os.environ.get("CLAUDE_CLI_PATH", "/usr/local/bin/claude")
    os.execvpe(real, [real] + sys.argv[1:], os.environ)

os.environ["SAGE_CLAUDE_WRAPPER_ACTIVE"] = "1"

# 导入核心模块
try:
    from memory import get_context, save_memory
    from config_manager import get_config_manager
except ImportError as e:
    print(f"[Sage] 导入模块失败: {e}", file=sys.stderr)
    # 直接调用原始 Claude
    real_claude = os.environ.get("CLAUDE_CLI_PATH", "/usr/local/bin/claude")
    os.execvpe(real_claude, [real_claude] + sys.argv[1:], os.environ)

def main():
    """主函数：记忆注入 + Claude 调用"""
    try:
        # 获取用户输入
        user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
        
        if not user_input:
            # 没有输入，直接调用 Claude
            real_claude = os.environ.get("CLAUDE_CLI_PATH", "/usr/local/bin/claude")
            os.execvpe(real_claude, [real_claude] + sys.argv[1:], os.environ)
        
        # 获取相关记忆上下文
        context = get_context(user_input)
        
        # 构造增强提示
        if context:
            enhanced_prompt = f"{context}\n\n当前查询：{user_input}"
        else:
            enhanced_prompt = user_input
        
        # 调用原始 Claude
        real_claude = os.environ.get("CLAUDE_CLI_PATH", "/usr/local/bin/claude")
        process = subprocess.run(
            [real_claude, enhanced_prompt],
            capture_output=True,
            text=True,
            env=os.environ
        )
        
        # 输出结果
        if process.stdout:
            print(process.stdout, end='')
        if process.stderr:
            print(process.stderr, end='', file=sys.stderr)
        
        # 保存对话记录
        if process.returncode == 0 and process.stdout:
            try:
                save_memory(user_input, "user")
                save_memory(process.stdout, "assistant")
            except Exception as e:
                print(f"[Sage] 保存记忆失败: {e}", file=sys.stderr)
        
        sys.exit(process.returncode)
        
    except Exception as e:
        print(f"[Sage] 执行错误: {e}", file=sys.stderr)
        # 错误时直接调用原始 Claude
        real_claude = os.environ.get("CLAUDE_CLI_PATH", "/usr/local/bin/claude")
        os.execvpe(real_claude, [real_claude] + sys.argv[1:], os.environ)

if __name__ == "__main__":
    main()