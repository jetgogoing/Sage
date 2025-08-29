#!/usr/bin/env python3
"""
测试断路器重置功能的脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_core.resilience import breaker_manager
from sage_core.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


async def test_circuit_breaker_reset():
    """测试断路器重置功能"""
    print("=== 断路器重置功能测试 ===")
    
    # 1. 创建测试断路器
    config = CircuitBreakerConfig(failure_threshold=2)
    test_breaker1 = CircuitBreaker('test_database', config)
    test_breaker2 = CircuitBreaker('test_api', config)
    
    breaker_manager.register(test_breaker1)
    breaker_manager.register(test_breaker2)
    
    print("1. 初始状态:")
    stats = breaker_manager.get_all_stats()
    for stat in stats:
        print(f"   {stat['name']}: {stat['state']}")
    
    # 2. 模拟断路器触发
    try:
        # 让test_database断路器失败几次
        for i in range(3):
            try:
                test_breaker1.call(lambda: exec('raise Exception("模拟失败")'))
            except:
                pass
    except:
        pass
    
    print("\n2. 模拟失败后状态:")
    stats = breaker_manager.get_all_stats()
    for stat in stats:
        state_emoji = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}
        emoji = state_emoji.get(stat['state'], "⚪")
        print(f"   {emoji} {stat['name']}: {stat['state']} (失败次数: {stat['failure_count']})")
    
    # 3. 测试重置功能
    print("\n3. 执行重置操作...")
    breaker_manager.reset_all()
    
    print("\n4. 重置后状态:")
    stats = breaker_manager.get_all_stats()
    for stat in stats:
        state_emoji = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}
        emoji = state_emoji.get(stat['state'], "⚪")
        print(f"   {emoji} {stat['name']}: {stat['state']} (失败次数: {stat['failure_count']})")
    
    # 4. 测试单个断路器重置
    print("\n5. 测试单个断路器重置...")
    # 让test_api失败
    try:
        for i in range(3):
            try:
                test_breaker2.call(lambda: exec('raise Exception("模拟API失败")'))
            except:
                pass
    except:
        pass
    
    print("   test_api失败后:")
    breaker = breaker_manager.get('test_api')
    if breaker:
        stat = breaker.get_stats()
        print(f"   🔴 {stat['name']}: {stat['state']}")
    
    # 重置单个断路器
    if breaker:
        breaker.reset()
        stat = breaker.get_stats()
        print(f"   重置后: 🟢 {stat['name']}: {stat['state']}")
    
    print("\n✅ 断路器重置功能测试完成！")


if __name__ == "__main__":
    asyncio.run(test_circuit_breaker_reset())