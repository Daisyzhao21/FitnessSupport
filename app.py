import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="健身营养助手", page_icon="💪", layout="wide")

# 加载数据
@st.cache_data
def load_food_data():
    df = pd.read_csv('food_nutrition.csv', encoding='utf-8-sig')
    return df

@st.cache_data
def load_exercise_data():
    exercises = pd.DataFrame([
        {"器材": "跑步机", "类型": "有氧", "消耗系数": 0.12, "说明": "速度8km/h"},
        {"器材": "椭圆机", "类型": "有氧", "消耗系数": 0.10, "说明": "中等阻力"},
        {"器材": "动感单车", "类型": "有氧", "消耗系数": 0.11, "说明": "中等强度"},
        {"器材": "划船机", "类型": "有氧", "消耗系数": 0.13, "说明": "全身运动"},
        {"器材": "卧推架", "类型": "力量", "消耗系数": 0.07, "说明": "胸部训练"},
        {"器材": "深蹲架", "类型": "力量", "消耗系数": 0.09, "说明": "腿部训练"},
        {"器材": "哑铃", "类型": "自由重量", "消耗系数": 0.06, "说明": "通用"},
    ])
    return exercises

df_food = load_food_data()
df_exercise = load_exercise_data()

# 初始化 Session State
if 'food_records' not in st.session_state:
    st.session_state.food_records = []
if 'exercise_records' not in st.session_state:
    st.session_state.exercise_records = []
if 'total_calories' not in st.session_state:
    st.session_state.total_calories = 0
if 'total_protein' not in st.session_state:
    st.session_state.total_protein = 0
if 'total_burned' not in st.session_state:
    st.session_state.total_burned = 0
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {'gender': '男', 'weight': 70, 'height': 170, 'age': 25, 'activity_level': '中等', 'goal': '减脂'}
if 'bmr' not in st.session_state:
    st.session_state.bmr = 1600
if 'daily_target' not in st.session_state:
    st.session_state.daily_target = 2000
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'search_weight' not in st.session_state:
    st.session_state.search_weight = 100
if 'search_term' not in st.session_state:
    st.session_state.search_term = ""

# 计算 BMR
def calculate_bmr():
    p = st.session_state.user_profile
    if p['gender'] == '男':
        bmr = 66 + (13.7 * p['weight']) + (5 * p['height']) - (6.8 * p['age'])
    else:
        bmr = 655 + (9.6 * p['weight']) + (1.8 * p['height']) - (4.7 * p['age'])
    activity_factors = {'低': 1.2, '中等': 1.375, '高': 1.55, '非常高': 1.725}
    tdee = bmr * activity_factors[p['activity_level']]
    if p['goal'] == '减脂':
        target = tdee - 300
    elif p['goal'] == '增肌':
        target = tdee + 300
    else:
        target = tdee
    st.session_state.bmr = int(bmr)
    st.session_state.daily_target = int(target)

# CSS
st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1rem;
    border-radius: 15px;
    margin-bottom: 1rem;
    text-align: center;
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>💪 健身营养助手</h1><p>📸 拍照识别 | 🏋️ 累计记录 | 📊 摄入 vs 消耗</p></div>', unsafe_allow_html=True)

# 三列布局
col_left, col_mid, col_right = st.columns([1, 1.5, 1.3])

# ==================== 左侧：个人信息 ====================
with col_left:
    st.markdown("### 👤 个人信息")
    
    with st.expander("编辑信息", expanded=False):
        gender = st.selectbox("性别", ["男", "女"], index=0 if st.session_state.user_profile['gender']=='男' else 1)
        age = st.number_input("年龄", 15, 100, st.session_state.user_profile['age'])
        height = st.number_input("身高(cm)", 100, 250, st.session_state.user_profile['height'])
        weight = st.number_input("体重(kg)", 30, 200, st.session_state.user_profile['weight'])
        activity = st.selectbox("活动水平", ["低", "中等", "高", "非常高"], 
                                index=["低", "中等", "高", "非常高"].index(st.session_state.user_profile['activity_level']))
        goal = st.selectbox("健身目标", ["减脂", "保持体重", "增肌"],
                           index=["减脂", "保持体重", "增肌"].index(st.session_state.user_profile['goal']))
        
        if st.button("更新信息", use_container_width=True):
            st.session_state.user_profile = {'gender': gender, 'age': age, 'height': height, 'weight': weight,
                                            'activity_level': activity, 'goal': goal}
            calculate_bmr()
            st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 摄入 vs 消耗")
    
    net = st.session_state.total_calories - st.session_state.total_burned
    remaining = st.session_state.daily_target - net
    
    st.metric("基础代谢", f"{st.session_state.bmr} kcal")
    st.metric("每日目标", f"{st.session_state.daily_target} kcal")
    
    col_a, col_b = st.columns(2)
    col_a.metric("🍽️ 摄入", f"{st.session_state.total_calories:.0f} kcal")
    col_b.metric("🏋️ 消耗", f"{st.session_state.total_burned:.0f} kcal")
    
    if remaining > 0:
        st.success(f"✅ 剩余: {remaining:.0f} kcal")
        progress = min(max((st.session_state.daily_target - remaining) / st.session_state.daily_target, 0), 1)
        st.progress(progress)
    else:
        st.error(f"⚠️ 超标: {-remaining:.0f} kcal")
        st.progress(1.0)
    
    if st.button("🗑️ 清空记录", use_container_width=True):
        st.session_state.food_records = []
        st.session_state.exercise_records = []
        st.session_state.total_calories = 0
        st.session_state.total_protein = 0
        st.session_state.total_burned = 0
        st.rerun()

# ==================== 中间：食物摄入 ====================
with col_mid:
    st.markdown("## 🍽️ 食物摄入")
    
    meal = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"], key="meal_selector")
    
    # 搜索区域
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        search_term = st.text_input("搜索食物", placeholder="鸡胸肉、米饭、西兰花...", key="search_input", value=st.session_state.search_term)
    with col_s2:
        search_weight = st.number_input("重量(g)", 10, 1000, st.session_state.search_weight, step=50, key="search_weight_input")
    
    # 保存搜索状态
    if search_term != st.session_state.search_term or search_weight != st.session_state.search_weight:
        st.session_state.search_term = search_term
        st.session_state.search_weight = search_weight
        if search_term:
            results = df_food[df_food['名称'].str.contains(search_term, na=False)]
            st.session_state.search_results = results.head(8) if len(results) > 0 else None
        else:
            st.session_state.search_results = None
    
    # 显示搜索结果
    if st.session_state.search_results is not None and len(st.session_state.search_results) > 0:
        for idx, row in st.session_state.search_results.iterrows():
            cal = row['热量'] * st.session_state.search_weight / 100
            pro = row['蛋白质'] * st.session_state.search_weight / 100
            
            c1, c2, c3, c4 = st.columns([2, 1.2, 1.2, 1])
            c1.markdown(f"**{row['名称']}**")
            c1.caption(row['类别'])
            c2.write(f"{cal:.0f} kcal")
            c3.write(f"蛋白质 {pro:.0f}g")
            
            # 使用 query_params 来触发添加，避免 rerun 问题
            button_key = f"add_{meal}_{row['名称']}_{idx}"
            if c4.button("➕ 添加", key=button_key):
                # 直接修改 session state
                st.session_state.food_records.append({
                    '时间': datetime.now().strftime("%H:%M"),
                    '餐次': meal,
                    '名称': row['名称'],
                    '重量': st.session_state.search_weight,
                    '热量': cal,
                    '蛋白质': pro
                })
                st.session_state.total_calories += cal
                st.session_state.total_protein += pro
                st.success(f"✅ 已添加 {row['名称']} ({st.session_state.search_weight}g) 到{meal}")
                # 强制刷新页面
                st.rerun()
    elif search_term:
        st.warning("未找到该食物，请尝试其他关键词")
    
    st.markdown("---")
    st.markdown("### 📋 今日饮食")
    
    if st.session_state.food_records:
        for m in ["早餐", "午餐", "晚餐", "加餐"]:
            meals = [r for r in st.session_state.food_records if r['餐次'] == m]
            if meals:
                st.markdown(f"**{m}**")
                for r in meals:
                    st.write(f"  🕐 {r['时间']} | {r['名称']} | {r['重量']}g | {r['热量']:.0f}kcal | 蛋白质 {r['蛋白质']:.0f}g")
    else:
        st.info("暂无记录")

# ==================== 右侧：运动消耗 ====================
with col_right:
    st.markdown("## 🏋️ 运动消耗")
    
    exercise_name = st.selectbox("选择器材", df_exercise['器材'].tolist(), key="exercise_select")
    duration = st.number_input("时长(分钟)", 1, 180, 30, step=5, key="duration_input")
    extra_weight = st.number_input("负重(kg)", 0, 100, 0, step=5, key="extra_weight_input")
    
    selected = df_exercise[df_exercise['器材'] == exercise_name].iloc[0]
    calories = selected['消耗系数'] * (st.session_state.user_profile['weight'] + extra_weight) * duration
    st.info(f"🔥 预计消耗: **{calories:.0f} kcal**")
    
    if st.button("✅ 记录运动", type="primary", use_container_width=True, key="add_exercise"):
        st.session_state.exercise_records.append({
            '时间': datetime.now().strftime("%H:%M"),
            '器材': exercise_name,
            '时长': duration,
            '负重': extra_weight,
            '消耗': calories
        })
        st.session_state.total_burned += calories
        st.success(f"✅ 已记录 {exercise_name} {duration}分钟")
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📋 今日运动")
    
    if st.session_state.exercise_records:
        total_min = sum(r['时长'] for r in st.session_state.exercise_records)
        st.metric("总时长", f"{total_min} 分钟")
        for r in st.session_state.exercise_records[-15:]:
            st.write(f"  🕐 {r['时间']} | {r['器材']} | {r['时长']}分钟 | 🔥 {r['消耗']:.0f}kcal")
    else:
        st.info("暂无记录")

st.markdown("---")
st.markdown("<p style='text-align:center;color:gray'>📸 拍照识别食物 | 🏋️ 运动记录 | 📊 摄入vs消耗</p>", unsafe_allow_html=True)
