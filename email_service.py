"""
邮件发送服务 - 使用 SendGrid
"""

import streamlit as st
from datetime import datetime, date
import pandas as pd

def send_daily_report_email(to_email, user_name, food_records, exercise_records, total_calories, total_burned, daily_target):
    """发送每日报告邮件"""
    
    # 获取 SendGrid 配置
    try:
        sendgrid_api_key = st.secrets["SENDGRID_API_KEY"]
        from_email = st.secrets["SENDGRID_FROM_EMAIL"]
    except:
        return False, "邮件服务未配置，请在 Secrets 中添加 SENDGRID_API_KEY 和 SENDGRID_FROM_EMAIL"
    
    if not sendgrid_api_key or sendgrid_api_key == "你的SendGrid_API_Key":
        return False, "请先配置 SendGrid API Key"
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
        
        today_str = date.today().strftime("%Y-%m-%d")
        
        # 构建邮件内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 10px; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .section {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 10px; }}
                .section h2 {{ color: #667eea; margin-top: 0; }}
                .food-item, .exercise-item {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
                .summary {{ background: #e8f4f8; padding: 15px; border-radius: 10px; margin: 20px 0; }}
                .summary-item {{ display: inline-block; width: 30%; text-align: center; }}
                .summary-number {{ font-size: 24px; font-weight: bold; color: #667eea; }}
                .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
                .progress-bar {{ background: #e0e0e0; border-radius: 10px; height: 20px; margin: 10px 0; }}
                .progress-fill {{ background: #4ecdc4; border-radius: 10px; height: 20px; width: 0%; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💪 健身营养助手</h1>
                    <p>每日健康报告 - {today_str}</p>
                </div>
                
                <div class="summary">
                    <div class="summary-item">
                        <div class="summary-number">{total_calories:.0f}</div>
                        <div>🍽️ 摄入热量</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-number">{total_burned:.0f}</div>
                        <div>🏋️ 消耗热量</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-number">{total_calories - total_burned:.0f}</div>
                        <div>📊 净摄入</div>
                    </div>
                </div>
                
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {min(100, (total_calories / daily_target * 100))}%;"></div>
                </div>
                <p style="text-align: center;">目标进度: {min(100, (total_calories / daily_target * 100)):.0f}%</p>
        """
        
        # 添加饮食记录
        if food_records:
            html_content += """
                <div class="section">
                    <h2>🍽️ 今日饮食记录</h2>
            """
            for f in food_records:
                html_content += f"""
                    <div class="food-item">
                        <strong>{f.get('meal', '')}</strong> - {f.get('food_name', '')} | {f.get('quantity', 0)}g | {f.get('calories', 0):.0f} kcal | 蛋白质 {f.get('protein', 0):.0f}g
                    </div>
                """
            html_content += "</div>"
        else:
            html_content += """
                <div class="section">
                    <h2>🍽️ 今日饮食记录</h2>
                    <p>暂无饮食记录</p>
                </div>
            """
        
        # 添加运动记录
        if exercise_records:
            html_content += """
                <div class="section">
                    <h2>🏋️ 今日运动记录</h2>
            """
            for e in exercise_records:
                html_content += f"""
                    <div class="exercise-item">
                        {e.get('exercise_name', '')} | {e.get('duration', 0)}分钟 | 消耗 {e.get('calories', 0):.0f} kcal
                    </div>
                """
            html_content += "</div>"
        else:
            html_content += """
                <div class="section">
                    <h2>🏋️ 今日运动记录</h2>
                    <p>暂无运动记录</p>
                </div>
            """
        
        # 添加健康建议
        net = total_calories - total_burned
        if net > 300:
            advice = "⚠️ 今日摄入偏高，建议增加运动或控制饮食"
        elif net < -100:
            advice = "💪 今日消耗较大，注意补充营养"
        else:
            advice = "✅ 今日饮食控制良好，继续保持！"
        
        html_content += f"""
                <div class="section">
                    <h2>💡 健康建议</h2>
                    <p>{advice}</p>
                </div>
                
                <div class="footer">
                    <p>此报告由健身营养助手自动生成</p>
                    <p>坚持记录，健康生活每一天！</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 创建邮件
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=f"💪 健身营养助手 - 每日健康报告 {today_str}",
            html_content=HtmlContent(html_content)
        )
        
        # 发送
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        
        if response.status_code in [200, 202]:
            return True, "报告已发送到您的邮箱"
        else:
            return False, f"发送失败，状态码: {response.status_code}"
            
    except Exception as e:
        return False, f"发送失败: {str(e)}"

def is_sendgrid_configured():
    """检查 SendGrid 是否已配置"""
    try:
        api_key = st.secrets["SENDGRID_API_KEY"]
        from_email = st.secrets["SENDGRID_FROM_EMAIL"]
        return api_key and api_key != "你的SendGrid_API_Key" and from_email
    except:
        return False
