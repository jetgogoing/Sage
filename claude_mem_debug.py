#!/usr/bin/env python3
"""调试版本的claude_mem_v3.py - 添加详细日志"""

import sys
import os

# 清除递归保护
if 'SAGE_RECURSION_GUARD' in os.environ:
    del os.environ['SAGE_RECURSION_GUARD']

print(f"[DEBUG] Python版本: {sys.version}")
print(f"[DEBUG] 脚本路径: {__file__}")
print(f"[DEBUG] 参数: {sys.argv}")

# 导入主模块前先设置调试模式
os.environ['SAGE_DEBUG'] = '1'

print("[DEBUG] 开始导入claude_mem_v3模块...")

try:
    # 添加路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # 导入必要的模块
    from claude_mem_v3 import ImprovedCrossplatformClaude, ParsedArgs
    
    print("[DEBUG] 导入成功，创建应用实例...")
    app = ImprovedCrossplatformClaude()
    
    print("[DEBUG] 查找Claude可执行文件...")
    claude_path = app.find_claude_executable()
    print(f"[DEBUG] Claude路径: {claude_path}")
    
    if not claude_path:
        print("[DEBUG] 未找到Claude，尝试使用环境变量中的路径...")
        claude_path = os.getenv('ORIGINAL_CLAUDE_PATH', '/Users/jet/.claude/local/claude')
        print(f"[DEBUG] 使用路径: {claude_path}")
    
    # 解析参数
    print("[DEBUG] 解析参数...")
    args = sys.argv[1:] if len(sys.argv) > 1 else ["测试消息"]
    parsed = app.parse_arguments_improved(args)
    print(f"[DEBUG] 解析结果: user_prompt='{parsed.user_prompt}', claude_args={parsed.claude_args}")
    
    # 检查记忆配置
    print("[DEBUG] 检查记忆配置...")
    memory_enabled = app.get_config('memory_enabled', True)
    print(f"[DEBUG] 记忆功能启用: {memory_enabled}")
    
    # 测试记忆提供者
    print("[DEBUG] 获取记忆提供者...")
    try:
        provider = app.memory_provider
        print(f"[DEBUG] 记忆提供者类型: {type(provider).__name__}")
    except Exception as e:
        print(f"[DEBUG] 获取记忆提供者失败: {e}")
        provider = None
    
    # 如果有用户输入，尝试获取上下文
    if parsed.user_prompt and provider:
        print("[DEBUG] 尝试获取记忆上下文...")
        try:
            context = provider.get_context(parsed.user_prompt)
            print(f"[DEBUG] 获取到上下文长度: {len(context) if context else 0}")
        except Exception as e:
            print(f"[DEBUG] 获取上下文失败: {e}")
    
    # 执行命令
    if claude_path and os.path.exists(claude_path):
        print(f"[DEBUG] 准备执行Claude命令...")
        import subprocess
        
        cmd = [claude_path] + parsed.claude_args
        if parsed.user_prompt:
            cmd.append(parsed.user_prompt)
        
        print(f"[DEBUG] 执行命令: {' '.join(cmd)}")
        
        # 使用subprocess.PIPE捕获输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("[DEBUG] 等待Claude响应...")
        stdout, stderr = process.communicate(timeout=30)
        
        print(f"[DEBUG] 返回码: {process.returncode}")
        print(f"[DEBUG] 标准输出长度: {len(stdout)}")
        print(f"[DEBUG] 错误输出长度: {len(stderr)}")
        
        if stdout:
            print("[DEBUG] Claude响应预览:")
            print(stdout[:200] + "..." if len(stdout) > 200 else stdout)
        
        if stderr:
            print("[DEBUG] 错误输出:")
            print(stderr)
        
        # 保存对话
        if parsed.user_prompt and stdout and provider:
            print("[DEBUG] 尝试保存对话...")
            try:
                provider.save_conversation(parsed.user_prompt, stdout)
                print("[DEBUG] 对话保存成功")
            except Exception as e:
                print(f"[DEBUG] 保存对话失败: {e}")
                import traceback
                traceback.print_exc()
    else:
        print(f"[DEBUG] Claude路径不存在: {claude_path}")
        
except Exception as e:
    print(f"[DEBUG] 发生错误: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("[DEBUG] 调试完成")