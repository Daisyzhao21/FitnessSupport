import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image
import uuid

from image_recognition import FoodImageRecognizer

st.set_page_config(page_title="健身营养助手", page_icon="💪", layout="wide")

# 加载数据
@st.cache_data
def load_food_data():
    return pd.read_csv('food_nutrition.csv', encoding='utf-8-sig')

@st.cache_data
def load_exercise_data():
    return pd.read_csv('exercise_database.csv', encoding='utf-8-sig')

df_food = load_food_data()
df_exercise = load_exercise_data()

def get_recognizer():
    api_key = os.environ.get("QWEN_API_KEY")
    if hasattr(st, 'secrets') and 'QWEN_API_KEY' in st.secrets:
        api_key = st.secrets['QWEN_API_KEY']
    return FoodImageRecognizer(api_type="qwen", api_key=api_key) if api_key else None

# 初始化 Session State
for key, default in [
    ('user_profile', {'gender': '男', 'weight': 70, 'height': 170, 'age': 25, 'activity_level': '中等', 'goal': '减脂'}),
    ('food_records', []), ('exercise_records', []), ('total_calories', 0), ('total_protein', 0), ('total_burned', 0),
    ('search_results', None), ('search_weight', 100), ('search_term', ""), ('exercise_search_term', ""),
    ('custom_exercise_name', ""), ('custom_coefficient', 0.08), ('bmr', 1600), ('daily_target', 2000)
]:
    if key not in st.session_state:
        st.session_state[key] = default

def calculate_bmr():
    p = st.session_state.user_profile
    bmr = (66 + 13.7*p['weight'] + 5*p['height'] - 6.8*p['age']) if p['gender']=='男' else (655 + 9.6*p['weight'] + 1.8*p['height'] - 4.7*p['age'])
    factors = {'低':1.2, '中等':1.375, '高':1.55, '非常高':1.725}
    tdee = bmr * factors[p['activity_level']]
    adj = -300 if p['goal']=='减脂' else (300 if p['goal']=='增肌' else 0)
    st.session_state.bmr, st.session_state.daily_target = int(bmr), int(tdee + adj)

calculate_bmr()

st.markdown("""
<style>.main-header{background:linear-gradient(135deg,#667eea,#764ba2);padding:1rem;border-radius:15px;margin-bottom:1rem;text-align:center;color:white;}
@media (max-width:768px){.stButton button{width:100%;}}</style>
<div class="main-header"><h1>💪 健身营养助手</h1><p>📸 拍照识别 | 🏋️ 90+种运动 | 📊 摄入 vs 消耗</p></div>
""", unsafe_allow_html=True)

col_left, col_mid, col_right = st.columns([1, 1.5, 1.3])

# 左侧：个人信息
with col_left:
    st.markdown("### 👤 个人信息")
    st.info(f"👋 {st.session_state.user_profile['height']}cm / {st.session_state.user_profile['weight']}kg / {st.session_state.user_profile['goal']}")
    with st.expander("✏️ 编辑"):
        g = st.selectbox("性别",["男","女"],0 if st.session_state.user_profile['gender']=='男' else 1)
        a = st.number_input("年龄",15,100,st.session_state.user_profile['age'])
        h = st.number_input("身高(cm)",100,250,st.session_state.user_profile['height'])
        w = st.number_input("体重(kg)",30,200,st.session_state.user_profile['weight'])
        act = st.selectbox("活动水平",["低","中等","高","非常高"],index=["低","中等","高","非常高"].index(st.session_state.user_profile['activity_level']))
        goal = st.selectbox("目标",["减脂","保持体重","增肌"],index=["减脂","保持体重","增肌"].index(st.session_state.user_profile['goal']))
        if st.button("💾 保存"):
            st.session_state.user_profile = {'gender':g,'age':a,'height':h,'weight':w,'activity_level':act,'goal':goal}
            calculate_bmr()
            st.rerun()
    
    net = st.session_state.total_calories - st.session_state.total_burned
    remaining = st.session_state.daily_target - net
    st.metric("基础代谢",f"{st.session_state.bmr} kcal")
    st.metric("每日目标",f"{st.session_state.daily_target} kcal")
    col_a,col_b = st.columns(2)
    col_a.metric("🍽️ 摄入",f"{st.session_state.total_calories:.0f} kcal")
    col_b.metric("🏋️ 消耗",f"{st.session_state.total_burned:.0f} kcal")
    if remaining>0:
        st.success(f"✅ 剩余: {remaining:.0f} kcal")
        st.progress(min(max((st.session_state.daily_target-remaining)/st.session_state.daily_target,0),1))
    else:
        st.error(f"⚠️ 超标: {-remaining:.0f} kcal")
        st.progress(1.0)
    if st.button("🗑️ 清空记录"):
        st.session_state.food_records, st.session_state.exercise_records = [], []
        st.session_state.total_calories = st.session_state.total_protein = st.session_state.total_burned = 0
        st.rerun()

# 中间：食物摄入
with col_mid:
    st.markdown("## 🍽️ 食物摄入")
    mode = st.radio("方式",["🔍 手动","📸 拍照"],horizontal=True)
    meal = st.selectbox("餐次",["早餐","午餐","晚餐","加餐"])
    
    if mode == "🔍 手动":
        s1,s2 = st.columns([3,1])
        with s1: term = st.text_input("搜索", key="food_search", value=st.session_state.search_term)
        with s2: wt = st.number_input("重量(g)",10,1000,st.session_state.search_weight,50, key="food_wt")
        if term:
            st.session_state.search_term, st.session_state.search_weight = term, wt
            results = df_food[df_food['名称'].str.contains(term, na=False)].head(8)
            for _,row in results.iterrows():
                cal, pro = row['热量']*wt/100, row['蛋白质']*wt/100
                c1,c2,c3,c4 = st.columns([2,1,1,1])
                c1.markdown(f"**{row['名称']}**"); c1.caption(row['类别'])
                c2.write(f"{cal:.0f} kcal"); c3.write(f"蛋白质 {pro:.0f}g")
                if c4.button("➕", key=f"add_{row['名称']}"):
                    st.session_state.food_records.append({'时间':datetime.now().strftime("%H:%M"),'餐次':meal,'名称':row['名称'],'重量':wt,'热量':cal,'蛋白质':pro})
                    st.session_state.total_calories += cal; st.session_state.total_protein += pro
                    st.rerun()
    else:
        rec = get_recognizer()
        if rec:
            img = st.camera_input("拍照") or st.file_uploader("图片",type=['jpg','png'])
            if img and st.button("识别"):
                img = Image.open(img)
                img.save("/tmp/food.jpg")
                res = rec.recognize_food("/tmp/food.jpg")
                if not res.get("error"):
                    for f in res.get("foods",[]):
                        name, w2, cal, pro = f.get('name','未知'), f.get('weight',150), f.get('calories',225), f.get('protein',15)
                        if st.button(f"➕ 添加 {name}"):
                            st.session_state.food_records.append({'时间':datetime.now().strftime("%H:%M"),'餐次':meal,'名称':name,'重量':w2,'热量':cal,'蛋白质':pro})
                            st.session_state.total_calories += cal; st.session_state.total_protein += pro
                            st.rerun()
    
    st.markdown("### 📋 今日饮食")
    if st.session_state.food_records:
        for m in ["早餐","午餐","晚餐","加餐"]:
            items = [r for r in st.session_state.food_records if r['餐次']==m]
            if items:
                st.markdown(f"**{m}**")
                for r in items: st.write(f"  🕐 {r['时间']} | {r['名称']} | {r['重量']}g | {r['热量']:.0f}kcal | 蛋白质 {r['蛋白质']:.0f}g")
    else: st.info("暂无")

# 右侧：运动消耗
with col_right:
    st.markdown("## 🏋️ 运动消耗")
    mode_ex = st.radio("方式",["🔍 搜索","✏️ 自定义","📸 拍照"],horizontal=True)
    
    if mode_ex == "🔍 搜索":
        search = st.text_input("🔍 搜索运动", placeholder="深蹲、硬拉、俯卧撑、史密斯...", key="ex_search")
        filtered = df_exercise if not search else df_exercise[df_exercise['器材'].str.contains(search, na=False)]
        if len(filtered)==0:
            st.warning(f"未找到 '{search}'，试试其他词或使用「自定义」")
            filtered = df_exercise
        ex_name = st.selectbox("选择运动", filtered['器材'].tolist())
        ex = df_exercise[df_exercise['器材']==ex_name].iloc[0]
        st.caption(f"💡 {ex['说明']} | {ex['消耗系数']} kcal/kg/分钟")
        dur = st.number_input("分钟",1,180,30,5)
        extra = st.number_input("负重(kg)",0,100,0,5)
        cal = ex['消耗系数'] * (st.session_state.user_profile['weight'] + extra) * dur
        st.info(f"🔥 消耗: **{cal:.0f} kcal**")
        if st.button("✅ 记录"):
            st.session_state.exercise_records.append({'时间':datetime.now().strftime("%H:%M"),'器材':ex_name,'时长':dur,'负重':extra,'消耗':cal})
            st.session_state.total_burned += cal
            st.rerun()
    
    elif mode_ex == "✏️ 自定义":
        name = st.text_input("运动名称", placeholder="保加利亚深蹲、史密斯深蹲...")
        coeff = st.number_input("消耗系数",0.01,0.50,0.08,0.01, help="参考: 深蹲0.08, 硬拉0.10, 跑步0.12")
        dur = st.number_input("分钟",1,180,30,5, key="c_dur")
        extra = st.number_input("负重(kg)",0,100,0,5, key="c_extra")
        if name:
            cal = coeff * (st.session_state.user_profile['weight'] + extra) * dur
            st.info(f"🔥 {name} 消耗: **{cal:.0f} kcal**")
            if st.button("✅ 记录自定义"):
                st.session_state.exercise_records.append({'时间':datetime.now().strftime("%H:%M"),'器材':name,'时长':dur,'负重':extra,'消耗':cal})
                st.session_state.total_burned += cal
                st.rerun()
    
    else:
        rec = get_recognizer()
        if rec:
            img = st.camera_input("拍照", key="ex_cam") or st.file_uploader("图片",type=['jpg','png'], key="ex_up")
            if img and st.button("识别器材"):
                img = Image.open(img)
                img.save("/tmp/ex.jpg")
                res = rec.recognize_food("/tmp/ex.jpg")
                if not res.get("error"):
                    name = res.get("foods",[{}])[0].get('name','未知')
                    st.write(f"识别到: {name}")
                    dur = st.number_input("分钟",1,180,30,5, key="r_dur")
                    extra = st.number_input("负重",0,100,0,5, key="r_extra")
                    if st.button("记录"):
                        cal = 0.08 * (st.session_state.user_profile['weight'] + extra) * dur
                        st.session_state.exercise_records.append({'时间':datetime.now().strftime("%H:%M"),'器材':name,'时长':dur,'负重':extra,'消耗':cal})
                        st.session_state.total_burned += cal
                        st.rerun()
    
    st.markdown("### 📋 今日运动")
    if st.session_state.exercise_records:
        total_min = sum(r['时长'] for r in st.session_state.exercise_records)
        st.metric("总时长", f"{total_min} 分钟")
        for r in st.session_state.exercise_records[-15:]:
            st.write(f"  🕐 {r['时间']} | {r['器材']} | {r['时长']}分钟 | 🔥 {r['消耗']:.0f}kcal")
    else: st.info("暂无")

st.markdown("---")
st.markdown("<p style='text-align:center;color:gray'>🔍 搜索90+种运动 | ✏️ 自定义 | 📸 拍照识别</p>", unsafe_allow_html=True)
