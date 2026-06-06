"""
独立的历史数据模块
记录食物和运动数据到数据库，不影响主应用
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

DB_PATH = "fitness_data.db"

def init_history_db():
    """初始化历史数据数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 食物记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT NOT NULL,
            meal TEXT NOT NULL,
            food_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 运动记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercise_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT NOT NULL,
            exercise_name TEXT NOT NULL,
            duration INTEGER NOT NULL,
            extra_weight REAL DEFAULT 0,
            calories REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_food_to_history(user_id, date, meal, food_name, quantity, unit, calories, protein):
    """保存食物记录到历史"""
    if not user_id:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO food_history (user_id, date, meal, food_name, quantity, unit, calories, protein)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, date, meal, food_name, quantity, unit, calories, protein))
    conn.commit()
    conn.close()

def save_exercise_to_history(user_id, date, exercise_name, duration, extra_weight, calories):
    """保存运动记录到历史"""
    if not user_id:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO exercise_history (user_id, date, exercise_name, duration, extra_weight, calories)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, date, exercise_name, duration, extra_weight, calories))
    conn.commit()
    conn.close()

def load_food_history(user_id, date):
    """加载指定日期的食物记录"""
    if not user_id:
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT meal, food_name, quantity, unit, calories, protein
        FROM food_history
        WHERE user_id = ? AND date = ?
        ORDER BY created_at
    ''', (user_id, date))
    results = cursor.fetchall()
    conn.close()
    return [{'餐次': r[0], '名称': r[1], '数量': r[2], '单位': r[3], '热量': r[4], '蛋白质': r[5]} for r in results]

def load_exercise_history(user_id, date):
    """加载指定日期的运动记录"""
    if not user_id:
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT exercise_name, duration, extra_weight, calories
        FROM exercise_history
        WHERE user_id = ? AND date = ?
        ORDER BY created_at
    ''', (user_id, date))
    results = cursor.fetchall()
    conn.close()
    return [{'器材': r[0], '时长': r[1], '负重': r[2], '消耗': r[3]} for r in results]

def get_trend_data(user_id, days=30):
    """获取趋势数据（用于图表）"""
    if not user_id:
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH)
    
    # 获取食物数据
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    food_df = pd.read_sql_query('''
        SELECT date, SUM(calories) as total_calories, SUM(protein) as total_protein
        FROM food_history
        WHERE user_id = ? AND date BETWEEN ? AND ?
        GROUP BY date
        ORDER BY date
    ''', conn, params=(user_id, start_date, end_date))
    
    # 获取运动数据
    exercise_df = pd.read_sql_query('''
        SELECT date, SUM(calories) as total_burned
        FROM exercise_history
        WHERE user_id = ? AND date BETWEEN ? AND ?
        GROUP BY date
        ORDER BY date
    ''', conn, params=(user_id, start_date, end_date))
    
    conn.close()
    
    # 合并数据
    if len(food_df) > 0 or len(exercise_df) > 0:
        all_dates = set(food_df['date'].tolist()) | set(exercise_df['date'].tolist())
        trend_data = []
        for date in sorted(all_dates):
            calories = food_df[food_df['date'] == date]['total_calories'].sum() if len(food_df) > 0 else 0
            protein = food_df[food_df['date'] == date]['total_protein'].sum() if len(food_df) > 0 else 0
            burned = exercise_df[exercise_df['date'] == date]['total_burned'].sum() if len(exercise_df) > 0 else 0
            trend_data.append({'日期': date, '摄入': calories, '消耗': burned, '净摄入': calories - burned, '蛋白质': protein})
        
        return pd.DataFrame(trend_data)
    
    return pd.DataFrame()

def show_trend_chart(user_id):
    """显示趋势图表"""
    if not user_id:
        st.info("💡 登录后可以查看历史趋势图表")
        return
    
    trend_df = get_trend_data(user_id)
    
    if len(trend_df) > 0:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend_df['日期'], y=trend_df['摄入'], mode='lines+markers', name='摄入热量', line=dict(color='#ff6b6b', width=2)))
        fig.add_trace(go.Scatter(x=trend_df['日期'], y=trend_df['消耗'], mode='lines+markers', name='消耗热量', line=dict(color='#4ecdc4', width=2)))
        fig.add_trace(go.Scatter(x=trend_df['日期'], y=trend_df['净摄入'], mode='lines+markers', name='净摄入', line=dict(color='#667eea', width=2, dash='dash')))
        fig.update_layout(title="30天热量趋势", xaxis_title="日期", yaxis_title="热量 (kcal)", height=450)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无历史数据，登录后记录会自动保存")

def show_export_button(user_id):
    """显示导出按钮"""
    if not user_id:
        st.info("💡 登录后可以导出数据")
        return
    
    if st.button("📥 导出数据", use_container_width=True):
        conn = sqlite3.connect(DB_PATH)
        food_df = pd.read_sql_query('''
            SELECT date, meal, food_name, quantity, unit, calories, protein
            FROM food_history WHERE user_id = ?
            ORDER BY date, created_at
        ''', conn, params=(user_id,))
        exercise_df = pd.read_sql_query('''
            SELECT date, exercise_name, duration, extra_weight, calories
            FROM exercise_history WHERE user_id = ?
            ORDER BY date, created_at
        ''', conn, params=(user_id,))
        conn.close()
        
        if len(food_df) > 0:
            csv1 = food_df.to_csv(index=False)
            st.download_button("📥 下载饮食记录", csv1, "food_records.csv", "text/csv")
        if len(exercise_df) > 0:
            csv2 = exercise_df.to_csv(index=False)
            st.download_button("📥 下载运动记录", csv2, "exercise_records.csv", "text/csv")
        if len(food_df) == 0 and len(exercise_df) == 0:
            st.info("暂无数据")

# 初始化数据库
init_history_db()
