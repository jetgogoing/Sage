#!/usr/bin/env python3
"""测试执行流程"""

import sys
import os
import logging

# 清除递归保护环境变量
if 'SAGE_RECURSION_GUARD' in os.environ:
    del os.environ['SAGE_RECURSION_GUARD']

# 设置调试环境变量
os.environ['SAGE_DEBUG'] = '1'

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 添加路径
sys.path.insert(0, '/Volumes/1T HDD/Sage')

print("===== 开始测试执行流程 =====")

# 模拟运行 sage_minimal.py
import sage_minimal

# 创建实例
app = sage_minimal.ImprovedCrossplatformClaude()

# 测试参数
test_args = ["测试家庭信息：我的家人有吴鹏、李诗韵、吴宇恒、吴宇晨"]

print(f"\n测试参数: {test_args}")

# 执行
try:
    result = app.run(test_args)
    print(f"\n执行结果代码: {result}")
except Exception as e:
    print(f"\n执行出错: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n===== 测试完成 =====")