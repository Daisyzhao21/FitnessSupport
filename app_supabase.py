import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from PIL import Image
import uuid
from supabase import create_client

st.set_page_config(page_title="健身营养助手", page_icon="💪", layout="wide")

# ==================== Supabase 连接 ====================
@st.cache_resource
def init_supabase():
    # 读取 secrets（Streamlit Cloud）或环境变量（本地）
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except:
        # 本地开发：从 .streamlit/secrets.toml 读取
        import toml
        with open('.streamlit/secrets.toml', 'r') as f:
            config = toml.load(f)
        url = config["SUPABASE_URL"]
        key = config["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# ==================== 数据操作函数 ====================
def get_or_create_user(email, username=None):
    """获取或创建用户"""
    # 查询用户是否存在
    result = supabase.table("user_profiles").select("*").eq("email", email).execute()
    
    if result.data:
        return result.data[0]
    else:
        # 创建新用户
        new_user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "username": username or email.split('@')[0],
            "created_at": datetime.now().isoformat()
        }
        try:
            insert_result = supabase.table("user_profiles").insert(new_user).execute()
            return insert_result.data[0] if insert_result.data else None
        except Exception as e:
            st.error(f"创建用户失败: {e}")
            return None

def save_food_record(user_id, record_date, meal, food_name, quantity, unit, calories, protein):
    """保存食物记录"""
    try:
        data = {
            "user_id": user_id,
            "record_date": record_date,
            "meal": meal,
            "food_name": food_name,
            "quantity": quantity,
            "unit": unit,
            "calories": calories,
            "protein": protein
        }
        supabase.table("food_records").insert(data).execute()
        return True
    except Exception as e:
        print(f"保存失败: {e}")
        return False

def get_food_records(user_id, record_date):
    """获取食物记录"""
    try:
        result = supabase.table("food_records")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("record_date", record_date)\
            .order("created_at")\
            .execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"查询失败: {e}")
        return []

def save_exercise_record(user_id, record_date, exercise_name, duration, extra_weight, calories):
    """保存运动记录"""
    try:
        data = {
            "user_id": user_id,
            "record_date": record_date,
            "exercise_name": exercise_name,
            "duration": duration,
            "extra_weight": extra_weight,
            "calories": calories
        }
        supabase.table("exercise_records").insert(data).execute()
        return True
    except Exception as e:
        print(f"保存失败: {e}")
        return False

def get_exercise_records(user_id, record_date):
    """获取运动记录"""
    try:
        result = supabase.table("exercise_records")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("record_date", record_date)\
            .order("created_at")\
            .execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"查询失败: {e}")
        return []

def get_trend_data(user_id, days=30):
    """获取趋势数据"""
    try:
        from datetime import timedelta
        start_date = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = date.today().strftime("%Y-%m-%d")
        
        food_result = supabase.table("food_records")\
            .select("record_date, calories")\
            .eq("user_id", user_id)\
            .gte("record_date", start_date)\
            .lte("record_date", end_date)\
            .execute()
        
        exercise_result = supabase.table("exercise_records")\
            .select("record_date, calories")\
            .eq("user_id", user_id)\
            .gte("record_date", start_date)\
            .lte("record_date", end_date)\
            .execute()
        
        return food_result.data, exercise_result.data
    except Exception as e:
        print(f"获取趋势失败: {e}")
        return [], []

# ==================== 加载食物数据 ====================
@st.cache_data
def load_food_data():
    df = pd.read_csv('food_nutrition.csv', encoding='utf-8-sig')
    return df

@st.cache_data
def load_exercise_data():
    return pd.read_csv('exercise_database.csv', encoding='utf-8-sig')

df_food = load_food_data()
df_exercise = load_exercise_data()

# 单位配置
UNIT_CONFIG = {
    'g': {'label': '克', 'default': 100, 'step': 50, 'min': 10, 'max': 1000},
    'ml': {'label': '毫升', 'default': 250, 'step': 50, 'min': 50, 'max': 1000},
    '个': {'label': '个', 'default': 1, 'step': 1, 'min': 1, 'max': 10},
    '碗': {'label': '碗', 'default': 1, 'step': 1, 'min': 1, 'max': 3},
    '杯': {'label': '杯', 'default': 1, 'step': 1, 'min': 1, 'max': 5},
}

def get_current_date():
    return date.today().strftime("%Y-%m-%d")

# ==================== UI ====================
st.title("💪 健身营养助手")

# 简单的登录界面（使用邮箱）
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if not st.session_state.user_id:
    st.markdown("### 🔐 登录/注册")
    
    col1, col2 = st.columns(2)
    with col1:
        email = st.text_input("邮箱地址", key="login_email")
    with col2:
        username = st.text_input("用户名（可选）", key="login_username", placeholder="留空使用邮箱前缀")
    
    if st.button("登录 / 注册", type="primary", use_container_width=True):
        if email:
            user = get_or_create_user(email, username if username else None)
            if user:
                st.session_state.user_id = user['id']
                st.session_state.user_email = user['email']
                st.success(f"✅ 欢迎，{user.get('username', email)}！")
                st.rerun()
            else:
                st.error("登录失败，请重试")
        else:
            st.warning("请输入邮箱地址")
    
    st.caption("💡 输入邮箱即可自动登录/注册，数据将云端保存")
    st.stop()

# 已登录界面
st.success(f"✅ 已登录：{st.session_state.get('user_email', '用户')}")

col_logout, col_date = st.columns([1, 3])
with col_logout:
    if st.button("🚪 退出", use_container_width=True):
        st.session_state.user_id = None
        st.rerun()

# 显示今日记录
today = get_current_date()
foods = get_food_records(st.session_state.user_id, today)
exercises = get_exercise_records(st.session_state.user_id, today)

total_calories = sum(f.get('calories', 0) for f in foods)
total_burned = sum(e.get('calories', 0) for e in exercises)

col1, col2, col3 = st.columns(3)
col1.metric("🍽️ 今日摄入", f"{total_calories:.0f} kcal")
col2.metric("🏋️ 今日消耗", f"{total_burned:.0f} kcal")
col3.metric("📊 净摄入", f"{total_calories - total_burned:.0f} kcal")

st.markdown("---")

# 简单食物添加
st.subheader("🍽️ 添加食物")
col_search, col_meal, col_weight = st.columns([2, 1, 1])
with col_search:
    search = st.text_input("搜索食物", placeholder="鸡胸肉、鸡蛋、米饭...")
with col_meal:
    meal = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"])
with col_weight:
    weight = st.number_input("重量(g)", 10, 500, 100, 50)

if search:
    results = df_food[df_food['名称'].str.contains(search, na=False)].head(5)
    for _, row in results.iterrows():
        cal = row['热量'] * weight / 100
        pro = row['蛋白质'] * weight / 100
        
        col1, col2, col3 = st.columns([2, 1, 1])
        col1.write(f"**{row['名称']}** - {row['类别']}")
        col2.write(f"{cal:.0f} kcal")
        if col3.button("➕ 添加", key=f"add_{row['名称']}"):
            save_food_record(st.session_state.user_id, today, meal, row['名称'], weight, 'g', cal, pro)
            st.success(f"✅ 已添加 {row['名称']}")
            st.rerun()
        st.divider()

# 显示今日食物列表
if foods:
    st.subheader("📋 今日饮食")
    for f in foods:
        st.write(f"  {f['meal']} | {f['food_name']} | {f['quantity']}g | {f['calories']:.0f}kcal")

st.caption("💾 数据已云端保存，永久不丢失")
