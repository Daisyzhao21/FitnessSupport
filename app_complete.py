import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from PIL import Image
import uuid
import plotly.graph_objects as go
from supabase import create_client

from image_recognition import FoodImageRecognizer

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

# ==================== 用户管理 ====================
def get_or_create_user(email, username=None):
    result = supabase.table("user_profiles").select("*").eq("email", email).execute()
    if result.data:
        return result.data[0]
    
    final_username = username or email.split('@')[0]
    username_check = supabase.table("user_profiles").select("*").eq("username", final_username).execute()
    if username_check.data:
        final_username = f"{final_username}_{uuid.uuid4().hex[:4]}"
    
    new_user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "username": final_username,
        "created_at": datetime.now().isoformat(),
        "weight": 70,
        "height": 170,
        "gender": "男",
        "age": 25,
        "activity_level": "中等",
        "goal": "减脂"
    }
    
    try:
        insert_result = supabase.table("user_profiles").insert(new_user).execute()
        return insert_result.data[0] if insert_result.data else None
    except Exception as e:
        st.error(f"创建用户失败: {e}")
        return None

def get_user_profile(user_id):
    try:
        result = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        if result.data:
            return result.data[0]
    except:
        pass
    return {'weight': 70, 'height': 170, 'gender': '男', 'age': 25, 'activity_level': '中等', 'goal': '减脂'}

def update_user_profile(user_id, profile):
    try:
        supabase.table("user_profiles").update(profile).eq("id", user_id).execute()
        return True
    except:
        return False

# ==================== 数据操作函数 ====================
def save_food_record(user_id, record_date, meal, food_name, quantity, unit, calories, protein):
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
    try:
        result = supabase.table("food_records")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("record_date", record_date)\
            .order("created_at")\
            .execute()
        return result.data if result.data else []
    except:
        return []

def delete_food_record(record_id):
    try:
        supabase.table("food_records").delete().eq("id", record_id).execute()
        return True
    except:
        return False

def save_exercise_record(user_id, record_date, exercise_name, duration, extra_weight, calories):
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
    except:
        return False

def get_exercise_records(user_id, record_date):
    try:
        result = supabase.table("exercise_records")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("record_date", record_date)\
            .order("created_at")\
            .execute()
        return result.data if result.data else []
    except:
        return []

def delete_exercise_record(record_id):
    try:
        supabase.table("exercise_records").delete().eq("id", record_id).execute()
        return True
    except:
        return False

def get_trend_data(user_id, days=30):
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
    except:
        return [], []

# ==================== 加载食物运动数据 ====================
@st.cache_data
def load_food_data():
    df = pd.read_csv('food_nutrition.csv', encoding='utf-8-sig')
    return df

@st.cache_data
def load_exercise_data():
    return pd.read_csv('exercise_database.csv', encoding='utf-8-sig')

df_food = load_food_data()
df_exercise = load_exercise_data()

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
    return date.today().strftime("%Y-%m-%d")

def calculate_bmr(weight, height, age, gender):
    if gender == '男':
        return 66 + (13.7 * weight) + (5 * height) - (6.8 * age)
    else:
        return 655 + (9.6 * weight) + (1.8 * height) - (4.7 * age)

def get_daily_target(weight, height, age, gender, activity_level, goal):
    bmr = calculate_bmr(weight, height, age, gender)
    activity_factors = {'低': 1.2, '中等': 1.375, '高': 1.55, '非常高': 1.725}
    tdee = bmr * activity_factors.get(activity_level, 1.375)
    if goal == '减脂':
        return tdee - 300
    elif goal == '增肌':
        return tdee + 300
    else:
        return tdee

# ==================== UI ====================
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

# 登录逻辑
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if not st.session_state.user_id:
    st.markdown('<div class="main-header"><h1>💪 健身营养助手</h1><p>📸 拍照识别 | 🏋️ 运动记录 | 📊 摄入 vs 消耗</p></div>', unsafe_allow_html=True)
    
    st.markdown("### 🔐 登录/注册")
    st.info("💡 输入邮箱即可自动登录/注册，数据将云端保存")
    
    email = st.text_input("邮箱地址", key="login_email")
    username = st.text_input("用户名（可选）", key="login_username", placeholder="留空使用邮箱前缀")
    
    if st.button("登录 / 注册", type="primary", use_container_width=True):
        if email:
            with st.spinner("处理中..."):
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
    st.stop()

# ==================== 主界面 ====================
st.markdown('<div class="main-header"><h1>💪 健身营养助手</h1><p>📸 拍照识别 | 🏋️ 运动记录 | 📊 摄入 vs 消耗</p></div>', unsafe_allow_html=True)

# 用户信息栏
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
with col1:
    st.caption(f"👤 {st.session_state.get('user_email', '用户')}")
with col2:
    if st.button("📈 历史趋势", use_container_width=True):
        st.session_state.show_trend = True
with col3:
    if st.button("📥 导出数据", use_container_width=True):
        st.session_state.show_export = True
with col4:
    if st.button("🚪 退出", use_container_width=True):
        st.session_state.user_id = None
        st.rerun()

today = get_current_date()
foods = get_food_records(st.session_state.user_id, today)
exercises = get_exercise_records(st.session_state.user_id, today)

total_calories = sum(f.get('calories', 0) for f in foods)
total_burned = sum(e.get('calories', 0) for e in exercises)

# 获取用户资料
user_profile = get_user_profile(st.session_state.user_id)
user_weight = user_profile.get('weight', 70)
user_height = user_profile.get('height', 170)
user_gender = user_profile.get('gender', '男')
user_age = user_profile.get('age', 25)
user_activity = user_profile.get('activity_level', '中等')
user_goal = user_profile.get('goal', '减脂')

# 计算每日目标
daily_target = int(get_daily_target(user_weight, user_height, user_age, user_gender, user_activity, user_goal))
net = total_calories - total_burned
remaining = daily_target - net

# 显示统计卡片
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("🎯 每日目标", f"{daily_target} kcal")
col_b.metric("🍽️ 今日摄入", f"{total_calories:.0f} kcal")
col_c.metric("🏋️ 今日消耗", f"{total_burned:.0f} kcal")
if remaining > 0:
    col_d.metric("📊 剩余", f"{remaining:.0f} kcal", delta="还可吃")
else:
    col_d.metric("📊 超标", f"{-remaining:.0f} kcal", delta="已超标")

st.markdown("---")

# ==================== 三列布局 ====================
col_left, col_mid, col_right = st.columns([1, 1.5, 1.3])

# ==================== 左侧：个人信息（完整版）====================
with col_left:
    st.markdown("### 👤 个人信息")
    
    with st.expander("📝 编辑个人信息", expanded=False):
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            new_gender = st.selectbox("性别", ["男", "女"], index=0 if user_gender == '男' else 1)
            new_age = st.number_input("年龄", 15, 100, user_age)
        with col_g2:
            new_height = st.number_input("身高(cm)", 100, 250, user_height)
            new_weight = st.number_input("体重(kg)", 30, 200, user_weight)
        
        new_activity = st.selectbox("活动水平", ["低", "中等", "高", "非常高"], 
                                    index=["低", "中等", "高", "非常高"].index(user_activity))
        new_goal = st.selectbox("健身目标", ["减脂", "保持体重", "增肌"],
                               index=["减脂", "保持体重", "增肌"].index(user_goal))
        
        if st.button("💾 保存个人信息", use_container_width=True):
            new_profile = {
                "gender": new_gender,
                "age": new_age,
                "height": new_height,
                "weight": new_weight,
                "activity_level": new_activity,
                "goal": new_goal
            }
            update_user_profile(st.session_state.user_id, new_profile)
            st.success("✅ 个人信息已保存")
            st.rerun()
    
    # 显示当前信息摘要
    st.info(f"📏 {user_height}cm | ⚖️ {user_weight}kg | 🎯 {user_goal}")
    
    # 进度条
    st.markdown("#### 📊 今日进度")
    progress = min(max(total_calories / daily_target, 0), 1) if daily_target > 0 else 0
    st.progress(progress)
    st.caption(f"已完成 {progress*100:.0f}%")
    
    if st.button("🗑️ 清空今日记录", use_container_width=True):
        for f in foods:
            delete_food_record(f['id'])
        for e in exercises:
            delete_exercise_record(e['id'])
        st.rerun()

# ==================== 中间：食物摄入 ====================
with col_mid:
    st.markdown("## 🍽️ 食物摄入")
    mode = st.radio("方式", ["🔍 手动搜索", "📸 拍照识别"], horizontal=True)
    meal = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"])
    
    if mode == "🔍 手动搜索":
        term = st.text_input("🔍 搜索食物", placeholder="鸡胸肉、鸡蛋、米饭、红烧肉...")
        if term:
            results = df_food[df_food['名称'].str.contains(term, na=False)].head(10)
            if len(results) == 0:
                st.warning(f"未找到 '{term}'")
            for _, row in results.iterrows():
                unit = row.get('单位', 'g') if pd.notna(row.get('单位')) else 'g'
                config = UNIT_CONFIG.get(unit, UNIT_CONFIG['g'])
                std_qty = row.get('标准量', 100) if pd.notna(row.get('标准量')) else 100
                
                cols = st.columns([2, 0.8, 1.2, 0.8])
                cols[0].markdown(f"**{row['名称']}**")
                cols[0].caption(f"{row['类别']} | {row['热量']} kcal/{unit}")
                
                qty = cols[2].number_input(config['label'], config['min'], config['max'], config['default'], config['step'], 
                                           key=f"qty_{row['名称']}_{uuid.uuid4().hex[:4]}", label_visibility="collapsed")
                
                cal = row['热量'] * qty / std_qty
                cols[3].write(f"{cal:.0f} kcal")
                
                if cols[3].button("➕", key=f"add_{row['名称']}_{uuid.uuid4().hex[:4]}"):
                    save_food_record(st.session_state.user_id, today, meal, row['名称'], qty, unit, cal, row['蛋白质'] * qty / std_qty)
                    st.success(f"✅ 已添加 {row['名称']}")
                    st.rerun()
                st.divider()
    
    else:
        recognizer = get_recognizer()
        if recognizer:
            st.info("📸 拍照识别食物")
            input_method = st.radio("图片来源", ["📱 手机拍照", "📁 相册上传"], horizontal=True)
            
            img = None
            if input_method == "📱 手机拍照":
                img = st.camera_input("拍照", key="food_camera")
            else:
                img = st.file_uploader("选择图片", type=['jpg', 'jpeg', 'png'], key="food_upload")
            
            if img:
                image = Image.open(img)
                st.image(image, caption="预览", use_container_width=True)
                if st.button("🔍 识别食物", type="primary"):
                    with st.spinner("AI识别中..."):
                        temp_path = f"/tmp/food_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        image.save(temp_path)
                        res = recognizer.recognize_food(temp_path)
                        os.remove(temp_path)
                        if "error" in res:
                            st.error(f"识别失败: {res['error']}")
                        else:
                            for f in res.get("foods", []):
                                name = f.get('name', '未知')
                                weight_val = f.get('weight', 150)
                                cal = f.get('calories', weight_val * 1.5)
                                pro = f.get('protein', weight_val * 0.15)
                                col1, col2 = st.columns([3, 1])
                                col1.write(f"**{name}** - {weight_val}g, {cal:.0f}kcal")
                                if col2.button(f"➕", key=f"vision_{name}"):
                                    save_food_record(st.session_state.user_id, today, meal, name, weight_val, 'g', cal, pro)
                                    st.success(f"✅ 已添加 {name}")
                                    st.rerun()
        else:
            st.warning("⚠️ 未配置 API Key，拍照识别功能不可用")
            st.info("请在终端设置: export QWEN_API_KEY='你的key'")
    
    # 显示今日饮食记录
    st.markdown("---")
    st.markdown("### 📋 今日饮食")
    if foods:
        for m in ["早餐", "午餐", "晚餐", "加餐"]:
            meals_foods = [f for f in foods if f.get('meal') == m]
            if meals_foods:
                st.markdown(f"**{m}**")
                for f in meals_foods:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"  {f['food_name']} | {f['quantity']}{f.get('unit', 'g')} | {f['calories']:.0f}kcal | 蛋白质 {f.get('protein', 0):.0f}g")
                    with col2:
                        if st.button("🗑️", key=f"del_food_{f['id']}"):
                            delete_food_record(f['id'])
                            st.rerun()
    else:
        st.info("暂无记录，请搜索添加食物")

# ==================== 右侧：运动消耗（完整版）====================
with col_right:
    st.markdown("## 🏋️ 运动消耗")
    mode_ex = st.radio("方式", ["🔍 选择器材", "✏️ 自定义运动", "📸 拍照识别"], horizontal=True)
    
    if mode_ex == "🔍 选择器材":
        ex_name = st.selectbox("选择运动", df_exercise['器材'].tolist())
        ex = df_exercise[df_exercise['器材'] == ex_name].iloc[0]
        st.caption(f"💡 {ex['说明']} | 消耗系数: {ex['消耗系数']} kcal/kg/分钟")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            dur = st.number_input("时长(分钟)", 1, 180, 30, 5)
        with col_d2:
            extra = st.number_input("负重(kg)", 0, 100, 0, 5)
        
        cal = ex['消耗系数'] * (user_weight + extra) * dur
        st.info(f"🔥 预计消耗: **{cal:.0f} kcal**")
        
        if st.button("✅ 记录运动", type="primary", use_container_width=True):
            save_exercise_record(st.session_state.user_id, today, ex_name, dur, extra, cal)
            st.success(f"✅ 已记录 {ex_name} {dur}分钟")
            st.rerun()
    
    elif mode_ex == "✏️ 自定义运动":
        custom_name = st.text_input("运动名称", placeholder="例如: 俯卧撑、卷腹、波比跳...")
        custom_coeff = st.number_input("消耗系数", 0.01, 0.50, 0.08, 0.01, help="参考: 跑步0.12, 跳绳0.15, 力量0.07")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            dur = st.number_input("时长(分钟)", 1, 180, 30, 5, key="custom_dur")
        with col_d2:
            extra = st.number_input("负重(kg)", 0, 100, 0, 5, key="custom_extra")
        
        if custom_name:
            cal = custom_coeff * (user_weight + extra) * dur
            st.info(f"🔥 {custom_name} 预计消耗: **{cal:.0f} kcal**")
            if st.button("✅ 记录自定义运动", type="primary", use_container_width=True):
                save_exercise_record(st.session_state.user_id, today, custom_name, dur, extra, cal)
                st.success(f"✅ 已记录 {custom_name}")
                st.rerun()
    
    else:
        recognizer = get_recognizer()
        if recognizer:
            st.info("📸 拍照识别器材")
            input_method = st.radio("图片来源", ["📱 手机拍照", "📁 相册上传"], horizontal=True, key="ex_input_method")
            
            img = None
            if input_method == "📱 手机拍照":
                img = st.camera_input("拍照", key="ex_camera")
            else:
                img = st.file_uploader("选择图片", type=['jpg', 'jpeg', 'png'], key="ex_upload")
            
            if img:
                image = Image.open(img)
                st.image(image, caption="预览", use_container_width=True)
                if st.button("🔍 识别器材"):
                    with st.spinner("AI识别中..."):
                        temp_path = f"/tmp/ex_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        image.save(temp_path)
                        res = recognizer.recognize_food(temp_path)
                        os.remove(temp_path)
                        if "error" in res:
                            st.error(f"识别失败: {res['error']}")
                        else:
                            detected = res.get("foods", [{}])[0].get('name', '未知器材')
                            ex_name = st.text_input("器材名称", value=detected)
                            col_d1, col_d2 = st.columns(2)
                            with col_d1:
                                dur = st.number_input("时长(分钟)", 1, 180, 30, 5, key="reco_dur")
                            with col_d2:
                                extra = st.number_input("负重(kg)", 0, 100, 0, 5, key="reco_extra")
                            
                            cal = 0.08 * (user_weight + extra) * dur
                            st.info(f"🔥 预计消耗: **{cal:.0f} kcal**")
                            if st.button("✅ 记录", key="reco_add"):
                                save_exercise_record(st.session_state.user_id, today, ex_name, dur, extra, cal)
                                st.success(f"✅ 已记录 {ex_name}")
                                st.rerun()
        else:
            st.warning("⚠️ 未配置 API Key")
    
    # 显示今日运动记录
    st.markdown("---")
    st.markdown("### 📋 今日运动")
    if exercises:
        total_min = sum(e.get('duration', 0) for e in exercises)
        st.metric("总运动时长", f"{total_min} 分钟")
        for e in exercises:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"  {e['exercise_name']} | {e['duration']}分钟 | {e['calories']:.0f}kcal")
            with col2:
                if st.button("🗑️", key=f"del_ex_{e['id']}"):
                    delete_exercise_record(e['id'])
                    st.rerun()
    else:
        st.info("暂无运动记录")

# ==================== 历史趋势弹窗 ====================
if st.session_state.get('show_trend', False):
    st.markdown("---")
    st.markdown("## 📈 历史热量趋势")
    
    food_trend, exercise_trend = get_trend_data(st.session_state.user_id)
    
    if food_trend or exercise_trend:
        dates = set()
        food_dict = {}
        exercise_dict = {}
        
        for f in food_trend:
            dates.add(f['record_date'])
            food_dict[f['record_date']] = food_dict.get(f['record_date'], 0) + f['calories']
        for e in exercise_trend:
            dates.add(e['record_date'])
            exercise_dict[e['record_date']] = exercise_dict.get(e['record_date'], 0) + e['calories']
        
        sorted_dates = sorted(dates)
        food_vals = [food_dict.get(d, 0) for d in sorted_dates]
        exercise_vals = [exercise_dict.get(d, 0) for d in sorted_dates]
        net_vals = [food_vals[i] - exercise_vals[i] for i in range(len(sorted_dates))]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=sorted_dates, y=food_vals, mode='lines+markers', name='摄入', line=dict(color='#ff6b6b', width=2)))
        fig.add_trace(go.Scatter(x=sorted_dates, y=exercise_vals, mode='lines+markers', name='消耗', line=dict(color='#4ecdc4', width=2)))
        fig.add_trace(go.Scatter(x=sorted_dates, y=net_vals, mode='lines+markers', name='净摄入', line=dict(color='#667eea', width=2, dash='dash')))
        fig.update_layout(title="30天热量趋势", xaxis_title="日期", yaxis_title="热量 (kcal)", height=450)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无历史数据")
    
    if st.button("关闭", use_container_width=True):
        st.session_state.show_trend = False
        st.rerun()

# ==================== 导出数据弹窗 ====================
if st.session_state.get('show_export', False):
    st.markdown("---")
    st.markdown("## 📥 导出数据")
    
    from datetime import timedelta
    col1, col2 = st.columns(2)
    with col1:
        export_start = st.date_input("开始日期", date.today() - timedelta(days=30))
    with col2:
        export_end = st.date_input("结束日期", date.today())
    
    if st.button("生成 CSV", use_container_width=True):
        # 获取指定日期范围的数据
        start_str = export_start.strftime("%Y-%m-%d")
        end_str = export_end.strftime("%Y-%m-%d")
        
        try:
            food_result = supabase.table("food_records")\
                .select("*")\
                .eq("user_id", st.session_state.user_id)\
                .gte("record_date", start_str)\
                .lte("record_date", end_str)\
                .execute()
            
            exercise_result = supabase.table("exercise_records")\
                .select("*")\
                .eq("user_id", st.session_state.user_id)\
                .gte("record_date", start_str)\
                .lte("record_date", end_str)\
                .execute()
            
            if food_result.data:
                food_df = pd.DataFrame(food_result.data)
                csv1 = food_df.to_csv(index=False)
                st.download_button("📥 下载饮食记录", csv1, f"food_records_{start_str}_{end_str}.csv", "text/csv")
            
            if exercise_result.data:
                exercise_df = pd.DataFrame(exercise_result.data)
                csv2 = exercise_df.to_csv(index=False)
                st.download_button("📥 下载运动记录", csv2, f"exercise_records_{start_str}_{end_str}.csv", "text/csv")
            
            if not food_result.data and not exercise_result.data:
                st.info("所选日期范围内无数据")
        except Exception as e:
            st.error(f"导出失败: {e}")
    
    if st.button("关闭", use_container_width=True):
        st.session_state.show_export = False
        st.rerun()

st.markdown("---")
st.markdown("<p style='text-align:center;color:gray'>🔍 手动搜索 | 📸 拍照识别 | 🏋️ 运动记录 | ✏️ 自定义运动 | 💾 云端保存</p>", unsafe_allow_html=True)
