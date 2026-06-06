"""
验证码服务模块
支持：邮件验证码（SendGrid）、短信验证码（阿里云）
"""

import random
import string
import os
from datetime import datetime, timedelta
import json

# 验证码存储（生产环境应使用Redis）
verification_codes = {}

def generate_code(length=6):
    """生成6位数字验证码"""
    return ''.join(random.choices(string.digits, k=length))

def save_code(key, code, expires_minutes=10):
    """保存验证码"""
    expires_at = datetime.now() + timedelta(minutes=expires_minutes)
    verification_codes[key] = {
        'code': code,
        'expires_at': expires_at,
        'attempts': 0
    }

def verify_code(key, code):
    """验证验证码"""
    if key not in verification_codes:
        return False, "验证码不存在或已过期"
    
    data = verification_codes[key]
    if datetime.now() > data['expires_at']:
        del verification_codes[key]
        return False, "验证码已过期"
    
    if data['attempts'] >= 5:
        del verification_codes[key]
        return False, "验证码错误次数过多"
    
    if data['code'] != code:
        data['attempts'] += 1
        return False, f"验证码错误，还剩{5 - data['attempts']}次机会"
    
    del verification_codes[key]
    return True, "验证成功"

# ==================== 邮件服务（SendGrid）====================
def send_email_via_sendgrid(to_email, code):
    """使用 SendGrid 发送邮件验证码"""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        api_key = os.environ.get('SENDGRID_API_KEY')
        from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@fitnessapp.com')
        
        if not api_key:
            return False, "邮件服务未配置"
        
        subject = "【健身营养助手】邮箱验证码"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .code {{ font-size: 32px; font-weight: bold; color: #667eea; padding: 20px; text-align: center; }}
                .footer {{ color: #999; font-size: 12px; text-align: center; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>💪 健身营养助手</h2>
                <p>您好！</p>
                <p>您正在注册/登录健身营养助手，验证码如下：</p>
                <div class="code">{code}</div>
                <p>验证码有效期为10分钟，请尽快使用。</p>
                <p>如果这不是您本人的操作，请忽略此邮件。</p>
                <div class="footer">
                    <p>此邮件由系统自动发送，请勿回复</p>
                    <p>&copy; 2024 健身营养助手</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        if response.status_code in [200, 202]:
            return True, "验证码已发送"
        else:
            return False, f"发送失败: {response.status_code}"
            
    except Exception as e:
        return False, f"发送失败: {str(e)}"

# ==================== 短信服务（阿里云）====================
def send_sms_via_aliyun(phone, code):
    """使用阿里云短信服务发送验证码"""
    try:
        from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
        
        access_key_id = os.environ.get('ALIYUN_ACCESS_KEY_ID')
        access_key_secret = os.environ.get('ALIYUN_ACCESS_KEY_SECRET')
        sign_name = os.environ.get('ALIYUN_SMS_SIGN_NAME', '健身营养助手')
        template_code = os.environ.get('ALIYUN_SMS_TEMPLATE_CODE', 'SMS_00000000')
        
        if not access_key_id or not access_key_secret:
            return False, "短信服务未配置"
        
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret
        )
        config.endpoint = 'dysmsapi.aliyuncs.com'
        
        client = DysmsapiClient(config)
        
        request = dysmsapi_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=sign_name,
            template_code=template_code,
            template_param=f'{{"code":"{code}"}}'
        )
        
        response = client.send_sms(request)
        
        if response.body.code == 'OK':
            return True, "验证码已发送"
        else:
            return False, f"发送失败: {response.body.message}"
            
    except Exception as e:
        return False, f"发送失败: {str(e)}"

# ==================== 演示模式（开发/测试用）====================
def send_demo_code(contact, code, method='email'):
    """演示模式：打印验证码到控制台"""
    print(f"\n{'='*50}")
    print(f"【演示模式】{method}验证码")
    print(f"接收方: {contact}")
    print(f"验证码: {code}")
    print(f"有效期: 10分钟")
    print(f"{'='*50}\n")
    return True, "验证码已发送（演示模式）"

# ==================== 统一发送接口 ====================
def send_verification_code(contact, method='email'):
    """
    发送验证码
    method: 'email' 或 'sms'
    """
    code = generate_code()
    key = f"{method}:{contact}"
    
    # 检查发送频率（60秒内不能重复发送）
    if key in verification_codes:
        last_send = verification_codes.get(f"{key}:sent_at")
        if last_send and (datetime.now() - last_send).seconds < 60:
            return False, "发送太频繁，请60秒后再试"
    
    # 根据方法选择发送渠道
    if method == 'email':
        # 优先使用真实邮件服务，否则用演示模式
        if os.environ.get('SENDGRID_API_KEY'):
            success, msg = send_email_via_sendgrid(contact, code)
        else:
            success, msg = send_demo_code(contact, code, 'email')
    elif method == 'sms':
        # 优先使用真实短信服务，否则用演示模式
        if os.environ.get('ALIYUN_ACCESS_KEY_ID'):
            success, msg = send_sms_via_aliyun(contact, code)
        else:
            success, msg = send_demo_code(contact, code, 'sms')
    else:
        return False, "不支持的发送方式"
    
    if success:
        save_code(key, code)
        verification_codes[f"{key}:sent_at"] = datetime.now()
    
    return success, msg

def verify_verification_code(contact, code, method='email'):
    """验证验证码"""
    key = f"{method}:{contact}"
    return verify_code(key, code)

# 导出函数
__all__ = [
    'send_verification_code',
    'verify_verification_code',
    'send_email_via_sendgrid',
    'send_sms_via_aliyun'
]
