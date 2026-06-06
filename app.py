import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image
import uuid
import json

from image_recognition import FoodImageRecognizer

st.set_page_config(page_title="健身营养助手", page_icon="💪", layout="wide")

# 版本号 - 强制刷新缓存
APP_VERSION = "2.0.2"
if 'app_version' not in st.session_state or st.session_state.app_version != APP_VERSION:
    st.session_state.clear()
    st.session_state.app_version = APP_VERSION

# 使用 JavaScript 获取用户本地时间
def get_user_local_time():
    """通过前端 JavaScript 获取用户本地时间"""
    # 注入 JavaScript 获取本地时间
    js_code = """
    <script>
    function getUserTime() {
        const now = new Date();
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const timeStr = hours + ':' + minutes;
        
        // 存储到 sessionStorage
        sessionStorage.setItem('user_local_time', timeStr);
        sessionStorage.setItem('user_timezone_offset', now.getTimezoneOffset());
        
        // 通过 URL 参数传递（备用）
        const url = new URL(window.location.href);
        url.searchParams.set('local_time', timeStr);
        window.history.replaceState({}, '', url);
        
        return timeStr;
    }
    getUserTime();
    </script>
    """
    st.markdown(js_code, unsafe_allow_html=True)
    
    # 尝试从 query params 获取时间
    query_params = st.query_params
    if 'local_time' in query_params:
        return query_params['local_time']
    
    # 默认返回当前时间（服务器时间）
    return datetime.now().strftime("%H:%M")

# 简化版 - 直接使用 Python 的本地时间（Streamlit Cloud 会用 UTC）
# 改用浏览器本地时间
def get_current_time():
    # 尝试从 localStorage 获取用户时间
    import streamlit as st
    user_time = st.query_params.get("local_time", None)
    if user_time:
        return user_time
    return datetime.now().strftime("%H:%M")
    """获取用户本地时间（通过 JavaScript）"""
    return get_user_local_time()

# 加载数据
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

def get_recognizer():
    api_key = os.environ.get("QWEN_API_KEY")
    if hasattr(st, 'secrets') and 'QWEN_API_KEY' in st.secrets:
        api_key = st.secrets['QWEN_API_KEY']
    return FoodImageRecognizer(api_type="qwen", api_key=api_key) if api_key else None

# 初始化 Session State
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {'gender': '男', 'weight': 70, 'height': 170, 'age': 25, 'activity_level': '中等', 'goal': '减脂'}
if 'food_records' not in st.session_state:
    st.session_state.food_records = []
if 'exercise_records' not in st.session_state:
    st.session_state.exercise_records = []
if 'total_calories' not in st.session_state:
    st.session_state.total_calories = 0.0
if 'total_protein' not in st.session_state:
    st.session_state.total_protein = 0.0
if 'total_burned' not in st.session_state:
    st.session_state.total_burned = 0.0
if 'bmr' not in st.session_state:
    st.session_state.bmr = 1600
if 'daily_target' not in st.session_state:
    st.session_state.daily_target = 2000

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

calculate_bmr()

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
@media (max-width: 768px) {
    .stButton button { width: 100%; }
}
</style>
<div class="main-header">
    <h1>💪 健身营养助手</h1>
    <p>📸 拍照识别 | 🏋️ 运动记录 | 📊 摄入 vs 消耗</p>
</div>
""", unsafe_allow_html=True)

# 三列布局
col_left, col_mid, col_right = st.columns([1, 1.5, 1.3])

# ==================== 左侧：个人信息 ====================
with col_left:
    st.markdown("### 👤 个人信息")
    st.info(f"{st.session_state.user_profile['height']}cm / {st.session_state.user_profile['weight']}kg / {st.session_state.user_profile['goal']}")
    with st.expander("✏️ 编辑"):
        g = st.selectbox("性别", ["男", "女"], 0 if st.session_state.user_profile['gender']=='男' else 1)
        a = st.number_input("年龄", 15, 100, st.session_state.user_profile['age'])
        h = st.number_input("身高(cm)", 100, 250, st.session_state.user_profile['height'])
        w = st.number_input("体重(kg)", 30, 200, st.session_state.user_profile['weight'])
        act = st.selectbox("活动水平", ["低", "中等", "高", "非常高"], 
                          index=["低", "中等", "高", "非常高"].index(st.session_state.user_profile['activity_level']))
        goal = st.selectbox("目标", ["减脂", "保持体重", "增肌"],
                           index=["减脂", "保持体重", "增肌"].index(st.session_state.user_profile['goal']))
        if st.button("💾 保存"):
            st.session_state.user_profile = {'gender': g, 'age': a, 'height': h, 'weight': w, 'activity_level': act, 'goal': goal}
            calculate_bmr()
            st.rerun()
    
    net = st.session_state.total_calories - st.session_state.total_burned
    remaining = st.session_state.daily_target - net
    st.metric("🎯 每日目标", f"{st.session_state.daily_target} kcal")
    col_a, col_b = st.columns(2)
    col_a.metric("🍽️ 摄入", f"{st.session_state.total_calories:.0f}")
    col_b.metric("🏋️ 消耗", f"{st.session_state.total_burned:.0f}")
    if remaining > 0:
        st.success(f"剩余: {remaining:.0f} kcal")
        st.progress(min(max(remaining / st.session_state.daily_target, 0), 1))
    else:
        st.error(f"超标: {-remaining:.0f} kcal")
        st.progress(1.0)
    
    if st.button("🗑️ 清空记录"):
        st.session_state.food_records = []
        st.session_state.exercise_records = []
        st.session_state.total_calories = 0.0
        st.session_state.total_protein = 0.0
        st.session_state.total_burned = 0.0
        st.rerun()

# ==================== 中间：食物摄入 ====================
with col_mid:
    st.markdown("## 🍽️ 食物摄入")
    mode = st.radio("方式", ["🔍 手动", "📸 拍照"], horizontal=True)
    meal = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"])
    st.caption(f"🕐 {get_current_time()}")
    
    if mode == "🔍 手动":
        term = st.text_input("🔍 搜索食物", placeholder="鸡腿肉、卤牛肉、鸡胸肉、西兰花...")
        if term:
            results = df_food[df_food['名称'].str.contains(term, na=False)].head(8)
            if len(results) == 0:
                st.warning(f"未找到 '{term}'，试试：鸡腿肉、卤牛肉、鸡胸肉")
            for _, row in results.iterrows():
                unit = row.get('单位', 'g') if pd.notna(row.get('单位')) else 'g'
                config = UNIT_CONFIG.get(unit, UNIT_CONFIG['g'])
                std_qty = row.get('标准量', 100) if pd.notna(row.get('标准量')) else 100
                
                cols = st.columns([2, 0.8, 1.2, 0.8])
                cols[0].markdown(f"**{row['名称']}**")
                cols[0].caption(row['类别'])
                cols[1].write(f"{row['热量']:.0f}")
                
                qty = cols[2].number_input(
                    config['label'], 
                    config['min'], config['max'], config['default'], config['step'],
                    key=f"qty_{row['名称']}",
                    label_visibility="collapsed"
                )
                
                multiplier = qty / std_qty
                cal = row['热量'] * multiplier
                pro = row['蛋白质'] * multiplier
                cols[3].write(f"{cal:.0f}")
                
                if cols[3].button("➕", key=f"add_{row['名称']}"):
                    st.session_state.food_records.append({
                        '时间': get_current_time(),
                        '餐次': meal,
                        '名称': row['名称'],
                        '数量': qty,
                        '单位': unit,
                        '热量': cal,
                        '蛋白质': pro
                    })
                    st.session_state.total_calories += cal
                    st.session_state.total_protein += pro
                    st.success(f"✅ 已添加 {row['名称']}")
                    st.rerun()
                st.divider()
    
    else:
        recognizer = get_recognizer()
        if recognizer:
            st.markdown("📸 **提示：移动端默认使用后置摄像头**")
            img = st.camera_input("拍照", key="food_camera")
            if img:
                image = Image.open(img)
                st.image(image, caption="预览", use_container_width=True)
                if st.button("识别食物"):
                    with st.spinner("AI识别中..."):
                        temp_path = f"/tmp/food_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        image.save(temp_path)
                        res = recognizer.recognize_food(temp_path)
                        os.remove(temp_path)
                        if not res.get("error"):
                            for f in res.get("foods", []):
                                name = f.get('name', '未知')
                                weight = f.get('weight', 150)
                                cal = f.get('calories', weight * 1.5)
                                pro = f.get('protein', weight * 0.15)
                                if st.button(f"➕ 添加 {name}"):
                                    st.session_state.food_records.append({
                                        '时间': get_current_time(),
                                        '餐次': meal,
                                        '名称': name,
                                        '数量': weight,
                                        '单位': 'g',
                                        '热量': cal,
                                        '蛋白质': pro
                                    })
                                    st.session_state.total_calories += cal
                                    st.session_state.total_protein += pro
                                    st.success(f"✅ 已添加 {name}")
                                    st.rerun()
    
    # 显示今日饮食记录
    st.markdown("---")
    st.markdown("### 📋 今日饮食")
    
    if len(st.session_state.food_records) > 0:
        for m in ["早餐", "午餐", "晚餐", "加餐"]:
            items = [r for r in st.session_state.food_records if r.get('餐次') == m]
            if items:
                st.markdown(f"**{m}**")
                for r in items:
                    unit = r.get('单位', 'g')
                    label = UNIT_CONFIG.get(unit, UNIT_CONFIG['g'])['label']
                    st.write(f"  🕐 {r['时间']} | {r['名称']} | {r['数量']}{label} | {r['热量']:.0f}kcal")
    else:
        st.info("暂无记录，请搜索添加食物")

# ==================== 右侧：运动消耗 ====================
with col_right:
    st.markdown("## 🏋️ 运动消耗")
    mode_ex = st.radio("方式", ["🔍 搜索", "✏️ 自定义", "📸 拍照"], horizontal=True)
    st.caption(f"🕐 {get_current_time()}")
    
    if mode_ex == "🔍 搜索":
        search = st.text_input("🔍 搜索运动", placeholder="深蹲、硬拉...")
        filtered = df_exercise if not search else df_exercise[df_exercise['器材'].str.contains(search, na=False)]
        if len(filtered) == 0:
            st.warning("未找到")
            filtered = df_exercise
        ex_name = st.selectbox("运动", filtered['器材'].tolist())
        ex = df_exercise[df_exercise['器材'] == ex_name].iloc[0]
        st.caption(f"{ex['说明']} | {ex['消耗系数']} kcal/kg/分钟")
        dur = st.number_input("分钟", 1, 180, 30, 5)
        extra = st.number_input("负重(kg)", 0, 100, 0, 5)
        cal = ex['消耗系数'] * (st.session_state.user_profile['weight'] + extra) * dur
        st.info(f"🔥 {cal:.0f} kcal")
        if st.button("✅ 记录"):
            st.session_state.exercise_records.append({
                '时间': get_current_time(),
                '器材': ex_name,
                '时长': dur,
                '负重': extra,
                '消耗': cal
            })
            st.session_state.total_burned += cal
            st.success(f"✅ 已记录 {ex_name}")
            st.rerun()
    
    elif mode_ex == "✏️ 自定义":
        name = st.text_input("运动名称")
        coeff = st.number_input("系数", 0.01, 0.50, 0.08, 0.01)
        dur = st.number_input("分钟", 1, 180, 30, 5, key="c_dur")
        extra = st.number_input("负重", 0, 100, 0, 5, key="c_extra")
        if name:
            cal = coeff * (st.session_state.user_profile['weight'] + extra) * dur
            st.info(f"🔥 {cal:.0f} kcal")
            if st.button("✅ 记录"):
                st.session_state.exercise_records.append({
                    '时间': get_current_time(),
                    '器材': name,
                    '时长': dur,
                    '负重': extra,
                    '消耗': cal
                })
                st.session_state.total_burned += cal
                st.success(f"✅ 已记录 {name}")
                st.rerun()
    
    else:
        recognizer = get_recognizer()
        if recognizer:
            img = st.camera_input("拍照", key="ex_cam") or st.file_uploader("图片", type=['jpg', 'png'], key="ex_up")
            if img and st.button("识别"):
                img = Image.open(img)
                img.save("/tmp/ex.jpg")
                res = recognizer.recognize_food("/tmp/ex.jpg")
                if not res.get("error"):
                    name = res.get("foods", [{}])[0].get('name', '未知')
                    st.write(f"识别: {name}")
                    dur = st.number_input("分钟", 1, 180, 30, 5, key="r_dur")
                    extra = st.number_input("负重", 0, 100, 0, 5, key="r_extra")
                    if st.button("记录"):
                        cal = 0.08 * (st.session_state.user_profile['weight'] + extra) * dur
                        st.session_state.exercise_records.append({
                            '时间': get_current_time(),
                            '器材': name,
                            '时长': dur,
                            '负重': extra,
                            '消耗': cal
                        })
                        st.session_state.total_burned += cal
                        st.success("✅ 已记录")
                        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📋 今日运动")
    if len(st.session_state.exercise_records) > 0:
        total_min = sum(r.get('时长', 0) for r in st.session_state.exercise_records)
        st.metric("总时长", f"{total_min} 分钟")
        for r in st.session_state.exercise_records[-15:]:
            st.write(f"  🕐 {r['时间']} | {r['器材']} | {r['时长']}分钟 | 🔥 {r['消耗']:.0f}kcal")
    else:
        st.info("暂无运动记录")

st.markdown("---")
st.markdown("<p style='text-align:center;color:gray'>🔍 搜索 | ✏️ 自定义 | 📸 拍照识别 | 🕐 自动使用本地时间</p>", unsafe_allow_html=True)
