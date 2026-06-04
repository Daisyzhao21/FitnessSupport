import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="健身食物热量AI助手",
    page_icon="💪",
    layout="wide"
)

# 加载食物数据库
@st.cache_data
def load_food_data():
    df = pd.read_csv('food_nutrition.csv', encoding='utf-8-sig')
    return df

df = load_food_data()

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .result-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.2rem;
        border-radius: 12px;
        margin: 0.5rem 0;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #667eea;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>💪 健身食物热量AI助手</h1>
    <p>智能计算食物热量 | 科学规划每日饮食</p>
</div>
""", unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    st.markdown("### 🎯 今日目标")
    
    # 用户目标设置
    goal = st.selectbox("健身目标", ["减脂", "保持体重", "增肌"])
    
    if goal == "减脂":
        default_cal = 1800
    elif goal == "保持体重":
        default_cal = 2200
    else:
        default_cal = 2600
    
    daily_target = st.number_input("每日热量目标 (kcal)", min_value=1200, max_value=4000, value=default_cal)
    
    st.markdown("---")
    st.markdown("### 📊 今日累计")
    
    # 初始化session state
    if 'total_calories' not in st.session_state:
        st.session_state.total_calories = 0
    if 'total_protein' not in st.session_state:
        st.session_state.total_protein = 0
    if 'food_records' not in st.session_state:
        st.session_state.food_records = []
    
    remaining = daily_target - st.session_state.total_calories
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("已摄入", f"{st.session_state.total_calories:.0f} kcal")
    with col2:
        st.metric("剩余", f"{remaining:.0f} kcal", delta="还可吃" if remaining > 0 else "已超标")
    
    st.progress(min(st.session_state.total_calories / daily_target, 1.0))
    
    if st.button("🗑️ 清空今日记录"):
        st.session_state.total_calories = 0
        st.session_state.total_protein = 0
        st.session_state.food_records = []
        st.rerun()

# 主界面 - 两个Tab
tab1, tab2, tab3 = st.tabs(["🔍 食物查询", "📝 今日记录", "💡 智能推荐"])

# Tab 1: 食物查询
with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🔍 搜索食物")
        
        # 搜索框
        search_term = st.text_input("输入食物名称", placeholder="例如：鸡胸肉、米线、西兰花...")
        
        # 类别筛选
        categories = ["全部"] + sorted(df['类别'].unique().tolist())
        selected_category = st.selectbox("筛选类别", categories)
    
    with col2:
        st.markdown("### ⚙️ 份量设置")
        weight = st.number_input("重量 (克)", min_value=10, max_value=2000, value=100, step=50)
    
    # 搜索结果
    if search_term:
        # 搜索匹配
        filtered = df[df['名称'].str.contains(search_term, na=False)]
        
        if selected_category != "全部":
            filtered = filtered[filtered['类别'] == selected_category]
        
        if len(filtered) > 0:
            st.markdown(f"**找到 {len(filtered)} 种食物：**")
            
            for _, row in filtered.iterrows():
                # 计算实际营养
                calories = row['热量'] * weight / 100
                protein = row['蛋白质'] * weight / 100
                
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])
                with col1:
                    st.markdown(f"**{row['名称']}**")
                    st.caption(row['类别'])
                with col2:
                    st.metric("热量", f"{calories:.0f} kcal")
                with col3:
                    st.metric("蛋白质", f"{protein:.0f} g")
                with col4:
                    st.markdown(f"📊 {row['热量']} kcal/100g")
                with col5:
                    if st.button(f"➕ 添加", key=row['名称']):
                        st.session_state.total_calories += calories
                        st.session_state.total_protein += protein
                        st.session_state.food_records.append({
                            '时间': datetime.now().strftime("%H:%M:%S"),
                            '名称': row['名称'],
                            '重量': weight,
                            '热量': calories,
                            '蛋白质': protein
                        })
                        st.success(f"✅ 已添加 {row['名称']} {weight}g")
                        st.rerun()
        else:
            st.warning("未找到该食物，试试其他关键词")
    else:
        st.info("💡 请输入食物名称开始查询，例如：米线、鸡胸肉、西兰花")

# Tab 2: 今日记录
with tab2:
    st.markdown("### 📝 今日饮食记录")
    
    if len(st.session_state.food_records) > 0:
        records_df = pd.DataFrame(st.session_state.food_records)
        
        # 显示记录表格
        st.dataframe(
            records_df[['时间', '名称', '重量', '热量', '蛋白质']],
            use_container_width=True,
            column_config={
                '热量': st.column_config.NumberColumn("热量 (kcal)", format="%.0f"),
                '蛋白质': st.column_config.NumberColumn("蛋白质 (g)", format="%.0f"),
                '重量': st.column_config.NumberColumn("重量 (g)", format="%.0f"),
            }
        )
        
        # 汇总
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总热量", f"{st.session_state.total_calories:.0f} kcal")
        with col2:
            st.metric("总蛋白质", f"{st.session_state.total_protein:.0f} g")
        with col3:
            protein_ratio = st.session_state.total_protein / (st.session_state.total_calories / 4) * 100 if st.session_state.total_calories > 0 else 0
            st.metric("蛋白质占比", f"{protein_ratio:.0f}%", help="建议占热量20-30%")
    else:
        st.info("📭 还没有记录，去「食物查询」添加吧")

# Tab 3: 智能推荐
with tab3:
    st.markdown("### 💡 智能食物推荐")
    
    remaining_cal = daily_target - st.session_state.total_calories
    remaining_protein = (daily_target * 0.25 / 4) - st.session_state.total_protein  # 按25%蛋白质目标
    
    if remaining_cal > 0:
        st.info(f"📊 剩余热量: {remaining_cal:.0f} kcal | 建议补充蛋白质: {max(0, remaining_protein):.0f} g")
        
        # 根据剩余热量推荐食物
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🥩 高蛋白推荐")
            high_protein = df[df['蛋白质'] > 15].head(5)
            for _, row in high_protein.iterrows():
                calories_100g = row['热量']
                st.markdown(f"**{row['名称']}** - {row['热量']} kcal/100g | 蛋白质 {row['蛋白质']}g/100g")
        
        with col2:
            st.markdown("#### 🥬 低卡推荐")
            low_cal = df[df['热量'] < 50].head(5)
            for _, row in low_cal.iterrows():
                st.markdown(f"**{row['名称']}** - {row['热量']} kcal/100g | 蛋白质 {row['蛋白质']}g/100g")
    else:
        st.warning("⚠️ 今日热量已超标，建议控制饮食或增加运动")
    
    # 营养建议
    st.markdown("---")
    st.markdown("#### 📖 营养小贴士")
    
    if st.session_state.total_protein < daily_target * 0.2 / 4:
        st.markdown("💪 **蛋白质不足**：建议增加鸡胸肉、鸡蛋、鱼、豆腐等高蛋白食物")
    elif st.session_state.total_protein > daily_target * 0.35 / 4:
        st.markdown("⚠️ **蛋白质偏高**：适量即可，过量会增加肾脏负担")
    else:
        st.markdown("✅ **蛋白质摄入良好**，继续保持！")

# 页脚
st.markdown("---")
st.markdown("<p style='text-align:center;color:gray'>💪 科学健身 | 合理饮食 | 健康生活</p>", unsafe_allow_html=True)
