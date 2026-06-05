import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image
import json
import numpy as np
import uuid

# 导入图片识别模块
from image_recognition import FoodImageRecognizer

st.set_page_config(
    page_title="健身营养助手",
    page_icon="💪",
    layout="wide"
)

# ==================== 加载数据 ====================
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
        {"器材": "登山机", "类型": "有氧", "消耗系数": 0.14, "说明": "高强度"},
        {"器材": "跳绳", "类型": "有氧", "消耗系数": 0.15, "说明": "高强度"},
        {"器材": "卧推架", "类型": "力量", "消耗系数": 0.07, "说明": "胸部训练"},
        {"器材": "深蹲架", "类型": "力量", "消耗系数": 0.09, "说明": "腿部训练"},
        {"器材": "引体向上架", "类型": "力量", "消耗系数": 0.07, "说明": "背部训练"},
        {"器材": "哑铃", "类型": "自由重量", "消耗系数": 0.06, "说明": "通用"},
        {"器材": "杠铃", "类型": "自由重量", "消耗系数": 0.07, "说明": "通用"},
        {"器材": "壶铃", "类型": "自由重量", "消耗系数": 0.10, "说明": "爆发力"},
        {"器材": "瑜伽", "类型": "柔韧", "消耗系数": 0.05, "说明": "放松"},
    ])
    return exercises

df_food = load_food_data()
df_exercise = load_exercise_data()

# ==================== 初始化识别器 ====================
def get_recognizer():
    api_key = os.environ.get("QWEN_API_KEY")
    if hasattr(st, 'secrets') and 'QWEN_API_KEY' in st.secrets:
        api_key = st.secrets['QWEN_API_KEY']
    if api_key:
        return FoodImageRecognizer(api_type="qwen", api_key=api_key)
    return None

# ==================== 用户信息 ====================
def init_user_profile():
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = {
            'gender': '男', 'age': 25, 'height': 170, 'weight': 70,
            'activity_level': '中等', 'goal': '减脂'
        }
    
    if 'bmr' not in st.session_state:
        profile = st.session_state.user_profile
        if profile['gender'] == '男':
            bmr = 66 + (13.7 * profile['weight']) + (5 * profile['height']) - (6.8 * profile['age'])
        else:
            bmr = 655 + (9.6 * profile['weight']) + (1.8 * profile['height']) - (4.7 * profile['age'])
        
        activity_factors = {'低': 1.2, '中等': 1.375, '高': 1.55, '非常高': 1.725}
        tdee = bmr * activity_factors.get(profile['activity_level'], 1.375)
        
        if profile['goal'] == '减脂':
            daily_target = tdee - 300
        elif profile['goal'] == '增肌':
            daily_target = tdee + 300
        else:
            daily_target = tdee
        
        st.session_state.daily_target = int(daily_target)
        st.session_state.bmr = int(bmr)

# ==================== 计算运动消耗 ====================
def calculate_exercise_calories(exercise_row, duration, weight, extra_weight=0):
    coeff = float(exercise_row['消耗系数'])
    return coeff * (weight + extra_weight) * duration

# ==================== 初始化 Session ====================
def init_session():
    if 'total_calories' not in st.session_state:
        st.session_state.total_calories = 0
    if 'total_protein' not in st.session_state:
        st.session_state.total_protein = 0
    if 'total_burned' not in st.session_state:
        st.session_state.total_burned = 0
    if 'food_records' not in st.session_state:
        st.session_state.food_records = []
    if 'exercise_records' not in st.session_state:
        st.session_state.exercise_records = []
    if 'current_meal' not in st.session_state:
        st.session_state.current_meal = "早餐"

init_user_profile()
init_session()

# ==================== CSS ====================
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
""", unsafe_allow_html=True)

# ==================== 头部 ====================
st.markdown("""
<div class="main-header">
    <h1>💪 健身营养助手</h1>
    <p>📸 拍照识别 | 🏋️ 累计记录 | 📊 摄入 vs 消耗</p>
</div>
""", unsafe_allow_html=True)

# ==================== 三列布局 ====================
col1, col2, col3 = st.columns([1, 1.5, 1.3], gap="medium")

# ==================== 左侧：个人信息 + 总览 ====================
with col1:
    st.markdown("### 👤 个人信息")
    
    with st.expander("编辑信息", expanded=False):
        gender = st.selectbox("性别", ["男", "女"], 
                              index=0 if st.session_state.user_profile['gender']=='男' else 1,
                              key="profile_gender")
        age = st.number_input("年龄", 15, 100, st.session_state.user_profile['age'], key="profile_age")
        height = st.number_input("身高(cm)", 100, 250, st.session_state.user_profile['height'], key="profile_height")
        weight = st.number_input("体重(kg)", 30, 200, st.session_state.user_profile['weight'], key="profile_weight")
        activity_level = st.selectbox("活动水平", ["低", "中等", "高", "非常高"], 
                                      index=["低", "中等", "高", "非常高"].index(st.session_state.user_profile['activity_level']),
                                      key="profile_activity")
        goal = st.selectbox("健身目标", ["减脂", "保持体重", "增肌"],
                           index=["减脂", "保持体重", "增肌"].index(st.session_state.user_profile['goal']),
                           key="profile_goal")
        
        if st.button("🔄 更新", use_container_width=True, key="profile_update"):
            st.session_state.user_profile = {
                'gender': gender, 'age': age, 'height': height, 'weight': weight,
                'activity_level': activity_level, 'goal': goal
            }
            if gender == '男':
                bmr = 66 + (13.7 * weight) + (5 * height) - (6.8 * age)
            else:
                bmr = 655 + (9.6 * weight) + (1.8 * height) - (4.7 * age)
            activity_factors = {'低': 1.2, '中等': 1.375, '高': 1.55, '非常高': 1.725}
            tdee = bmr * activity_factors[activity_level]
            if goal == '减脂':
                daily_target = tdee - 300
            elif goal == '增肌':
                daily_target = tdee + 300
            else:
                daily_target = tdee
            st.session_state.daily_target = int(daily_target)
            st.session_state.bmr = int(bmr)
            st.success("✅ 已更新")
            st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 摄入 vs 消耗")
    
    net = st.session_state.total_calories - st.session_state.total_burned
    remaining = st.session_state.daily_target - net
    
    st.metric("🔥 基础代谢", f"{st.session_state.bmr} kcal")
    st.metric("🎯 每日目标", f"{st.session_state.daily_target} kcal")
    
    st.markdown("#### 今日累计")
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("🍽️ 摄入", f"{st.session_state.total_calories:.0f} kcal")
    with col_b:
        st.metric("🏋️ 消耗", f"{st.session_state.total_burned:.0f} kcal")
    
    # 修复 progress bar
    if st.session_state.daily_target > 0:
        consumed = st.session_state.total_calories - st.session_state.total_burned
        progress_value = min(max(consumed / st.session_state.daily_target, 0.0), 1.0)
    else:
        progress_value = 0.0
    
    if remaining > 0:
        st.success(f"✅ 剩余: {remaining:.0f} kcal")
        st.progress(progress_value)
    else:
        st.error(f"⚠️ 超标: {-remaining:.0f} kcal")
        st.progress(1.0)
    
    st.markdown("---")
    if st.button("🗑️ 清空记录", use_container_width=True, key="clear_all"):
        st.session_state.total_calories = 0
        st.session_state.total_protein = 0
        st.session_state.total_burned = 0
        st.session_state.food_records = []
        st.session_state.exercise_records = []
        st.rerun()

# ==================== 中间：食物摄入模块 ====================
with col2:
    st.markdown("## 🍽️ 食物摄入")
    
    # 餐次选择
    meal_options = ["早餐", "午餐", "晚餐", "加餐"]
    selected_meal = st.selectbox("餐次", meal_options, key="meal_select")
    
    # 输入方式
    food_mode = st.radio("输入方式", ["手动搜索", "拍照识别"], horizontal=True, key="food_mode")
    
    # ===== 手动搜索 =====
    if food_mode == "手动搜索":
        # 搜索框和重量在一行
        col_search, col_weight = st.columns([3, 1])
        with col_search:
            search = st.text_input("食物名称", placeholder="鸡胸肉、米饭、西兰花...", key="food_search")
        with col_weight:
            food_weight = st.number_input("重量(g)", 10, 1000, 100, 50, key="food_w")
        
        if search:
            # 搜索匹配
            results = df_food[df_food['名称'].str.contains(search, na=False)]
            
            if len(results) == 0:
                st.warning("未找到该食物，尝试其他关键词")
            else:
                # 显示结果列表
                for idx, row in results.head(10).iterrows():
                    cal_per_100g = row['热量']
                    pro_per_100g = row['蛋白质']
                    cal = cal_per_100g * food_weight / 100
                    pro = pro_per_100g * food_weight / 100
                    
                    # 使用容器显示每个食物
                    with st.container():
                        col_name, col_cal, col_pro, col_btn = st.columns([2.5, 1, 1.2, 1])
                        col_name.write(f"**{row['名称']}**")
                        col_name.caption(row['类别'])
                        col_cal.write(f"{cal:.0f} kcal")
                        col_pro.write(f"蛋白质 {pro:.0f}g")
                        
                        # 添加按钮 - 使用唯一的key
                        btn_key = f"add_food_{selected_meal}_{row['名称']}_{idx}_{uuid.uuid4().hex[:6]}"
                        if col_btn.button("➕", key=btn_key, use_container_width=True):
                            # 更新总量
                            st.session_state.total_calories += cal
                            st.session_state.total_protein += pro
                            # 添加记录
                            st.session_state.food_records.append({
                                '时间': datetime.now().strftime("%H:%M"),
                                '餐次': selected_meal,
                                '名称': row['名称'],
                                '重量': food_weight,
                                '热量': cal,
                                '蛋白质': pro,
                                '来源': '手动'
                            })
                            st.success(f"✅ 已添加 {row['名称']} ({food_weight}g) 到{selected_meal}")
                            st.rerun()
                    st.divider()
    
    # ===== 拍照识别 =====
    else:
        recognizer = get_recognizer()
        if recognizer is None:
            st.warning("⚠️ 未配置 API Key，拍照识别功能不可用")
        else:
            input_method = st.radio("图片来源", ["手机拍照", "相册上传"], horizontal=True, key="food_input_method")
            
            uploaded_file = None
            if input_method == "手机拍照":
                uploaded_file = st.camera_input("拍照", key="food_camera")
            else:
                uploaded_file = st.file_uploader("选择图片", type=['jpg', 'jpeg', 'png'], key="food_upload")
            
            if uploaded_file:
                image = Image.open(uploaded_file)
                st.image(image, caption="图片", use_container_width=True)
                
                if st.button("识别食物", type="primary", key="food_recognize"):
                    with st.spinner("AI识别中..."):
                        temp_path = f"/tmp/food_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        image.save(temp_path)
                        result = recognizer.recognize_food(temp_path)
                        os.remove(temp_path)
                        
                        if "error" in result:
                            st.error(f"识别失败: {result['error']}")
                        else:
                            foods = result.get("foods", [])
                            if not foods:
                                st.info("未识别到食物")
                            else:
                                for food in foods:
                                    name = food.get('name', '未知')
                                    fw = food.get('weight', 150)
                                    cal = food.get('calories', fw * 1.5)
                                    pro = food.get('protein', fw * 0.15)
                                    
                                    col_a, col_b, col_c = st.columns([2, 1, 1])
                                    col_a.write(f"**{name}**")
                                    col_b.write(f"{cal:.0f} kcal")
                                    col_c.write(f"蛋白质 {pro:.0f}g")
                                    
                                    btn_key = f"add_vision_{selected_meal}_{name}_{uuid.uuid4().hex[:6]}"
                                    if st.button("➕ 添加", key=btn_key):
                                        st.session_state.total_calories += cal
                                        st.session_state.total_protein += pro
                                        st.session_state.food_records.append({
                                            '时间': datetime.now().strftime("%H:%M"),
                                            '餐次': selected_meal,
                                            '名称': name,
                                            '重量': fw,
                                            '热量': cal,
                                            '蛋白质': pro,
                                            '来源': '拍照'
                                        })
                                        st.success(f"✅ 已添加 {name}")
                                        st.rerun()
    
    # 显示今日饮食记录
    st.markdown("---")
    st.markdown("### 📋 今日饮食")
    
    if len(st.session_state.food_records) > 0:
        # 按餐次分组显示
        for meal in ["早餐", "午餐", "晚餐", "加餐"]:
            meal_records = [r for r in st.session_state.food_records if r.get('餐次') == meal]
            if meal_records:
                st.markdown(f"**{meal}**")
                for r in meal_records:
                    st.write(f"  {r['时间']} | {r['名称']} | {r['重量']}g | {r['热量']:.0f}kcal | 蛋白质 {r['蛋白质']:.0f}g")
    else:
        st.info("暂无饮食记录")

# ==================== 右侧：运动消耗模块 ====================
with col3:
    st.markdown("## 🏋️ 运动消耗")
    
    exercise_mode = st.radio("输入方式", ["手动选择", "拍照识别"], horizontal=True, key="exercise_mode")
    
    # ===== 手动选择 =====
    if exercise_mode == "手动选择":
        exercise_name = st.selectbox("选择器材", df_exercise['器材'].tolist(), key="manual_exercise")
        selected = df_exercise[df_exercise['器材'] == exercise_name].iloc[0]
        st.caption(f"💡 {selected['说明']} | {selected['消耗系数']} kcal/kg/分钟")
        
        col_a, col_b = st.columns(2)
        with col_a:
            duration = st.number_input("时长(分钟)", 1, 180, 30, 5, key="manual_duration")
        with col_b:
            extra_weight = st.number_input("负重(kg)", 0, 100, 0, 5, key="manual_weight")
        
        calories = calculate_exercise_calories(selected, duration, weight, extra_weight)
        st.info(f"🔥 预计消耗: **{calories:.0f} kcal**")
        
        if st.button("✅ 记录运动", type="primary", use_container_width=True, key="manual_add"):
            st.session_state.total_burned += calories
            st.session_state.exercise_records.append({
                '时间': datetime.now().strftime("%H:%M"),
                '器材': exercise_name,
                '时长': duration,
                '负重': extra_weight,
                '消耗': calories,
                '来源': '手动'
            })
            st.success(f"✅ 已记录 {exercise_name} {duration}分钟")
            st.rerun()
    
    # ===== 拍照识别器材 =====
    else:
        recognizer = get_recognizer()
        if recognizer is None:
            st.warning("⚠️ 未配置 API Key")
        else:
            input_method = st.radio("图片来源", ["手机拍照", "相册上传"], horizontal=True, key="exercise_input_method")
            
            uploaded_file = None
            if input_method == "手机拍照":
                uploaded_file = st.camera_input("拍照", key="exercise_camera")
            else:
                uploaded_file = st.file_uploader("选择图片", type=['jpg', 'jpeg', 'png'], key="exercise_upload")
            
            if uploaded_file:
                image = Image.open(uploaded_file)
                st.image(image, caption="图片", use_container_width=True)
                
                if st.button("识别器材", key="exercise_recognize"):
                    with st.spinner("AI识别中..."):
                        temp_path = f"/tmp/exercise_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        image.save(temp_path)
                        result = recognizer.recognize_food(temp_path)
                        os.remove(temp_path)
                        
                        if "error" in result:
                            st.error(f"识别失败: {result['error']}")
                        else:
                            detected = result.get("foods", [{}])[0].get('name', '未知')
                            ex_name = st.text_input("器材名称", value=detected, key="detected_name")
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                duration = st.number_input("时长(分钟)", 1, 180, 30, 5, key="reco_duration")
                            with col_b:
                                extra_weight = st.number_input("负重(kg)", 0, 100, 0, 5, key="reco_weight")
                            
                            # 查找匹配的器材
                            matched = df_exercise[df_exercise['器材'].str.contains(ex_name[:4], na=False)]
                            if len(matched) > 0:
                                calories = matched.iloc[0]['消耗系数'] * (weight + extra_weight) * duration
                                st.info(f"🔥 预计消耗: **{calories:.0f} kcal**")
                                
                                if st.button("✅ 记录", key="reco_add"):
                                    st.session_state.total_burned += calories
                                    st.session_state.exercise_records.append({
                                        '时间': datetime.now().strftime("%H:%M"),
                                        '器材': ex_name,
                                        '时长': duration,
                                        '负重': extra_weight,
                                        '消耗': calories,
                                        '来源': '拍照'
                                    })
                                    st.success(f"✅ 已记录")
                                    st.rerun()
    
    # 显示今日运动记录
    st.markdown("---")
    st.markdown("### 📋 今日运动")
    
    if len(st.session_state.exercise_records) > 0:
        total_minutes = sum(r.get('时长', 0) for r in st.session_state.exercise_records)
        st.metric("🏋️ 总时长", f"{total_minutes} 分钟")
        for r in st.session_state.exercise_records[-15:]:
            st.write(f"  {r['时间']} | {r['器材']} | {r['时长']}分钟 | 🔥 {r['消耗']:.0f}kcal")
    else:
        st.info("暂无运动记录")

st.markdown("---")
st.markdown("<p style='text-align:center;color:gray'>📸 拍照识别 | 🏋️ 运动消耗 | 📊 摄入vs消耗</p>", unsafe_allow_html=True)
