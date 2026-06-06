"""
邮箱验证和密码找回服务
"""

import streamlit as st
import random
import string
from datetime import datetime, timedelta
import hashlib

def generate_code(length=6):
    """生成6位数字验证码"""
    return ''.join(random.choices(string.digits, k=length))

def generate_token():
    """生成重置令牌"""
    return hashlib.sha256(f"{datetime.now()}{random.random()}".encode()).hexdigest()[:32]

def send_verification_email(to_email, code):
    """发送邮箱验证码"""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        sendgrid_api_key = st.secrets["SENDGRID_API_KEY"]
        from_email = st.secrets["SENDGRID_FROM_EMAIL"]
        
        subject = "【健身营养助手】邮箱验证码"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body>
            <h2>💪 健身营养助手</h2>
            <p>您的邮箱验证码是：</p>
            <h1 style="color: #667eea;">{code}</h1>
            <p>验证码有效期为10分钟，请尽快验证。</p>
            <p>如果这不是您本人的操作，请忽略此邮件。</p>
        </body>
        </html>
        """
        
        message = Mail(from_email=from_email, to_emails=to_email, subject=subject, html_content=html_content)
        sg = SendGridAPIClient(sendgrid_api_key)
        sg.send(message)
        return True, "验证码已发送"
    except Exception as e:
        return False, f"发送失败: {str(e)}"

def send_reset_email(to_email, reset_link):
    """发送密码重置邮件"""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        sendgrid_api_key = st.secrets["SENDGRID_API_KEY"]
        from_email = st.secrets["SENDGRID_FROM_EMAIL"]
        
        subject = "【健身营养助手】密码重置"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body>
            <h2>💪 健身营养助手</h2>
            <p>您正在申请重置密码，请点击下方链接：</p>
            <p><a href="{reset_link}" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">点击重置密码</a></p>
            <p>链接有效期为30分钟。</p>
            <p>如果这不是您本人的操作，请忽略此邮件。</p>
        </body>
        </html>
        """
        
        message = Mail(from_email=from_email, to_emails=to_email, subject=subject, html_content=html_content)
        sg = SendGridAPIClient(sendgrid_api_key)
        sg.send(message)
        return True, "重置邮件已发送"
    except Exception as e:
        return False, f"发送失败: {str(e)}"
