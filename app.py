import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

st.set_page_config(page_title="健身营养助手", page_icon="💪", layout="wide")

# 加载食物数据
@st.cache_data
def load_food_data():
    df = pd.read_csv('food_nutrition.csv', encoding='utf-8-sig')
    return df

df_food = load_food_data()

# 单位配置
UNIT_CONFIG = {
    'g': {'label': '克', 'default': 100, 'step': 50, 'min': 10, 'max': 1000},
    'ml': {'label': '毫升', 'default': 250, 'step': 50, 'min': 50, 'max': 1000},
}

def get_current_time():
    return datetime.now().strftime("%H:%M")

# 初始化 session state - 最简单直接的方式
if 'records' not in st.session_state:
    st.session_state.records = []
if 'total_cal' not in st.session_state:
    st.session_state.total_cal = 0

st.title("💪 健身营养助手")

# 显示当前记录数用于调试
st.caption(f"📊 当前记录数: {len(st.session_state.records)}")

# 添加食物区域
st.subheader("🍽️ 添加食物")

col1, col2 = st.columns([2, 1])
with col1:
    search_term = st.text_input("搜索食物", placeholder="啤酒、鸡胸肉、米饭...")
with col2:
    meal = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"])

if search_term:
    results = df_food[df_food['名称'].str.contains(search_term, na=False)].head(5)
    
    for _, row in results.iterrows():
        unit = row.get('单位', 'g') if pd.notna(row.get('单位')) else 'g'
        config = UNIT_CONFIG.get(unit, UNIT_CONFIG['g'])
        std_qty = row.get('标准量', 100) if pd.notna(row.get('标准量')) else 100
        
        # 计算每单位热量
        cal_per_unit = row['热量'] / std_qty
        
        # 选择数量
        qty = st.number_input(
            f"{row['名称']} 数量({config['label']})",
            min_value=config['min'],
            max_value=config['max'],
            value=config['default'],
            step=config['step'],
            key=f"qty_{row['名称']}_{uuid.uuid4().hex[:4]}"
        )
        
        cal = cal_per_unit * qty
        
        if st.button(f"➕ 添加 {row['名称']}", key=f"add_{row['名称']}_{uuid.uuid4().hex[:4]}"):
            st.session_state.records.append({
                '时间': get_current_time(),
                '餐次': meal,
                '名称': row['名称'],
                '数量': qty,
                '单位': config['label'],
                '热量': cal
            })
            st.session_state.total_cal += cal
            st.success(f"✅ 已添加 {row['名称']} {qty}{config['label']} - {cal:.0f}kcal")
            st.rerun()

# 显示记录
st.subheader("📋 今日饮食")

if len(st.session_state.records) > 0:
    for r in st.session_state.records:
        st.write(f"🕐 {r['时间']} | {r['餐次']} | {r['名称']} | {r['数量']}{r['单位']} | {r['热量']:.0f}kcal")
    
    st.metric("总热量", f"{st.session_state.total_cal:.0f} kcal")
else:
    st.info("暂无记录，请搜索添加食物")

# 清空按钮
if st.button("🗑️ 清空所有记录"):
    st.session_state.records = []
    st.session_state.total_cal = 0
    st.rerun()

st.markdown("---")
st.caption("💡 提示：搜索食物后选择数量，点击添加按钮")
