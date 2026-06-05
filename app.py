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

# 初始化 - 使用最简单的方式
if 'food_items' not in st.session_state:
    st.session_state.food_items = []
if 'total_kcal' not in st.session_state:
    st.session_state.total_kcal = 0

st.title("💪 健身营养助手")

# 调试信息
st.caption(f"🔍 调试: 当前记录数 = {len(st.session_state.food_items)}")

# 添加食物区域
st.subheader("🍽️ 添加食物")

col1, col2 = st.columns([2, 1])
with col1:
    search = st.text_input("搜索食物", placeholder="啤酒、鸡胸肉、米饭...")
with col2:
    meal_choice = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"])

if search:
    matched = df_food[df_food['名称'].str.contains(search, na=False)].head(5)
    
    for _, food in matched.iterrows():
        unit = food.get('单位', 'g') if pd.notna(food.get('单位')) else 'g'
        config = UNIT_CONFIG.get(unit, UNIT_CONFIG['g'])
        std_qty = food.get('标准量', 100) if pd.notna(food.get('标准量')) else 100
        
        # 每单位热量
        cal_per_unit = food['热量'] / std_qty
        
        # 数量输入
        amount = st.number_input(
            f"{food['名称']} 数量({config['label']})",
            min_value=config['min'],
            max_value=config['max'],
            value=config['default'],
            step=config['step'],
            key=f"amt_{food['名称']}"
        )
        
        calories = cal_per_unit * amount
        
        if st.button(f"➕ 添加 {food['名称']}", key=f"btn_{food['名称']}"):
            new_item = {
                'time': get_current_time(),
                'meal': meal_choice,
                'name': food['名称'],
                'amount': amount,
                'unit': config['label'],
                'calories': calories
            }
            st.session_state.food_items.append(new_item)
            st.session_state.total_kcal += calories
            st.success(f"✅ 已添加 {food['名称']} - {calories:.0f}kcal")
            st.rerun()
        st.divider()

# 显示记录区域
st.subheader("📋 今日饮食")

if len(st.session_state.food_items) > 0:
    for item in st.session_state.food_items:
        st.write(f"🕐 {item['time']} | {item['meal']} | {item['name']} | {item['amount']}{item['unit']} | {item['calories']:.0f}kcal")
    
    st.metric("总热量", f"{st.session_state.total_kcal:.0f} kcal")
else:
    st.info("暂无记录，请在上方搜索添加食物")

# 清空按钮
if st.button("🗑️ 清空所有记录"):
    st.session_state.food_items = []
    st.session_state.total_kcal = 0
    st.rerun()

st.markdown("---")
st.caption("💡 提示：搜索食物 → 选择数量 → 点击添加")
