#!/usr/bin/env python3
"""
测试通过MCP接口调用断路器重置功能
"""
import asyncio
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_mcp_reset():
    """测试MCP重置功能"""
    print("=== 测试MCP断路器重置接口 ===")
    
    try:
        # 导入并初始化MCP服务器
        from sage_mcp_stdio_single import SageMCPStdioServerV3
        from sage_core.resilience import breaker_manager
        from sage_core.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        
        # 创建测试断路器
        config = CircuitBreakerConfig(failure_threshold=2)
        test_breaker = CircuitBreaker('mcp_test_breaker', config)
        breaker_manager.register(test_breaker)
        
        print("1. 注册测试断路器完成")
        
        # 让断路器进入故障状态
        try:
            for i in range(3):
                try:
                    test_breaker.call(lambda: exec('raise Exception("模拟MCP测试失败")'))
                except:
                    pass
        except:
            pass
        
        print("2. 断路器当前状态:")
        stats = breaker_manager.get_all_stats()
        for stat in stats:
            state_emoji = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}
            emoji = state_emoji.get(stat['state'], "⚪")
            print(f"   {emoji} {stat['name']}: {stat['state']}")
        
        # 创建MCP服务器实例
        server_instance = SageMCPStdioServerV3()
        
        # 模拟MCP调用 - 重置所有断路器
        print("\n3. 通过MCP接口重置所有断路器...")
        
        # 手动调用工具处理函数
        tools_handler = None
        for handler_name, handler_func in server_instance.server._request_handlers.items():
            if 'call' in handler_name.lower():
                tools_handler = handler_func
                break
        
        if tools_handler:
            try:
                result = await tools_handler("reset_circuit_breaker", {"all": True})
                print("MCP调用结果:")
                for item in result:
                    print(f"   {item.text}")
            except Exception as e:
                print(f"   MCP调用失败: {e}")
        else:
            print("   未找到MCP工具处理器")
        
        print("\n4. 重置后断路器状态:")
        stats = breaker_manager.get_all_stats()
        for stat in stats:
            state_emoji = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}
            emoji = state_emoji.get(stat['state'], "⚪")
            print(f"   {emoji} {stat['name']}: {stat['state']}")
        
        print("\n✅ MCP断路器重置接口测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_reset())