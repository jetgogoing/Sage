#!/usr/bin/env python3
"""
Sage MCP 轻量化记忆系统 - Claude CLI 注入器

功能说明：
- 作为 Claude CLI 的包装器，拦截用户输入并注入历史上下文
- 使用 subprocess 调用原始 claude 命令，保持完全兼容性
- 自动保存每次对话到数据库供未来检索

使用方法：
1. 设置 alias: alias claude='python /path/to/claude_mem.py'
2. 正常使用: claude "你的查询"

作者：Sage MCP 项目组
"""

import sys
import os
import subprocess
import json
from dotenv import load_dotenv
from memory import get_context, save_memory

# 加载环境变量
load_dotenv()

# Claude CLI 可执行文件路径
CLAUDE_CLI_PATH = os.getenv('CLAUDE_CLI_PATH', '/home/jetgogoing/.nvm/versions/node/v18.20.8/bin/claude')

def inject_memory_context(user_input):
    """
    主要的注入逻辑：
    1. 获取历史上下文
    2. 构造带上下文的提示
    3. 调用原始 claude 命令
    4. 保存对话记录
    """
    try:
        # 获取相关历史上下文
        context = get_context(user_input)
        
        # 构造增强的提示
        if context:
            enhanced_prompt = f"{context}\n\n当前查询：{user_input}"
        else:
            enhanced_prompt = user_input
        
        # 调用原始 claude 命令
        # 注意：这里使用 subprocess 调用原始 claude CLI
        cmd = [CLAUDE_CLI_PATH] + sys.argv[1:]
        
        # 替换用户输入为增强版本
        for i, arg in enumerate(cmd):
            if arg == user_input:
                cmd[i] = enhanced_prompt
                break
        
        # 执行命令并实时输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # 收集输出用于保存
        full_output = []
        
        # 实时输出并收集响应
        for line in process.stdout:
            print(line, end='')
            full_output.append(line)
        
        process.wait()
        
        # 保存完整对话到数据库
        claude_response = ''.join(full_output)
        save_memory(user_input, claude_response)
        
        return process.returncode
        
    except Exception as e:
        print(f"记忆系统错误: {e}", file=sys.stderr)
        # 出错时直接调用原始命令
        return subprocess.call([CLAUDE_CLI_PATH] + sys.argv[1:])

def main():
    """主入口：拦截 claude 命令并注入记忆功能"""
    if len(sys.argv) < 2:
        # 无参数时直接传递给原始 claude
        return subprocess.call([CLAUDE_CLI_PATH])
    
    # 提取用户输入（最后一个参数通常是查询内容）
    # TODO: 需要更智能地解析 claude CLI 的参数格式
    user_input = None
    for arg in reversed(sys.argv[1:]):
        if not arg.startswith('-'):
            user_input = arg
            break
    
    if user_input:
        return inject_memory_context(user_input)
    else:
        # 没有检测到查询内容，直接传递
        return subprocess.call([CLAUDE_CLI_PATH] + sys.argv[1:])

if __name__ == "__main__":
    sys.exit(main())