#!/usr/bin/env python3
"""
简单测试断路器重置功能
"""
import asyncio
import sys
import os
import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_core.resilience import breaker_manager
from sage_core.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


def simulate_mcp_reset_tool(all=True, breaker_name=None):
    """模拟MCP重置工具的逻辑"""
    # 记录操作前状态
    stats_before = breaker_manager.get_all_stats()
    
    # 执行重置
    if all:
        breaker_manager.reset_all()
        operation = "重置所有断路器"
    elif breaker_name:
        breaker = breaker_manager.get(breaker_name)
        if breaker:
            breaker.reset()
            operation = f"重置断路器: {breaker_name}"
        else:
            return f"错误: 断路器 '{breaker_name}' 不存在"
    else:
        return "错误: 必须指定 all=True 或提供 breaker_name"
    
    # 记录操作后状态
    stats_after = breaker_manager.get_all_stats()
    
    # 记录到日志文件
    log_dir = os.path.join(os.getenv('SAGE_HOME', '.'), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_entry = f"[{datetime.datetime.now()}] {operation}\n"
    log_file = os.path.join(log_dir, 'circuit_breaker_reset.log')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    
    # 构建响应
    response = [f"✅ {operation}已完成\n"]
    response.append("断路器状态:")
    for stat in stats_after:
        state_emoji = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}
        emoji = state_emoji.get(stat['state'], "⚪")
        response.append(f"  {emoji} {stat['name']}: {stat['state']}")
    
    response.append(f"\n操作已记录到: {log_file}")
    
    return "\n".join(response)


async def test_simple_reset():
    """测试简单重置功能"""
    print("=== 简单断路器重置测试 ===")
    
    # 1. 创建测试断路器
    config = CircuitBreakerConfig(failure_threshold=2)
    test_breaker1 = CircuitBreaker('database_test', config)
    test_breaker2 = CircuitBreaker('api_test', config)
    
    breaker_manager.register(test_breaker1)
    breaker_manager.register(test_breaker2)
    
    print("1. 初始状态:")
    stats = breaker_manager.get_all_stats()
    for stat in stats:
        print(f"   {stat['name']}: {stat['state']}")
    
    # 2. 让断路器进入故障状态
    print("\n2. 模拟断路器故障...")
    try:
        for i in range(3):
            try:
                test_breaker1.call(lambda: exec('raise Exception("数据库连接失败")'))
            except:
                pass
    except:
        pass
    
    try:
        for i in range(3):
            try:
                test_breaker2.call(lambda: exec('raise Exception("API调用失败")'))
            except:
                pass
    except:
        pass
    
    print("故障后状态:")
    stats = breaker_manager.get_all_stats()
    for stat in stats:
        state_emoji = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}
        emoji = state_emoji.get(stat['state'], "⚪")
        print(f"   {emoji} {stat['name']}: {stat['state']}")
    
    # 3. 测试重置所有断路器
    print("\n3. 调用重置所有断路器...")
    result = simulate_mcp_reset_tool(all=True)
    print(result)
    
    # 4. 测试重置单个断路器
    print("\n4. 再次模拟单个断路器故障...")
    try:
        for i in range(3):
            try:
                test_breaker1.call(lambda: exec('raise Exception("数据库再次失败")'))
            except:
                pass
    except:
        pass
    
    print("5. 重置单个断路器...")
    result = simulate_mcp_reset_tool(all=False, breaker_name='database_test')
    print(result)
    
    print("\n✅ 所有测试完成！")


if __name__ == "__main__":
    asyncio.run(test_simple_reset())