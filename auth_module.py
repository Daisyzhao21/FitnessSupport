"""
独立的用户认证模块
不影响主应用的食物添加功能
"""

import streamlit as st
import sqlite3
import hashlib
from datetime import datetime

DB_PATH = "fitness_data.db"

def init_auth_db():
    """初始化认证数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    """注册新用户"""
    if len(username) < 3:
        return False, "用户名至少3个字符"
    if len(password) < 4:
        return False, "密码至少4个字符"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hash_password(password))
        )
        conn.commit()
        conn.close()
        return True, "注册成功"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "用户名已存在"

def login_user(username, password):
    """用户登录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, username FROM users WHERE username = ? AND password = ?",
        (username, hash_password(password))
    )
    result = cursor.fetchone()
    if result:
        # 更新最后登录时间
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE user_id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), result[0])
        )
        conn.commit()
    conn.close()
    return result

def show_auth_sidebar():
    """在侧边栏显示登录/注册界面（独立模块）"""
    with st.sidebar:
        st.markdown("---")
        
        if st.session_state.get('logged_in', False):
            st.markdown(f"### 👤 {st.session_state.username}")
            if st.button("🚪 退出登录", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.session_state.username = None
                st.rerun()
        else:
            st.markdown("### 🔐 账号")
            
            tab1, tab2 = st.tabs(["登录", "注册"])
            
            with tab1:
                login_username = st.text_input("用户名", key="login_username_input", placeholder="请输入用户名")
                login_password = st.text_input("密码", type="password", key="login_password_input", placeholder="请输入密码")
                if st.button("登录", key="login_btn", use_container_width=True):
                    if login_username and login_password:
                        result = login_user(login_username, login_password)
                        if result:
                            st.session_state.logged_in = True
                            st.session_state.user_id = result[0]
                            st.session_state.username = result[1]
                            st.success(f"✅ 欢迎回来，{result[1]}！")
                            st.rerun()
                        else:
                            st.error("用户名或密码错误")
                    else:
                        st.warning("请输入用户名和密码")
            
            with tab2:
                new_username = st.text_input("用户名", key="new_username_input", placeholder="至少3个字符")
                new_password = st.text_input("密码", type="password", key="new_password_input", placeholder="至少4个字符")
                confirm_password = st.text_input("确认密码", type="password", key="confirm_password_input", placeholder="再次输入密码")
                if st.button("注册", key="register_btn", use_container_width=True):
                    if not new_username or not new_password:
                        st.warning("请填写用户名和密码")
                    elif new_password != confirm_password:
                        st.error("两次输入的密码不一致")
                    else:
                        success, msg = register_user(new_username, new_password)
                        if success:
                            st.success(msg + "，请登录")
                        else:
                            st.error(msg)

# 初始化数据库
init_auth_db()
