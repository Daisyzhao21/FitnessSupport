import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from PIL import Image
import uuid
import plotly.graph_objects as go
from supabase import create_client
import hashlib

from image_recognition import FoodImageRecognizer
from email_service import send_daily_report_email, is_sendgrid_configured

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

# ==================== 密码加密 ====================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ==================== 用户管理 ====================
def create_user(email, password, username=None):
    """创建新用户"""
    result = supabase.table("user_profiles").select("*").eq("email", email).execute()
    if result.data:
        return None, "邮箱已存在"
    
    final_username = username or email.split('@')[0]
    username_check = supabase.table("user_profiles").select("*").eq("username", final_username).execute()
    if username_check.data:
        final_username = f"{final_username}_{uuid.uuid4().hex[:4]}"
    
    new_user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "username": final_username,
        "password": hash_password(password),
        "weight": 70.0,
        "height": 170.0,
        "gender": "男",
        "age": 25,
        "activity_level": "中等",
        "goal": "减脂",
        "created_at": datetime.now().isoformat()
    }
    try:
        insert_result = supabase.table("user_profiles").insert(new_user).execute()
        return insert_result.data[0], "注册成功"
    except Exception as e:
        return None, f"注册失败: {e}"

def login_user(email, password):
    """用户登录"""
    result = supabase.table("user_profiles").select("*").eq("email", email).execute()
    if not result.data:
        return None, "邮箱不存在"
    
    user = result.data[0]
    if user.get('password') == hash_password(password):
        return user, "登录成功"
    else:
        return None, "密码错误"

def get_user_profile(user_id):
    try:
        result = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        if result.data:
            return result.data[0]
    except:
        pass
    return None

def update_user_profile(user_id, profile):
    try:
        supabase.table("user_profiles").update(profile).eq("id", user_id).execute()
        return True
    except:
        return False

# ==================== 数据操作函数 ====================
def save_food_record(user_id, date_str, meal, food_name, quantity, calories, protein):
    if not user_id:
        return False
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
    except:
        return False

def get_food_records(user_id, date_str):
    if not user_id:
        return []
    try:
        result = supabase.table("food_records")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("record_date", date_str)\
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

def save_exercise_record(user_id, date_str, exercise_name, duration, extra_weight, calories):
    if not user_id:
        return False
    try:
        data = {
            "user_id": user_id,
            "record_date": date_str,
            "exercise_name": exercise_name,
            "duration": duration,
            "extra_weight": extra_weight,
            "calories": calories
        }
        supabase.table("exercise_records").insert(data).execute()
        return True
    except:
        return False

def get_exercise_records(user_id, date_str):
    if not user_id:
        return []
    try:
        result = supabase.table("exercise_records")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("record_date", date_str)\
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
    if not user_id:
        return [], []
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

def calculate_bmr(weight, height, age, gender):
    w = float(weight) if weight else 70
    h = float(height) if height else 170
    a = int(age) if age else 25
    if gender == '男':
        return 66 + (13.7 * w) + (5 * h) - (6.8 * a)
    else:
        return 655 + (9.6 * w) + (1.8 * h) - (4.7 * a)

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

# ==================== 初始化 Session State ====================
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'show_trend' not in st.session_state:
    st.session_state.show_trend = False
if 'show_email' not in st.session_state:
    st.session_state.show_email = False
if 'show_auth' not in st.session_state:
    st.session_state.show_auth = False

if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        'weight': 70,
        'height': 170,
        'gender': '男',
        'age': 25,
        'activity_level': '中等',
        'goal': '减脂'
    }

if 'food_records' not in st.session_state:
    st.session_state.food_records = []
if 'exercise_records' not in st.session_state:
    st.session_state.exercise_records = []
if 'total_calories' not in st.session_state:
    st.session_state.total_calories = 0
if 'total_burned' not in st.session_state:
    st.session_state.total_burned = 0

# ==================== 登录/注册弹窗 ====================
def show_auth_modal():
    st.markdown("### 🔐 登录/注册")
    
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        login_email = st.text_input("邮箱", key="login_email")
        login_password = st.text_input("密码", type="password", key="login_password")
        if st.button("登录", type="primary", use_container_width=True, key="login_btn"):
            if login_email and login_password:
                user, msg = login_user(login_email, login_password)
                if user:
                    st.session_state.user_id = user['id']
                    st.session_state.user_email = login_email
                    profile = get_user_profile(user['id'])
                    if profile:
                        st.session_state.user_profile = {
                            'weight': profile.get('weight', 70),
                            'height': profile.get('height', 170),
                            'gender': profile.get('gender', '男'),
                            'age': profile.get('age', 25),
                            'activity_level': profile.get('activity_level', '中等'),
                            'goal': profile.get('goal', '减脂')
                        }
                    today = get_current_date()
                    st.session_state.food_records = get_food_records(user['id'], today)
                    st.session_state.exercise_records = get_exercise_records(user['id'], today)
                    st.session_state.total_calories = sum(f.get('calories', 0) for f in st.session_state.food_records)
                    st.session_state.total_burned = sum(e.get('calories', 0) for e in st.session_state.exercise_records)
                    st.session_state.show_auth = False
                    st.success("✅ 登录成功！")
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("请输入邮箱和密码")
    
    with tab2:
        reg_email = st.text_input("邮箱", key="reg_email")
        reg_password = st.text_input("密码", type="password", key="reg_password")
        reg_confirm = st.text_input("确认密码", type="password", key="reg_confirm")
        reg_username = st.text_input("用户名（可选）", key="reg_username", placeholder="留空使用邮箱前缀")
        if st.button("注册", type="primary", use_container_width=True, key="register_btn"):
            if not reg_email or not reg_password:
                st.warning("请填写邮箱和密码")
            elif reg_password != reg_confirm:
                st.error("两次输入的密码不一致")
            elif len(reg_password) < 4:
                st.error("密码至少4位")
            else:
                user, msg = create_user(reg_email, reg_password, reg_username if reg_username else None)
                if user:
                    st.success("✅ 注册成功！请登录")
                else:
                    st.error(msg)
    
    if st.button("继续试用", use_container_width=True, key="continue_btn"):
        st.session_state.show_auth = False
        st.rerun()

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

st.markdown('<div class="main-header"><h1>💪 健身营养助手</h1><p>📸 拍照识别 | 🏋️ 运动记录 | 📊 摄入 vs 消耗</p></div>', unsafe_allow_html=True)

# 用户栏
col1, col2, col3, col4, col5 = st.columns([1.5, 0.8, 0.8, 0.8, 0.8])
with col1:
    if st.session_state.user_id:
        st.caption(f"👤 {st.session_state.get('user_email', '用户')}")
    else:
        st.caption("👤 访客模式")
with col2:
    if st.session_state.user_id:
        if st.button("📝 资料", use_container_width=True, key="profile_btn"):
            st.session_state.show_profile = not st.session_state.get('show_profile', False)
    else:
        if st.button("🔐 登录", use_container_width=True, key="auth_btn"):
            st.session_state.show_auth = True
with col3:
    if st.session_state.user_id:
        if st.button("📈 趋势", use_container_width=True, key="trend_btn"):
            st.session_state.show_trend = True
    else:
        st.button("📈 趋势", disabled=True, use_container_width=True, key="trend_disabled")
with col4:
    if st.session_state.user_id:
        if st.button("📧 报告", use_container_width=True, key="email_btn"):
            st.session_state.show_email = True
    else:
        st.button("📧 报告", disabled=True, use_container_width=True, key="email_disabled")
with col5:
    if st.session_state.user_id:
        if st.button("🚪 退出", use_container_width=True, key="logout_btn"):
            st.session_state.user_id = None
            st.session_state.user_email = None
            st.rerun()

# 登录弹窗
if st.session_state.get('show_auth', False):
    show_auth_modal()
    st.stop()

# 个人信息编辑（在左侧栏直接显示）
today = get_current_date()
foods = st.session_state.food_records
exercises = st.session_state.exercise_records

total_calories = st.session_state.total_calories
total_burned = st.session_state.total_burned

user_profile = st.session_state.user_profile
user_weight = float(user_profile.get('weight', 70))
user_height = float(user_profile.get('height', 170))
user_gender = user_profile.get('gender', '男')
user_age = int(user_profile.get('age', 25))
user_activity = user_profile.get('activity_level', '中等')
user_goal = user_profile.get('goal', '减脂')

daily_target = int(get_daily_target(user_weight, user_height, user_age, user_gender, user_activity, user_goal))
remaining = daily_target - (total_calories - total_burned)

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("🎯 每日目标", f"{daily_target} kcal")
col_b.metric("🍽️ 今日摄入", f"{total_calories:.0f} kcal")
col_c.metric("🏋️ 今日消耗", f"{total_burned:.0f} kcal")
if remaining > 0:
    col_d.metric("📊 剩余", f"{remaining:.0f} kcal")
else:
    col_d.metric("📊 超标", f"{-remaining:.0f} kcal")

st.markdown("---")

col_left, col_mid, col_right = st.columns([1, 1.5, 1.3])

# ==================== 左侧：个人信息（可直接编辑）====================
with col_left:
    st.markdown("### 👤 个人信息")
    
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        new_weight = st.number_input("体重(kg)", 30, 200, int(user_weight), key="edit_weight")
        new_height = st.number_input("身高(cm)", 100, 250, int(user_height), key="edit_height")
        new_age = st.number_input("年龄", 15, 100, user_age, key="edit_age")
    with col_w2:
        new_gender = st.selectbox("性别", ["男", "女"], index=0 if user_gender == '男' else 1, key="edit_gender")
        new_activity = st.selectbox("活动水平", ["低", "中等", "高", "非常高"], 
                                    index=["低", "中等", "高", "非常高"].index(user_activity), key="edit_activity")
        new_goal = st.selectbox("健身目标", ["减脂", "保持体重", "增肌"],
                               index=["减脂", "保持体重", "增肌"].index(user_goal), key="edit_goal")
    
    if st.button("💾 保存个人信息", use_container_width=True, key="save_profile"):
        st.session_state.user_profile = {
            'weight': float(new_weight),
            'height': float(new_height),
            'gender': new_gender,
            'age': new_age,
            'activity_level': new_activity,
            'goal': new_goal
        }
        if st.session_state.user_id:
            update_user_profile(st.session_state.user_id, st.session_state.user_profile)
        st.success("✅ 已保存")
        st.rerun()
    
    progress = min(total_calories / daily_target, 1) if daily_target > 0 else 0
    st.progress(progress)
    st.caption(f"今日进度 {progress*100:.0f}%")
    
    if st.button("🗑️ 清空今日记录", use_container_width=True, key="clear_records"):
        st.session_state.food_records = []
        st.session_state.exercise_records = []
        st.session_state.total_calories = 0
        st.session_state.total_burned = 0
        if st.session_state.user_id:
            for f in foods:
                if 'id' in f:
                    delete_food_record(f['id'])
            for e in exercises:
                if 'id' in e:
                    delete_exercise_record(e['id'])
        st.rerun()

# ==================== 中间：食物摄入 ====================
with col_mid:
    st.markdown("## 🍽️ 食物摄入")
    mode = st.radio("方式", ["🔍 手动搜索", "📸 拍照识别"], horizontal=True)
    meal = st.selectbox("餐次", ["早餐", "午餐", "晚餐", "加餐"])
    
    if mode == "🔍 手动搜索":
        term = st.text_input("🔍 搜索食物", placeholder="鸡胸肉、鸡蛋、米饭...")
        if term:
            results = df_food[df_food['名称'].str.contains(term, na=False)].head(8)
            if len(results) == 0:
                st.warning(f"未找到 '{term}'")
            for idx, row in results.iterrows():
                unit = row.get('单位', 'g') if pd.notna(row.get('单位')) else 'g'
                config = UNIT_CONFIG.get(unit, UNIT_CONFIG['g'])
                std_qty = row.get('标准量', 100) if pd.notna(row.get('标准量')) else 100
                
                cols = st.columns([2, 0.8, 1.2, 0.8])
                cols[0].markdown(f"**{row['名称']}**")
                cols[0].caption(f"{row['类别']} | {row['热量']} kcal/{unit}")
                
                qty = cols[2].number_input(config['label'], config['min'], config['max'], config['default'], config['step'], 
                                           key=f"qty_{row['名称']}_{idx}", label_visibility="collapsed")
                
                cal = row['热量'] * qty / std_qty
                cols[3].write(f"{cal:.0f} kcal")
                
                if cols[3].button("➕", key=f"add_{row['名称']}_{idx}"):
                    st.session_state.food_records.append({
                        'meal': meal, 'food_name': row['名称'], 'quantity': qty,
                        'calories': cal, 'protein': row['蛋白质'] * qty / std_qty
                    })
                    st.session_state.total_calories += cal
                    if st.session_state.user_id:
                        save_food_record(st.session_state.user_id, today, meal, row['名称'], qty, cal, row['蛋白质'] * qty / std_qty)
                    st.success(f"✅ 已添加 {row['名称']}")
                    st.rerun()
                st.divider()
    
    else:
        recognizer = get_recognizer()
        if recognizer:
            img = st.camera_input("拍照", key="food_camera")
            if img:
                image = Image.open(img)
                st.image(image, caption="预览", use_container_width=True)
                if st.button("识别食物", key="recognize_food"):
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
                                if st.button(f"➕ 添加 {name}", key=f"vision_add_{name}"):
                                    st.session_state.food_records.append({
                                        'meal': meal, 'food_name': name, 'quantity': weight_val,
                                        'calories': cal, 'protein': pro
                                    })
                                    st.session_state.total_calories += cal
                                    if st.session_state.user_id:
                                        save_food_record(st.session_state.user_id, today, meal, name, weight_val, cal, pro)
                                    st.success(f"✅ 已添加 {name}")
                                    st.rerun()
        else:
            st.warning("⚠️ 未配置 API Key")
    
    st.markdown("---")
    st.markdown("### 📋 今日饮食")
    if foods:
        for m in ["早餐", "午餐", "晚餐", "加餐"]:
            meals_foods = [f for f in foods if f.get('meal') == m]
            if meals_foods:
                st.markdown(f"**{m}**")
                for i, f in enumerate(meals_foods):
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"  {f['food_name']} | {f['quantity']}g | {f['calories']:.0f}kcal")
                    if col2.button("🗑️", key=f"del_food_{m}_{i}_{f['food_name']}"):
                        if 'id' in f and st.session_state.user_id:
                            delete_food_record(f['id'])
                        st.session_state.food_records.remove(f)
                        st.session_state.total_calories -= f['calories']
                        st.rerun()
    else:
        st.info("暂无记录")

# ==================== 右侧：运动消耗 ====================
with col_right:
    st.markdown("## 🏋️ 运动消耗")
    mode_ex = st.radio("方式", ["🔍 选择器材", "✏️ 自定义运动", "📸 拍照识别"], horizontal=True)
    
    if mode_ex == "🔍 选择器材":
        exercise_search = st.text_input("🔍 搜索运动", placeholder="跑步机、深蹲、卧推...")
        if exercise_search:
            filtered = df_exercise[df_exercise['器材'].str.contains(exercise_search, na=False)]
        else:
            filtered = df_exercise
        
        if len(filtered) == 0:
            st.warning(f"未找到 '{exercise_search}'")
            filtered = df_exercise
        
        ex_name = st.selectbox("选择运动", filtered['器材'].tolist())
        ex = df_exercise[df_exercise['器材'] == ex_name].iloc[0]
        st.caption(f"💡 {ex['说明']} | 消耗系数: {ex['消耗系数']} kcal/kg/分钟")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            dur = st.number_input("时长(分钟)", 1, 180, 30, 5)
        with col_d2:
            extra = st.number_input("负重(kg)", 0, 100, 0, 5)
        
        cal = ex['消耗系数'] * (user_weight + extra) * dur
        st.info(f"🔥 预计消耗: **{cal:.0f} kcal**")
        
        if st.button("✅ 记录运动", type="primary", use_container_width=True, key="record_exercise"):
            st.session_state.exercise_records.append({
                'exercise_name': ex_name, 'duration': dur, 'extra_weight': extra, 'calories': cal
            })
            st.session_state.total_burned += cal
            if st.session_state.user_id:
                save_exercise_record(st.session_state.user_id, today, ex_name, dur, extra, cal)
            st.success(f"✅ 已记录 {ex_name}")
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
            if st.button("✅ 记录自定义运动", type="primary", use_container_width=True, key="record_custom"):
                st.session_state.exercise_records.append({
                    'exercise_name': custom_name, 'duration': dur, 'extra_weight': extra, 'calories': cal
                })
                st.session_state.total_burned += cal
                if st.session_state.user_id:
                    save_exercise_record(st.session_state.user_id, today, custom_name, dur, extra, cal)
                st.success(f"✅ 已记录 {custom_name}")
                st.rerun()
    
    else:
        recognizer = get_recognizer()
        if recognizer:
            st.info("📸 拍照识别器材")
            input_method = st.radio("图片来源", ["📱 手机拍照", "📁 相册上传"], horizontal=True)
            
            img = None
            if input_method == "📱 手机拍照":
                img = st.camera_input("拍照", key="ex_camera")
            else:
                img = st.file_uploader("选择图片", type=['jpg', 'jpeg', 'png'], key="ex_upload")
            
            if img:
                image = Image.open(img)
                st.image(image, caption="预览", use_container_width=True)
                if st.button("🔍 识别器材", key="recognize_exercise"):
                    with st.spinner("AI识别中..."):
                        temp_path = f"/tmp/ex_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        image.save(temp_path)
                        res = recognizer.recognize_food(temp_path)
                        os.remove(temp_path)
                        if "error" in res:
                            st.error(f"识别失败: {res['error']}")
                        else:
                            detected = res.get("foods", [{}])[0].get('name', '未知器材')
                            ex_name = st.text_input("器材名称", value=detected, key="detected_name")
                            col_d1, col_d2 = st.columns(2)
                            with col_d1:
                                dur = st.number_input("时长(分钟)", 1, 180, 30, 5, key="reco_dur")
                            with col_d2:
                                extra = st.number_input("负重(kg)", 0, 100, 0, 5, key="reco_extra")
                            
                            cal = 0.08 * (user_weight + extra) * dur
                            st.info(f"🔥 预计消耗: **{cal:.0f} kcal**")
                            if st.button("✅ 记录", key="reco_record"):
                                st.session_state.exercise_records.append({
                                    'exercise_name': ex_name, 'duration': dur, 'extra_weight': extra, 'calories': cal
                                })
                                st.session_state.total_burned += cal
                                if st.session_state.user_id:
                                    save_exercise_record(st.session_state.user_id, today, ex_name, dur, extra, cal)
                                st.success(f"✅ 已记录 {ex_name}")
                                st.rerun()
        else:
            st.warning("⚠️ 未配置 API Key")
    
    st.markdown("---")
    st.markdown("### 📋 今日运动")
    if exercises:
        total_min = sum(e.get('duration', 0) for e in exercises)
        st.metric("总运动时长", f"{total_min} 分钟")
        for i, e in enumerate(exercises):
            col1, col2 = st.columns([3, 1])
            col1.write(f"  {e['exercise_name']} | {e['duration']}分钟 | {e['calories']:.0f}kcal")
            if col2.button("🗑️", key=f"del_ex_{i}_{e['exercise_name']}"):
                if 'id' in e and st.session_state.user_id:
                    delete_exercise_record(e['id'])
                st.session_state.exercise_records.remove(e)
                st.session_state.total_burned -= e['calories']
                st.rerun()
    else:
        st.info("暂无运动记录")

# ==================== 历史趋势弹窗 ====================
if st.session_state.get('show_trend', False) and st.session_state.user_id:
    st.markdown("---")
    st.markdown("## 📈 历史趋势")
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
        fig.add_trace(go.Scatter(x=sorted_dates, y=food_vals, mode='lines+markers', name='摄入'))
        fig.add_trace(go.Scatter(x=sorted_dates, y=exercise_vals, mode='lines+markers', name='消耗'))
        fig.add_trace(go.Scatter(x=sorted_dates, y=net_vals, mode='lines+markers', name='净摄入'))
        fig.update_layout(title="30天热量趋势", height=450)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无数据")
    
    if st.button("关闭", key="close_trend"):
        st.session_state.show_trend = False
        st.rerun()

# ==================== 邮件发送弹窗 ====================
if st.session_state.get('show_email', False) and st.session_state.user_id:
    st.markdown("---")
    st.markdown("## 📧 发送每日报告")
    
    email_address = st.text_input("收件邮箱", value=st.session_state.get('user_email', ''), placeholder="输入邮箱地址", key="report_email")
    
    with st.expander("📋 报告预览"):
        st.write(f"📅 日期: {today}")
        st.write(f"🍽️ 今日摄入: {total_calories:.0f} kcal")
        st.write(f"🏋️ 今日消耗: {total_burned:.0f} kcal")
        st.write(f"📊 净摄入: {total_calories - total_burned:.0f} kcal")
        if foods:
            st.write("**饮食记录:**")
            for f in foods:
                st.write(f"  - {f['meal']}: {f['food_name']} ({f['quantity']}g) - {f['calories']:.0f}kcal")
        if exercises:
            st.write("**运动记录:**")
            for e in exercises:
                st.write(f"  - {e['exercise_name']}: {e['duration']}分钟 - {e['calories']:.0f}kcal")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📧 发送报告", type="primary", use_container_width=True, key="send_report"):
            if email_address:
                with st.spinner("正在发送..."):
                    success, msg = send_daily_report_email(
                        email_address,
                        st.session_state.user_email,
                        foods,
                        exercises,
                        total_calories,
                        total_burned,
                        daily_target
                    )
                    if success:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
            else:
                st.warning("请输入邮箱地址")
    
    with col_btn2:
        if st.button("关闭", use_container_width=True, key="close_email"):
            st.session_state.show_email = False
            st.rerun()
    
    if not is_sendgrid_configured():
        st.info("💡 邮件服务配置中，请联系管理员配置 SendGrid")

st.markdown("---")
st.markdown("<p style='text-align:center;color:gray'>🔍 搜索 | 📸 拍照 | 🏋️ 运动 | ✏️ 自定义 | 💾 数据本地保存 | 🔐 登录后云端同步</p>", unsafe_allow_html=True)
