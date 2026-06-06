import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from PIL import Image
import uuid
from supabase import create_client

st.set_page_config(page_title="健身营养助手", page_icon="💪", layout="wide")

# ==================== Supabase 连接 ====================
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except:
        try:
            import toml
            with open('.streamlit/secrets.toml', 'r') as f:
                config = toml.load(f)
            url = config["SUPABASE_URL"]
            key = config["SUPABASE_KEY"]
        except:
            st.error("无法加载 Supabase 配置")
            st.stop()
    return create_client(url, key)

supabase = init_supabase()

# ==================== 辅助函数 ====================
def get_or_create_user(email):
    result = supabase.table("user_profiles").select("*").eq("email", email).execute()
    if result.data:
        return result.data[0]
    
    new_user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "username": email.split('@')[0],
        "weight": 70.0,
        "height": 170.0,
        "created_at": datetime.now().isoformat()
    }
    try:
        insert_result = supabase.table("user_profiles").insert(new_user).execute()
        return insert_result.data[0]
    except Exception as e:
        st.error(f"创建用户失败: {e}")
        return None

def save_food_record(user_id, date_str, meal, food_name, quantity, calories, protein):
    try:
        data = {
            "user_id": user_id,
            "record_date": date_str,
            "meal": meal,
            "food_name": food_name,
            "quantity": quantity,
            "unit": "g",
            "calories": calories,
            "protein": protein
        }
        supabase.table("food_records").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"保存失败: {e}")
        return False

def get_food_records(user_id, date_str):
    try:
        result = supabase.table("food_records")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("record_date", date_str)\
            .execute()
        return result.data if result.data else []
    except:
        return []

# ==================== 加载食物数据 ====================
@st.cache_data
def load_food_data():
    df = pd.read_csv('food_nutrition.csv', encoding='utf-8-sig')
    return df

df_food = load_food_data()

# ==================== UI ====================
# 登录
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if not st.session_state.user_id:
    st.title("💪 健身营养助手")
    email = st.text_input("邮箱地址")
    if st.button("登录/注册"):
        if email:
            user = get_or_create_user(email)
            if user:
                st.session_state.user_id = user['id']
                st.session_state.user_email = email
                st.rerun()
    st.stop()

# 主界面
st.title("💪 健身营养助手")
st.caption(f"👤 {st.session_state.get('user_email', '用户')}")

if st.button("退出"):
    st.session_state.user_id = None
    st.rerun()

today = date.today().strftime("%Y-%m-%d")
foods = get_food_records(st.session_state.user_id, today)
total_calories = sum(f.get('calories', 0) for f in foods)

st.metric("今日摄入", f"{total_calories:.0f} kcal")

# 添加食物
st.subheader("➕ 添加食物")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    search = st.text_input("搜索食物")
with col2:
    meal = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"])
with col3:
    weight = st.number_input("重量(g)", 10, 500, 100, 50)

if search:
    results = df_food[df_food['名称'].str.contains(search, na=False)].head(5)
    for _, row in results.iterrows():
        cal = row['热量'] * weight / 100
        pro = row['蛋白质'] * weight / 100
        
        col_a, col_b, col_c = st.columns([2, 1, 1])
        col_a.write(f"**{row['名称']}** - {row['类别']}")
        col_b.write(f"{cal:.0f} kcal | 蛋白质 {pro:.0f}g")
        
        if col_c.button(f"添加", key=f"add_{row['名称']}"):
            if save_food_record(st.session_state.user_id, today, meal, row['名称'], weight, cal, pro):
                st.success(f"✅ 已添加 {row['名称']}")
                st.rerun()
            else:
                st.error("添加失败")
        st.divider()

# 显示今日记录
st.subheader("📋 今日饮食")
if foods:
    for f in foods:
        st.write(f"  {f['meal']} | {f['food_name']} | {f['quantity']}g | {f['calories']:.0f}kcal")
else:
    st.info("暂无记录")

st.caption("💾 数据已云端保存")
