"""
邮箱验证服务 - 修复版
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
        
        # 直接从 st.secrets 读取
        sendgrid_api_key = st.secrets["SENDGRID_API_KEY"]
        from_email = st.secrets["SENDGRID_FROM_EMAIL"]
        
        subject = "【健身营养助手】邮箱验证码"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; border-radius: 10px;">
                    <h1 style="color: white; margin: 0;">💪 健身营养助手</h1>
                </div>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px;">
                    <p>您好！</p>
                    <p>您的验证码是：</p>
                    <div style="font-size: 32px; font-weight: bold; color: #667eea; text-align: center; padding: 20px; background: white; border-radius: 10px;">
                        {code}
                    </div>
                    <p>验证码有效期为10分钟，请尽快使用。</p>
                    <p>如果这不是您本人的操作，请忽略此邮件。</p>
                </div>
                <div style="text-align: center; color: #999; font-size: 12px; margin-top: 20px;">
                    <p>此邮件由系统自动发送，请勿回复</p>
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
        
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        
        if response.status_code in [200, 202]:
            return True, "验证码已发送，请查收邮件"
        else:
            return False, f"发送失败，状态码: {response.status_code}"
            
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
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; border-radius: 10px;">
                    <h1 style="color: white; margin: 0;">💪 健身营养助手</h1>
                </div>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px;">
                    <p>您好！</p>
                    <p>您正在申请重置密码，请点击下方链接：</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">点击重置密码</a>
                    </div>
                    <p>链接有效期为30分钟。</p>
                    <p>如果这不是您本人的操作，请忽略此邮件。</p>
                </div>
                <div style="text-align: center; color: #999; font-size: 12px; margin-top: 20px;">
                    <p>此邮件由系统自动发送，请勿回复</p>
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
        
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        return True, "重置邮件已发送" if response.status_code in [200, 202] else False, f"发送失败"
    except Exception as e:
        return False, f"发送失败: {str(e)}"
