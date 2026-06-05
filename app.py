import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

st.set_page_config(page_title="健身营养助手", layout="wide")

# 加载数据
@st.cache_data
def load_food_data():
    df = pd.read_csv('food_nutrition.csv', encoding='utf-8-sig')
    return df

df_food = load_food_data()

# 初始化 - 使用更稳定的方式
if 'foods' not in st.session_state:
    st.session_state.foods = []
if 'total_cal' not in st.session_state:
    st.session_state.total_cal = 0

st.title("🍽️ 食物记录")

# 显示当前记录
st.subheader("📋 今日记录")
if st.session_state.foods:
    for i, f in enumerate(st.session_state.foods):
        st.write(f"🕐 {f['time']} | {f['name']} | {f['qty']}g | {f['cal']:.0f}kcal")
    st.metric("总热量", f"{st.session_state.total_cal:.0f} kcal")
else:
    st.info("暂无记录")

st.divider()

# 添加食物
st.subheader("➕ 添加食物")
search = st.text_input("搜索食物")

if search:
    results = df_food[df_food['名称'].str.contains(search, na=False)].head(5)
    
    for _, row in results.iterrows():
        col1, col2, col3 = st.columns([2, 1, 1])
        col1.write(f"**{row['名称']}** - {row['热量']} kcal/100g")
        
        # 使用固定的 key 但用唯一标识符
        unique_id = str(uuid.uuid4())[:8]
        qty = col2.number_input("克", 10, 500, 100, key=f"qty_{row['名称']}_{unique_id}")
        cal = row['热量'] * qty / 100
        col3.write(f"{cal:.0f} kcal")
        
        if col3.button("➕ 添加", key=f"btn_{row['名称']}_{unique_id}"):
            st.session_state.foods.append({
                'time': datetime.now().strftime("%H:%M"),
                'name': row['名称'],
                'qty': qty,
                'cal': cal
            })
            st.session_state.total_cal += cal
            st.success(f"✅ 已添加 {row['名称']}")
            st.rerun()
        st.divider()

# 清空按钮
if st.button("🗑️ 清空"):
    st.session_state.foods = []
    st.session_state.total_cal = 0
    st.rerun()
