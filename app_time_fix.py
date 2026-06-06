# 时区修复代码 - 添加到 app.py 中替换原有的 get_current_time 函数
import time
import pytz
from datetime import datetime

def get_current_time():
    """获取当前本地时间（自动根据系统时区）"""
    # 获取本地时区
    local_tz = time.tzname[0]  # 获取本地时区名称
    # 使用系统本地时间
    now = datetime.now()
    return now.strftime("%H:%M")

def get_current_datetime():
    """获取完整的本地日期时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
