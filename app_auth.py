import streamlit as st
import random
import string
from database import *

def generate_verification_code():
    """生成6位数字验证码"""
    return ''.join(random.choices(string.digits, k=6))

def show_auth_modal():
    """显示登录/注册弹窗"""
    st.markdown("### 🔐 登录/注册")
    st.markdown("支持邮箱、手机号注册")
    
    tab1, tab2, tab3 = st.tabs(["登录", "邮箱注册", "手机号注册"])
    
    # ==================== 登录 ====================
    with tab1:
        login_type = st.radio("登录方式", ["用户名", "邮箱", "手机号"], horizontal=True)
        
        if login_type == "用户名":
            username = st.text_input("用户名", key="login_username")
            password = st.text_input("密码", type="password", key="login_password")
            if st.button("登录", type="primary", use_container_width=True):
                user_id, uname = login_by_username(username, password)
                if user_id:
                    st.session_state.mode = 'user'
                    st.session_state.user_id = user_id
                    st.session_state.username = uname
                    profile = get_user_profile(user_id)
                    if profile:
                        st.session_state.user_profile = profile
                    st.success(f"✅ 欢迎回来，{uname}！")
                    st.rerun()
                else:
                    st.error("用户名或密码错误")
        
        elif login_type == "邮箱":
            email = st.text_input("邮箱", key="login_email")
            password = st.text_input("密码", type="password", key="login_password2")
            if st.button("登录", type="primary", use_container_width=True):
                user_id, uname = login_by_email(email, password)
                if user_id:
                    st.session_state.mode = 'user'
                    st.session_state.user_id = user_id
                    st.session_state.username = uname
                    profile = get_user_profile(user_id)
                    if profile:
                        st.session_state.user_profile = profile
                    st.success(f"✅ 欢迎回来，{uname}！")
                    st.rerun()
                else:
                    st.error("邮箱或密码错误")
        
        else:  # 手机号
            phone = st.text_input("手机号", key="login_phone")
            password = st.text_input("密码", type="password", key="login_password3")
            if st.button("登录", type="primary", use_container_width=True):
                user_id, uname = login_by_phone(phone, password)
                if user_id:
                    st.session_state.mode = 'user'
                    st.session_state.user_id = user_id
                    st.session_state.username = uname
                    profile = get_user_profile(user_id)
                    if profile:
                        st.session_state.user_profile = profile
                    st.success(f"✅ 欢迎回来，{uname}！")
                    st.rerun()
                else:
                    st.error("手机号或密码错误")
    
    # ==================== 邮箱注册 ====================
    with tab2:
        reg_email = st.text_input("邮箱", key="reg_email")
        reg_username = st.text_input("用户名（可选）", key="reg_username", placeholder="留空则使用邮箱前缀")
        reg_password = st.text_input("密码", type="password", key="reg_password")
        confirm_password = st.text_input("确认密码", type="password", key="reg_confirm")
        
        # 验证码（演示模式，实际使用时需要接入邮件服务）
        st.info("💡 演示模式：验证码为 123456")
        verify_code = st.text_input("验证码", key="reg_code", placeholder="请输入验证码")
        
        if st.button("注册", type="primary", use_container_width=True):
            if reg_password != confirm_password:
                st.error("两次输入的密码不一致")
            elif len(reg_password) < 4:
                st.error("密码至少4位")
            elif verify_code != "123456":
                st.error("验证码错误")
            else:
                user_id, msg = create_user_by_email(reg_email, reg_password, reg_username if reg_username else None)
                if user_id:
                    st.success("✅ 注册成功！请登录")
                else:
                    st.error(msg)
    
    # ==================== 手机号注册 ====================
    with tab3:
        reg_phone = st.text_input("手机号", key="reg_phone", placeholder="11位手机号")
        reg_username2 = st.text_input("用户名（可选）", key="reg_username2", placeholder="留空则自动生成")
        reg_password2 = st.text_input("密码", type="password", key="reg_password2")
        confirm_password2 = st.text_input("确认密码", type="password", key="reg_confirm2")
        
        st.info("💡 演示模式：验证码为 123456")
        verify_code2 = st.text_input("验证码", key="reg_code2", placeholder="请输入验证码")
        
        if st.button("注册", type="primary", use_container_width=True):
            if reg_password2 != confirm_password2:
                st.error("两次输入的密码不一致")
            elif len(reg_password2) < 4:
                st.error("密码至少4位")
            elif verify_code2 != "123456":
                st.error("验证码错误")
            else:
                user_id, msg = create_user_by_phone(reg_phone, reg_password2, reg_username2 if reg_username2 else None)
                if user_id:
                    st.success("✅ 注册成功！请登录")
                else:
                    st.error(msg)
    
    # 微信/支付宝绑定提示
    st.markdown("---")
    st.markdown("#### 🔗 第三方登录（即将支持）")
    col1, col2 = st.columns(2)
    with col1:
        st.button("📱 微信登录", disabled=True, use_container_width=True)
    with col2:
        st.button("💰 支付宝登录", disabled=True, use_container_width=True)

def show_user_info():
    """显示用户信息"""
    if st.session_state.mode == 'user' and st.session_state.user_id:
        user_info = get_user_by_id(st.session_state.user_id)
        if user_info:
            with st.expander("👤 账户信息"):
                st.write(f"用户名: {user_info['username']}")
                if user_info['email']:
                    st.write(f"邮箱: {user_info['email']}")
                if user_info['phone']:
                    st.write(f"手机号: {user_info['phone']}")
                st.write(f"注册时间: {user_info['created_at']}")
                if user_info['last_login']:
                    st.write(f"最后登录: {user_info['last_login']}")
            
            # 绑定第三方
            with st.expander("🔗 绑定第三方账号"):
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("绑定微信", use_container_width=True):
                        st.info("微信绑定功能开发中")
                with col2:
                    if st.button("绑定支付宝", use_container_width=True):
                        st.info("支付宝绑定功能开发中")
