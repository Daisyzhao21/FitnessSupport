import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

DB_PATH = "fitness_data.db"

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 食物记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            record_date TEXT NOT NULL,
            meal TEXT NOT NULL,
            food_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # 运动记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercise_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            record_date TEXT NOT NULL,
            exercise_name TEXT NOT NULL,
            duration INTEGER NOT NULL,
            extra_weight INTEGER DEFAULT 0,
            calories REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # 用户个人信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            gender TEXT,
            age INTEGER,
            height REAL,
            weight REAL,
            activity_level TEXT,
            goal TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

def hash_password(password):
    """密码加密"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    """创建新用户"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hash_password(password))
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def verify_user(username, password):
    """验证用户登录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM users WHERE username = ? AND password = ?",
        (username, hash_password(password))
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_user_by_id(user_id):
    """获取用户信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_food_record(user_id, date, meal, food_name, quantity, unit, calories, protein):
    """保存食物记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO food_records (user_id, record_date, meal, food_name, quantity, unit, calories, protein)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, date, meal, food_name, quantity, unit, calories, protein))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id

def save_exercise_record(user_id, date, exercise_name, duration, extra_weight, calories):
    """保存运动记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO exercise_records (user_id, record_date, exercise_name, duration, extra_weight, calories)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, date, exercise_name, duration, extra_weight, calories))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id

def get_food_records_by_date(user_id, date):
    """获取指定日期的食物记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT record_id, meal, food_name, quantity, unit, calories, protein
        FROM food_records
        WHERE user_id = ? AND record_date = ?
        ORDER BY created_at
    ''', (user_id, date))
    results = cursor.fetchall()
    conn.close()
    return results

def get_exercise_records_by_date(user_id, date):
    """获取指定日期的运动记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT record_id, exercise_name, duration, extra_weight, calories
        FROM exercise_records
        WHERE user_id = ? AND record_date = ?
        ORDER BY created_at
    ''', (user_id, date))
    results = cursor.fetchall()
    conn.close()
    return results

def get_user_profile(user_id):
    """获取用户个人信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT gender, age, height, weight, activity_level, goal FROM user_profiles WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'gender': result[0],
            'age': result[1],
            'height': result[2],
            'weight': result[3],
            'activity_level': result[4],
            'goal': result[5]
        }
    return None

def save_user_profile(user_id, profile):
    """保存用户个人信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_profiles (user_id, gender, age, height, weight, activity_level, goal, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, profile['gender'], profile['age'], profile['height'], 
          profile['weight'], profile['activity_level'], profile['goal']))
    conn.commit()
    conn.close()

def get_date_range_summary(user_id, start_date, end_date):
    """获取日期范围内的汇总数据"""
    conn = sqlite3.connect(DB_PATH)
    
    # 食物汇总
    food_df = pd.read_sql_query('''
        SELECT record_date, SUM(calories) as total_calories, SUM(protein) as total_protein
        FROM food_records
        WHERE user_id = ? AND record_date BETWEEN ? AND ?
        GROUP BY record_date
    ''', conn, params=(user_id, start_date, end_date))
    
    # 运动汇总
    exercise_df = pd.read_sql_query('''
        SELECT record_date, SUM(calories) as total_burned
        FROM exercise_records
        WHERE user_id = ? AND record_date BETWEEN ? AND ?
        GROUP BY record_date
    ''', conn, params=(user_id, start_date, end_date))
    
    conn.close()
    return food_df, exercise_df

def delete_records_by_date(user_id, date):
    """删除指定日期的所有记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM food_records WHERE user_id = ? AND record_date = ?", (user_id, date))
    cursor.execute("DELETE FROM exercise_records WHERE user_id = ? AND record_date = ?", (user_id, date))
    conn.commit()
    conn.close()

def export_to_csv(user_id, start_date, end_date):
    """导出数据为CSV"""
    conn = sqlite3.connect(DB_PATH)
    
    food_df = pd.read_sql_query('''
        SELECT record_date, meal, food_name, quantity, unit, calories, protein
        FROM food_records
        WHERE user_id = ? AND record_date BETWEEN ? AND ?
        ORDER BY record_date, created_at
    ''', conn, params=(user_id, start_date, end_date))
    
    exercise_df = pd.read_sql_query('''
        SELECT record_date, exercise_name, duration, extra_weight, calories
        FROM exercise_records
        WHERE user_id = ? AND record_date BETWEEN ? AND ?
        ORDER BY record_date, created_at
    ''', conn, params=(user_id, start_date, end_date))
    
    conn.close()
    return food_df, exercise_df

# 初始化数据库
init_db()
