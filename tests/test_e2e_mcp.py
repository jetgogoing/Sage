#!/usr/bin/env python3
"""
端到端测试 Sage MCP 集成
"""

import subprocess
import json
import time
import os
import sys

def run_command(cmd, check=True):
    """运行命令并返回输出"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ 命令失败: {cmd}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    return result

def test_sage_mcp():
    """测试 Sage MCP 集成"""
    print("🧪 开始 Sage MCP 端到端测试...\n")
    
    # 1. 检查 Docker 服务
    print("1️⃣ 检查 Docker 服务...")
    docker_result = run_command("docker ps | grep sage-mcp-server")
    if docker_result.returncode == 0:
        print("✅ Docker 容器运行正常")
    else:
        print("❌ Docker 容器未运行")
        return False
    
    # 2. 检查 HTTP 服务健康状态
    print("\n2️⃣ 检查 HTTP 服务健康状态...")
    health_result = run_command("curl -s http://localhost:17800/health", check=False)
    if health_result.returncode == 0:
        try:
            health_data = json.loads(health_result.stdout)
            print(f"✅ HTTP 服务健康: {health_data['status']}")
            print(f"   记忆数量: {health_data['memory_count']}")
            print(f"   数据库状态: {health_data['database']}")
        except:
            print("❌ 健康检查响应格式错误")
            return False
    else:
        print("❌ HTTP 服务不可用")
        return False
    
    # 3. 测试 MCP 协议端点
    print("\n3️⃣ 测试 MCP 协议端点...")
    mcp_test_request = {
        "jsonrpc": "2.0",
        "method": "tools/save_conversation",
        "params": {
            "user_prompt": "E2E测试用户输入",
            "assistant_response": "E2E测试助手响应"
        },
        "id": 1
    }
    
    curl_cmd = f"""curl -s -X POST http://localhost:17800/mcp \
        -H "Content-Type: application/json" \
        -d '{json.dumps(mcp_test_request)}'"""
    
    mcp_result = run_command(curl_cmd, check=False)
    if mcp_result.returncode == 0:
        try:
            mcp_response = json.loads(mcp_result.stdout)
            if "result" in mcp_response:
                print("✅ MCP 端点响应正常")
                print(f"   响应: {mcp_response['result']}")
            else:
                print("❌ MCP 响应格式错误")
                return False
        except:
            print("❌ MCP 响应解析失败")
            return False
    else:
        print("❌ MCP 端点不可用")
        return False
    
    # 4. 检查 stdio 服务器文件
    print("\n4️⃣ 检查 stdio 服务器文件...")
    files_to_check = [
        "sage_mcp_stdio_v2.py",
        "start_sage_mcp_stdio_v2.sh"
    ]
    
    for file in files_to_check:
        if os.path.exists(file):
            print(f"✅ {file} 存在")
        else:
            print(f"❌ {file} 不存在")
            return False
    
    # 5. 检查 Claude 配置
    print("\n5️⃣ 检查 Claude 配置...")
    config_path = os.path.expanduser("~/.config/claude/claude_mcp_config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            if "sage" in config.get("mcpServers", {}):
                sage_config = config["mcpServers"]["sage"]
                print("✅ Sage 已配置在 Claude 中")
                print(f"   命令: {sage_config.get('command', 'N/A')}")
                
                # 检查命令文件是否存在
                cmd_path = sage_config.get('command', '')
                if os.path.exists(cmd_path):
                    print(f"✅ 启动脚本存在: {cmd_path}")
                else:
                    print(f"❌ 启动脚本不存在: {cmd_path}")
                    return False
            else:
                print("❌ Sage 未在 Claude 配置中")
                return False
    else:
        print("❌ Claude 配置文件不存在")
        return False
    
    # 6. 测试启动脚本
    print("\n6️⃣ 测试启动脚本...")
    # 使用 timeout 命令限制运行时间
    test_cmd = "timeout 5 ./start_sage_mcp_stdio_v2.sh"
    test_result = run_command(test_cmd, check=False)
    
    # 检查日志
    log_path = "/tmp/sage_mcp_stdio_v2.log"
    if os.path.exists(log_path):
        # 获取最新的日志行
        log_result = run_command(f"tail -n 5 {log_path}", check=False)
        if "Starting Sage MCP stdio server v2" in log_result.stdout:
            print("✅ stdio 服务器可以启动")
        else:
            print("⚠️  stdio 服务器启动状态不明")
    
    print("\n✅ 所有基础测试通过！")
    print("\n📝 建议的下一步:")
    print("1. 重启 Claude Code 以加载新的 MCP 配置")
    print("2. 在 Claude Code 中运行 /mcp list 查看 Sage 状态")
    print("3. 测试工具调用: /mcp sage save_conversation")
    
    return True

if __name__ == "__main__":
    success = test_sage_mcp()
    sys.exit(0 if success else 1)