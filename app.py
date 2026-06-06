import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from PIL import Image
import uuid
import plotly.express as px
import plotly.graph_objects as go

from image_recognition import FoodImageRecognizer
from database import *

st.set_page_config(page_title="健身营养助手", page_icon="💪", layout="wide")

# 加载食物数据
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

def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")

def calculate_bmr(weight, height, age, gender):
    if gender == '男':
        return 66 + (13.7 * weight) + (5 * height) - (6.8 * age)
    else:
        return 655 + (9.6 * weight) + (1.8 * height) - (4.7 * age)

# ==================== 初始化 Session ====================
if 'mode' not in st.session_state:
    st.session_state.mode = 'guest'  # guest 或 user
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = get_current_date()
if 'food_records' not in st.session_state:
    st.session_state.food_records = []
if 'exercise_records' not in st.session_state:
    st.session_state.exercise_records = []
if 'total_calories' not in st.session_state:
    st.session_state.total_calories = 0.0
if 'total_burned' not in st.session_state:
    st.session_state.total_burned = 0.0
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {'gender': '男', 'age': 25, 'height': 170, 'weight': 70, 'activity_level': '中等', 'goal': '减脂'}

# 计算每日目标
def get_daily_target():
    bmr = calculate_bmr(
        st.session_state.user_profile['weight'],
        st.session_state.user_profile['height'],
        st.session_state.user_profile['age'],
        st.session_state.user_profile['gender']
    )
    activity_factors = {'低': 1.2, '中等': 1.375, '高': 1.55, '非常高': 1.725}
    tdee = bmr * activity_factors[st.session_state.user_profile['activity_level']]
    if st.session_state.user_profile['goal'] == '减脂':
        return tdee - 300
    elif st.session_state.user_profile['goal'] == '增肌':
        return tdee + 300
    else:
        return tdee

# 保存记录到数据库（仅登录用户）
def save_to_database():
    if st.session_state.mode == 'user' and st.session_state.user_id:
        from database import delete_records_by_date, save_food_record, save_exercise_record
        
        delete_records_by_date(st.session_state.user_id, st.session_state.selected_date)
        
        for r in st.session_state.food_records:
            save_food_record(
                st.session_state.user_id,
                st.session_state.selected_date,
                r['餐次'],
                r['名称'],
                r['数量'],
                r.get('单位', 'g'),
                r['热量'],
                r.get('蛋白质', 0)
            )
        
        for r in st.session_state.exercise_records:
            save_exercise_record(
                st.session_state.user_id,
                st.session_state.selected_date,
                r['器材'],
                r['时长'],
                r.get('负重', 0),
                r['消耗']
            )

# 从数据库加载记录（仅登录用户）
def load_from_database():
    if st.session_state.mode == 'user' and st.session_state.user_id:
        food_records = get_food_records_by_date(st.session_state.user_id, st.session_state.selected_date)
        exercise_records = get_exercise_records_by_date(st.session_state.user_id, st.session_state.selected_date)
        
        st.session_state.food_records = [{
            '餐次': r[1], '名称': r[2], '数量': r[3], '单位': r[4],
            '热量': r[5], '蛋白质': r[6]
        } for r in food_records]
        st.session_state.exercise_records = [{
            '器材': r[1], '时长': r[2], '负重': r[3], '消耗': r[4]
        } for r in exercise_records]
        st.session_state.total_calories = sum(r[5] for r in food_records)
        st.session_state.total_burned = sum(r[4] for r in exercise_records)

# ==================== 用户认证弹窗 ====================
    st.markdown("### 🔐 登录/注册")
    st.markdown("登录后可以保存历史记录、查看趋势图表")
    
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        username = st.text_input("用户名", key="login_username")
        password = st.text_input("密码", type="password", key="login_password")
        if st.button("登录", type="primary", use_container_width=True):
            user_id = verify_user(username, password)
            if user_id:
                st.session_state.mode = 'user'
                st.session_state.user_id = user_id
                st.session_state.username = username
                # 加载用户个人信息
                profile = get_user_profile(user_id)
                if profile:
                    st.session_state.user_profile = profile
                load_from_database()
                st.success(f"✅ 欢迎回来，{username}！")
                st.rerun()
            else:
                st.error("用户名或密码错误")
    
    with tab2:
        new_username = st.text_input("用户名", key="reg_username")
        new_password = st.text_input("密码", type="password", key="reg_password")
        confirm_password = st.text_input("确认密码", type="password")
        if st.button("注册", type="primary", use_container_width=True):
            if new_password != confirm_password:
                st.error("两次输入的密码不一致")
            elif len(new_password) < 4:
                st.error("密码至少4位")
            else:
                user_id = create_user(new_username, new_password)
                if user_id:
                    st.success(f"✅ 注册成功！请登录")
                else:
                    st.error("用户名已存在")

def logout():
    st.session_state.mode = 'guest'
    st.session_state.user_id = None
    st.session_state.username = None
    # 不清空记录，保持当前数据
    st.rerun()

# ==================== 用户信息栏 ====================
def show_user_bar():
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.session_state.mode == 'user':
            st.caption(f"👤 已登录: {st.session_state.username}")
        else:
            st.caption("👤 访客模式 (数据仅保存在本地)")
    with col2:
        if st.session_state.mode == 'guest':
            if st.button("🔐 登录/注册", use_container_width=True):
                st.session_state.show_auth = True
        else:
            if st.button("🚪 退出登录", use_container_width=True):
                logout()
    with col3:
        if st.session_state.mode == 'user':
            if st.button("💾 立即保存", use_container_width=True):
                save_to_database()
                st.success("✅ 已保存")

# ==================== 页面头部 ====================
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

# 显示用户栏
show_user_bar()

# 显示认证弹窗
if st.session_state.get('show_auth', False):
    show_auth_modal()
    if st.button("继续试用", use_container_width=True):
        st.session_state.show_auth = False
        st.rerun()
    st.stop()

# 日期选择器
col_date1, col_date2, col_date3 = st.columns([2, 1, 1])
with col_date1:
    selected_date = st.date_input(
        "📅 选择日期",
        value=datetime.strptime(st.session_state.selected_date, "%Y-%m-%d") if st.session_state.selected_date else datetime.now(),
        key="date_picker"
    )
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    
    if selected_date_str != st.session_state.selected_date:
        if st.session_state.mode == 'user' and st.session_state.user_id:
            save_to_database()
        st.session_state.selected_date = selected_date_str
        if st.session_state.mode == 'user' and st.session_state.user_id:
            load_from_database()
        else:
            # 访客模式：切换日期时清空当前记录（不保存）
            st.session_state.food_records = []
            st.session_state.exercise_records = []
            st.session_state.total_calories = 0
            st.session_state.total_burned = 0
        st.rerun()

with col_date2:
    if st.button("📊 历史趋势", use_container_width=True):
        if st.session_state.mode == 'user':
            st.session_state.show_trend = True
        else:
            st.info("💡 登录后可以查看历史趋势图表")

with col_date3:
    if st.button("📥 导出数据", use_container_width=True):
        if st.session_state.mode == 'user':
            st.session_state.show_export = True
        else:
            st.info("💡 登录后可以导出数据")

st.caption(f"📅 当前记录日期: {selected_date_str}")

# 计算每日目标
daily_target = int(get_daily_target())

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
            if st.session_state.mode == 'user' and st.session_state.user_id:
                save_user_profile(st.session_state.user_id, st.session_state.user_profile)
            st.success("✅ 已保存")
            st.rerun()
    
    net = st.session_state.total_calories - st.session_state.total_burned
    remaining = daily_target - net
    st.metric("🎯 每日目标", f"{daily_target} kcal")
    col_a, col_b = st.columns(2)
    col_a.metric("🍽️ 摄入", f"{st.session_state.total_calories:.0f}")
    col_b.metric("🏋️ 消耗", f"{st.session_state.total_burned:.0f}")
    if remaining > 0:
        st.success(f"剩余: {remaining:.0f} kcal")
        st.progress(min(max(remaining / daily_target, 0), 1))
    else:
        st.error(f"超标: {-remaining:.0f} kcal")
        st.progress(1.0)
    
    if st.button("🗑️ 清空今日记录"):
        st.session_state.food_records = []
        st.session_state.exercise_records = []
        st.session_state.total_calories = 0.0
        st.session_state.total_burned = 0.0
        if st.session_state.mode == 'user' and st.session_state.user_id:
            save_to_database()
        st.rerun()

# ==================== 中间：食物摄入 ====================
with col_mid:
    st.markdown("## 🍽️ 食物摄入")
    mode = st.radio("方式", ["🔍 手动", "📸 拍照"], horizontal=True)
    meal = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"])
    
    if mode == "🔍 手动":
        term = st.text_input("🔍 搜索食物", placeholder="鸡腿肉、卤牛肉、鸡胸肉、西兰花...")
        if term:
            results = df_food[df_food['名称'].str.contains(term, na=False)].head(8)
            if len(results) == 0:
                st.warning(f"未找到 '{term}'")
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
                    key=f"qty_{row['名称']}_{uuid.uuid4().hex[:4]}",
                    label_visibility="collapsed"
                )
                
                multiplier = qty / std_qty
                cal = row['热量'] * multiplier
                pro = row['蛋白质'] * multiplier
                cols[3].write(f"{cal:.0f}")
                
                if cols[3].button("➕", key=f"add_{row['名称']}_{uuid.uuid4().hex[:4]}"):
                    st.session_state.food_records.append({
                        '餐次': meal,
                        '名称': row['名称'],
                        '数量': qty,
                        '单位': unit,
                        '热量': cal,
                        '蛋白质': pro
                    })
                    st.session_state.total_calories += cal
                    if st.session_state.mode == 'user' and st.session_state.user_id:
                        save_to_database()
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
                                        '餐次': meal,
                                        '名称': name,
                                        '数量': weight,
                                        '单位': 'g',
                                        '热量': cal,
                                        '蛋白质': pro
                                    })
                                    st.session_state.total_calories += cal
                                    if st.session_state.mode == 'user' and st.session_state.user_id:
                                        save_to_database()
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
                    st.write(f"  {r['名称']} | {r['数量']}{label} | {r['热量']:.0f}kcal")
    else:
        st.info("暂无记录，请搜索添加食物")

# ==================== 右侧：运动消耗 ====================
with col_right:
    st.markdown("## 🏋️ 运动消耗")
    mode_ex = st.radio("方式", ["🔍 搜索", "✏️ 自定义", "📸 拍照"], horizontal=True)
    
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
                '器材': ex_name,
                '时长': dur,
                '负重': extra,
                '消耗': cal
            })
            st.session_state.total_burned += cal
            if st.session_state.mode == 'user' and st.session_state.user_id:
                save_to_database()
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
                    '器材': name,
                    '时长': dur,
                    '负重': extra,
                    '消耗': cal
                })
                st.session_state.total_burned += cal
                if st.session_state.mode == 'user' and st.session_state.user_id:
                    save_to_database()
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
                            '器材': name,
                            '时长': dur,
                            '负重': extra,
                            '消耗': cal
                        })
                        st.session_state.total_burned += cal
                        if st.session_state.mode == 'user' and st.session_state.user_id:
                            save_to_database()
                        st.success("✅ 已记录")
                        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📋 今日运动")
    if len(st.session_state.exercise_records) > 0:
        total_min = sum(r.get('时长', 0) for r in st.session_state.exercise_records)
        st.metric("总时长", f"{total_min} 分钟")
        for r in st.session_state.exercise_records[-15:]:
            st.write(f"  {r['器材']} | {r['时长']}分钟 | 🔥 {r['消耗']:.0f}kcal")
    else:
        st.info("暂无运动记录")

# ==================== 历史趋势弹窗 ====================
if st.session_state.get('show_trend', False):
    st.markdown("---")
    st.markdown("## 📈 历史热量趋势")
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    food_df, exercise_df = get_date_range_summary(st.session_state.user_id, start_date, end_date)
    
    if len(food_df) > 0 or len(exercise_df) > 0:
        all_dates = set(food_df['record_date'].tolist()) | set(exercise_df['record_date'].tolist())
        trend_data = []
        for date in sorted(all_dates):
            calories = food_df[food_df['record_date'] == date]['total_calories'].sum() if len(food_df) > 0 else 0
            burned = exercise_df[exercise_df['record_date'] == date]['total_burned'].sum() if len(exercise_df) > 0 else 0
            trend_data.append({'日期': date, '摄入': calories, '消耗': burned, '净摄入': calories - burned})
        
        trend_df = pd.DataFrame(trend_data)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend_df['日期'], y=trend_df['摄入'], mode='lines+markers', name='摄入热量', line=dict(color='#ff6b6b', width=2)))
        fig.add_trace(go.Scatter(x=trend_df['日期'], y=trend_df['消耗'], mode='lines+markers', name='消耗热量', line=dict(color='#4ecdc4', width=2)))
        fig.add_trace(go.Scatter(x=trend_df['日期'], y=trend_df['净摄入'], mode='lines+markers', name='净摄入', line=dict(color='#667eea', width=2, dash='dash')))
        fig.update_layout(title="30天热量趋势", xaxis_title="日期", yaxis_title="热量 (kcal)", height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无历史数据，开始记录吧！")
    
    if st.button("关闭", use_container_width=True):
        st.session_state.show_trend = False
        st.rerun()

# ==================== 导出数据弹窗 ====================
if st.session_state.get('show_export', False):
    st.markdown("---")
    st.markdown("## 📥 导出数据")
    
    col1, col2 = st.columns(2)
    with col1:
        export_start = st.date_input("开始日期", datetime.now() - timedelta(days=30))
    with col2:
        export_end = st.date_input("结束日期", datetime.now())
    
    if st.button("导出 CSV"):
        food_df, exercise_df = export_to_csv(
            st.session_state.user_id,
            export_start.strftime("%Y-%m-%d"),
            export_end.strftime("%Y-%m-%d")
        )
        
        if len(food_df) > 0:
            csv1 = food_df.to_csv(index=False)
            st.download_button("📥 下载饮食记录", csv1, f"food_records_{export_start}_{export_end}.csv", "text/csv")
        
        if len(exercise_df) > 0:
            csv2 = exercise_df.to_csv(index=False)
            st.download_button("📥 下载运动记录", csv2, f"exercise_records_{export_start}_{export_end}.csv", "text/csv")
        
        if len(food_df) == 0 and len(exercise_df) == 0:
            st.info("所选日期范围内无数据")
    
    if st.button("关闭", use_container_width=True):
        st.session_state.show_export = False
        st.rerun()

st.markdown("---")
st.markdown("<p style='text-align:center;color:gray'>🔍 搜索 | ✏️ 自定义 | 📸 拍照识别 | 💾 登录后可保存历史</p>", unsafe_allow_html=True)
import streamlit as st
import random
import string
from database import *

def generate_verification_code():
    """生成6位数字验证码"""
    return ''.join(random.choices(string.digits, k=6))

def show_auth_modal():
    """显示登录/注册弹窗"""
    st.markdown("### 🔐 登录/注册")
    st.markdown("支持邮箱、手机号注册")
    
    tab1, tab2, tab3 = st.tabs(["登录", "邮箱注册", "手机号注册"])
    
    # ==================== 登录 ====================
    with tab1:
        login_type = st.radio("登录方式", ["用户名", "邮箱", "手机号"], horizontal=True)
        
        if login_type == "用户名":
            username = st.text_input("用户名", key="login_username")
            password = st.text_input("密码", type="password", key="login_password")
            if st.button("登录", type="primary", use_container_width=True):
                user_id, uname = login_by_username(username, password)
                if user_id:
                    st.session_state.mode = 'user'
                    st.session_state.user_id = user_id
                    st.session_state.username = uname
                    profile = get_user_profile(user_id)
                    if profile:
                        st.session_state.user_profile = profile
                    st.success(f"✅ 欢迎回来，{uname}！")
                    st.rerun()
                else:
                    st.error("用户名或密码错误")
        
        elif login_type == "邮箱":
            email = st.text_input("邮箱", key="login_email")
            password = st.text_input("密码", type="password", key="login_password2")
            if st.button("登录", type="primary", use_container_width=True):
                user_id, uname = login_by_email(email, password)
                if user_id:
                    st.session_state.mode = 'user'
                    st.session_state.user_id = user_id
                    st.session_state.username = uname
                    profile = get_user_profile(user_id)
                    if profile:
                        st.session_state.user_profile = profile
                    st.success(f"✅ 欢迎回来，{uname}！")
                    st.rerun()
                else:
                    st.error("邮箱或密码错误")
        
        else:  # 手机号
            phone = st.text_input("手机号", key="login_phone")
            password = st.text_input("密码", type="password", key="login_password3")
            if st.button("登录", type="primary", use_container_width=True):
                user_id, uname = login_by_phone(phone, password)
                if user_id:
                    st.session_state.mode = 'user'
                    st.session_state.user_id = user_id
                    st.session_state.username = uname
                    profile = get_user_profile(user_id)
                    if profile:
                        st.session_state.user_profile = profile
                    st.success(f"✅ 欢迎回来，{uname}！")
                    st.rerun()
                else:
                    st.error("手机号或密码错误")
    
    # ==================== 邮箱注册 ====================
    with tab2:
        reg_email = st.text_input("邮箱", key="reg_email")
        reg_username = st.text_input("用户名（可选）", key="reg_username", placeholder="留空则使用邮箱前缀")
        reg_password = st.text_input("密码", type="password", key="reg_password")
        confirm_password = st.text_input("确认密码", type="password", key="reg_confirm")
        
        # 验证码（演示模式，实际使用时需要接入邮件服务）
        st.info("💡 演示模式：验证码为 123456")
        verify_code = st.text_input("验证码", key="reg_code", placeholder="请输入验证码")
        
        if st.button("注册", type="primary", use_container_width=True):
            if reg_password != confirm_password:
                st.error("两次输入的密码不一致")
            elif len(reg_password) < 4:
                st.error("密码至少4位")
            elif verify_code != "123456":
                st.error("验证码错误")
            else:
                user_id, msg = create_user_by_email(reg_email, reg_password, reg_username if reg_username else None)
                if user_id:
                    st.success("✅ 注册成功！请登录")
                else:
                    st.error(msg)
    
    # ==================== 手机号注册 ====================
    with tab3:
        reg_phone = st.text_input("手机号", key="reg_phone", placeholder="11位手机号")
        reg_username2 = st.text_input("用户名（可选）", key="reg_username2", placeholder="留空则自动生成")
        reg_password2 = st.text_input("密码", type="password", key="reg_password2")
        confirm_password2 = st.text_input("确认密码", type="password", key="reg_confirm2")
        
        st.info("💡 演示模式：验证码为 123456")
        verify_code2 = st.text_input("验证码", key="reg_code2", placeholder="请输入验证码")
        
        if st.button("注册", type="primary", use_container_width=True):
            if reg_password2 != confirm_password2:
                st.error("两次输入的密码不一致")
            elif len(reg_password2) < 4:
                st.error("密码至少4位")
            elif verify_code2 != "123456":
                st.error("验证码错误")
            else:
                user_id, msg = create_user_by_phone(reg_phone, reg_password2, reg_username2 if reg_username2 else None)
                if user_id:
                    st.success("✅ 注册成功！请登录")
                else:
                    st.error(msg)
    
    # 微信/支付宝绑定提示
    st.markdown("---")
    st.markdown("#### 🔗 第三方登录（即将支持）")
    col1, col2 = st.columns(2)
    with col1:
        st.button("📱 微信登录", disabled=True, use_container_width=True)
    with col2:
        st.button("💰 支付宝登录", disabled=True, use_container_width=True)

def show_user_info():
    """显示用户信息"""
    if st.session_state.mode == 'user' and st.session_state.user_id:
        user_info = get_user_by_id(st.session_state.user_id)
        if user_info:
            with st.expander("👤 账户信息"):
                st.write(f"用户名: {user_info['username']}")
                if user_info['email']:
                    st.write(f"邮箱: {user_info['email']}")
                if user_info['phone']:
                    st.write(f"手机号: {user_info['phone']}")
                st.write(f"注册时间: {user_info['created_at']}")
                if user_info['last_login']:
                    st.write(f"最后登录: {user_info['last_login']}")
            
            # 绑定第三方
            with st.expander("🔗 绑定第三方账号"):
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("绑定微信", use_container_width=True):
                        st.info("微信绑定功能开发中")
                with col2:
                    if st.button("绑定支付宝", use_container_width=True):
                        st.info("支付宝绑定功能开发中")
