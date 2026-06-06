# 添加到 app.py 开头的时区修复
from datetime import datetime
import pytz

def get_current_time():
    """获取中国本地时间（东八区）"""
    # 使用东八区时间（中国标准时间）
    china_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(china_tz)
    return now.strftime("%H:%M")

def get_current_datetime():
    """获取完整的中文日期时间"""
    china_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(china_tz)
    return now.strftime("%Y-%m-%d %H:%M:%S")
