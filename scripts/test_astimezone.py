#!/usr/bin/env python3
"""
测试 astimezone() 的行为
"""

from datetime import datetime, timezone, timedelta

# 模拟从数据库获取的 UTC 时间
utc_time = datetime(2025, 8, 3, 15, 26, 24, tzinfo=timezone.utc)
print(f"原始 UTC 时间: {utc_time}")
print(f"ISO 格式: {utc_time.isoformat()}")

# 使用 astimezone() 不带参数 - 转换为本地时区
local_time = utc_time.astimezone()
print(f"\nastimezone() 后: {local_time}")
print(f"ISO 格式: {local_time.isoformat()}")
print(f"时区名称: {local_time.tzname()}")
print(f"UTC 偏移: {local_time.utcoffset()}")

# 验证系统时区
import time
print(f"\n系统时区: {time.tzname}")
print(f"当前系统时间: {datetime.now()}")
print(f"当前系统时间(带时区): {datetime.now().astimezone()}")