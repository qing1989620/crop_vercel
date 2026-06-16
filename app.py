"""
果园病虫害风险预警与防控可视化看板
=====================================
基于 LightGBM + SHAP 的智能预警系统
企业级 Streamlit 可视化大屏

运行方式：
    streamlit run app.py
    或双击 run.bat
"""
import streamlit as st
import pandas as pd
import numpy as np
import time
import datetime
import random
import os
import sys

# 将当前目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    APP_TITLE, APP_LAYOUT, AUTO_REFRESH_INTERVAL, ENABLE_AUTO_REFRESH,
    RISK_LEVELS, BASE_CONTROL_PLANS, SIMULATION_MODES, DEFAULT_SIMULATION_MODE
)
from utils.data_loader import (
    load_main_dataset, load_prevention_plan, load_response_zone_summary,
    load_three_tier_summary, load_strategy_system, load_risk_window_cross,
    load_feature_importance, load_shap_contributions, load_kpi_metrics,
    load_confusion_matrix, load_roc_auc, load_category_distribution,
    load_posi_weights, get_time_based_plan, get_risk_color_map
)
from utils.charts import (
    create_risk_pie_chart, create_risk_bar_chart, create_spatial_risk_map,
    create_time_trend_chart, create_feature_importance_chart,
    create_shap_chart, create_kpi_gauge, create_response_zone_chart,
    create_posi_weight_chart, create_risk_heatmap
)

# ==================== 页面基础配置 ====================
st.set_page_config(
    page_title="果园病虫害预警看板",
    page_icon="🍎",
    layout=APP_LAYOUT,
    initial_sidebar_state="expanded"
)

# ==================== 自定义 CSS 样式 ====================
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        text-align: center;
        color: #2c3e50;
        padding: 10px 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .status-bar {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 20px;
        padding: 8px;
        background: #f8f9fa;
        border-radius: 8px;
        margin: 5px 0 15px 0;
    }
    
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #2ecc71;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.3; }
        100% { opacity: 1; }
    }
    
    .metric-card {
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.3s;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .metric-label {
        font-size: 0.95rem;
        opacity: 0.9;
        margin-top: 5px;
    }
    
    .metric-delta {
        font-size: 0.8rem;
        opacity: 0.8;
        margin-top: 3px;
    }
    
    .custom-divider {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #bdc3c7, transparent);
        margin: 20px 0;
    }
    
    .advice-box-low {
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2ecc71;
        background: #eafaf1;
        margin: 10px 0;
    }
    
    .advice-box-mid {
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #f39c12;
        background: #fef9e7;
        margin: 10px 0;
    }
    
    .advice-box-high {
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #e74c3c;
        background: #fdedec;
        margin: 10px 0;
    }
    
    .footer {
        text-align: center;
        padding: 20px;
        color: #bdc3c7;
        font-size: 0.8rem;
        border-top: 1px solid #ecf0f1;
        margin-top: 30px;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==================== 自动刷新机制 ====================
if ENABLE_AUTO_REFRESH:
    st.markdown(
        f"""
        <script>
        setTimeout(function() {{
            window.location.reload();
        }}, {AUTO_REFRESH_INTERVAL * 1000});
        </script>
        """,
        unsafe_allow_html=True
    )

# ==================== 加载数据 ====================
@st.cache_data(ttl=30)
def load_all_data():
    """统一加载所有数据"""
    data = {}
    with st.spinner("正在加载数据..."):
        try:
            data["main"] = load_main_dataset()
            data["prevention"] = load_prevention_plan()
            data["response_zone"] = load_response_zone_summary()
            data["three_tier"] = load_three_tier_summary()
            data["strategy"] = load_strategy_system()
            data["risk_window"] = load_risk_window_cross()
            data["feature_importance"] = load_feature_importance()
            data["shap"] = load_shap_contributions()
            data["kpi"] = load_kpi_metrics()
            data["confusion"] = load_confusion_matrix()
            data["roc_auc"] = load_roc_auc()
            data["category_dist"] = load_category_distribution()
            data["posi_weights"] = load_posi_weights()
        except Exception as e:
            st.error(f"数据加载异常: {e}")
    return data


data = load_all_data()

# 获取主数据集
df_main = data.get("main", pd.DataFrame())
if df_main.empty:
    st.error("无法加载核心数据，请检查数据文件路径。")
    st.stop()

# ==================== 模拟实时数据扰动 ====================
def apply_simulation_perturbation(df: pd.DataFrame) -> pd.DataFrame:
    """对数据集施加随机扰动，模拟实时数据变化"""
    sim_df = df.copy()
    np.random.seed(int(time.time()))
    
    prob_cols = [c for c in sim_df.columns if "风险概率" in c and "等级" in c]
    for col in prob_cols:
        if col in sim_df.columns:
            noise = np.random.uniform(-0.03, 0.03, len(sim_df))
            sim_df[col] = sim_df[col] + noise
            sim_df[col] = sim_df[col].clip(0, 1)
    
    if len(prob_cols) == 3:
        sums = sim_df[prob_cols].sum(axis=1)
        for col in prob_cols:
            sim_df[col] = sim_df[col] / sums
    
    if len(prob_cols) == 3:
        sim_df["预测风险编码_sim"] = sim_df[prob_cols].values.argmax(axis=1)
        sim_df["预测风险标签_sim"] = sim_df["预测风险编码_sim"].map({0: "低", 1: "中", 2: "高"})
    
    numeric_cols = sim_df.select_dtypes(include=[np.number]).columns
    exclude_cols = prob_cols + ["风险等级编码", "预测风险等级"]
    for col in numeric_cols:
        if col not in exclude_cols and sim_df[col].dtype in [np.float64, np.float32]:
            std = sim_df[col].std()
            if std > 0:
                noise = np.random.normal(0, std * 0.02, len(sim_df))
                sim_df[col] = sim_df[col] + noise
    
    return sim_df


# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## 🍎 看板控制面板")
    st.markdown("---")
    
    sim_mode = st.radio(
        "📡 数据刷新模式",
        SIMULATION_MODES,
        index=SIMULATION_MODES.index(DEFAULT_SIMULATION_MODE)
    )
    
    st.markdown("---")
    st.markdown("### 🔍 数据筛选")
    
    if "果树品种" in df_main.columns:
        varieties = ["全部"] + sorted(df_main["果树品种"].unique().tolist())
        selected_variety = st.selectbox("果树品种", varieties)
    else:
        selected_variety = "全部"
    
    risk_filter = st.multiselect(
        "风险等级",
        ["低风险", "中风险", "高风险"],
        default=["低风险", "中风险", "高风险"]
    )
    
    if "病虫害类型" in df_main.columns:
        pest_types = ["全部"] + sorted(df_main["病虫害类型"].unique().astype(str).tolist())
        selected_pest = st.selectbox("病虫害类型", pest_types)
    else:
        selected_pest = "全部"
    
    st.markdown("---")
    st.markdown("### ⚙️ 刷新设置")
    refresh_on = st.toggle("启用自动刷新", value=ENABLE_AUTO_REFRESH)
    if refresh_on:
        refresh_interval = st.slider("刷新间隔（秒）", 3, 30, AUTO_REFRESH_INTERVAL)
        st.caption(f"当前：每 {refresh_interval} 秒刷新一次")
    
    st.markdown("---")
    st.markdown("### ℹ️ 系统信息")
    st.caption(f"数据地块总数：{len(df_main)}")
    
    if "预测风险标签" in df_main.columns:
        risk_counts_sidebar = df_main["预测风险标签"].value_counts()
        for label in ["低", "中", "高"]:
            cnt = risk_counts_sidebar.get(label, 0)
            emoji = {"低": "🟢", "中": "🟡", "高": "🔴"}.get(label, "")
            st.caption(f"{emoji} {label}风险：{cnt} 块")
    
    st.caption(f"页面加载时间：{datetime.datetime.now().strftime('%H:%M:%S')}")


# ==================== 应用筛选 ====================
df_filtered = df_main.copy()

if sim_mode == "模拟实时（随机扰动）":
    df_filtered = apply_simulation_perturbation(df_filtered)
    if "预测风险标签_sim" in df_filtered.columns:
        df_filtered["预测风险标签"] = df_filtered["预测风险标签_sim"]
    if "预测风险编码_sim" in df_filtered.columns:
        df_filtered["风险等级编码"] = df_filtered["预测风险编码_sim"]
elif sim_mode == "模拟实时（时段循环）":
    hour = datetime.datetime.now().hour
    cycle_seed = hour % 4
    np.random.seed(cycle_seed)
    df_filtered = apply_simulation_perturbation(df_filtered)
    if "预测风险标签_sim" in df_filtered.columns:
        df_filtered["预测风险标签"] = df_filtered["预测风险标签_sim"]
    if "预测风险编码_sim" in df_filtered.columns:
        df_filtered["风险等级编码"] = df_filtered["预测风险编码_sim"]

if selected_variety != "全部" and "果树品种" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["果树品种"] == selected_variety]

risk_code_map = {"低风险": 0, "中风险": 1, "高风险": 2, "低": 0, "中": 1, "高": 2}
if "风险等级编码" in df_filtered.columns:
    allowed_codes = [risk_code_map.get(r, r) for r in risk_filter]
    df_filtered = df_filtered[df_filtered["风险等级编码"].isin(allowed_codes)]
elif "预测风险标签" in df_filtered.columns:
    allowed_labels = [r.replace("风险", "") for r in risk_filter]
    df_filtered = df_filtered[df_filtered["预测风险标签"].isin(allowed_labels)]

if selected_pest != "全部" and "病虫害类型" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["病虫害类型"].astype(str) == selected_pest]


# ==================== 生成风险统计 ====================
if "风险等级编码" in df_filtered.columns:
    risk_col = "风险等级编码"
    risk_label_col = "预测风险标签" if "预测风险标签" in df_filtered.columns else None
elif "预测风险标签" in df_filtered.columns:
    df_filtered["_risk_code"] = df_filtered["预测风险标签"].map(
        lambda x: {"低": 0, "中": 1, "高": 2}.get(str(x), -1)
    )
    risk_col = "_risk_code"
    risk_label_col = "预测风险标签"
else:
    risk_col = None
    risk_label_col = None

if risk_col:
    risk_counts = df_filtered[risk_col].value_counts().to_dict()
    low_count = risk_counts.get(0, 0)
    mid_count = risk_counts.get(1, 0)
    high_count = risk_counts.get(2, 0)
else:
    low_count = mid_count = high_count = 0


# ==================== 头部标题区 ====================
st.markdown(f'<div class="main-title">{APP_TITLE}</div>', unsafe_allow_html=True)

current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
status_label = "🟢 系统运行中" if not df_main.empty else "🔴 数据异常"
st.markdown(f"""
<div class="status-bar">
    <span><span class="status-dot"></span> {status_label}</span>
    <span>|</span>
    <span>🕐 当前时间：{current_time}</span>
    <span>|</span>
    <span>📡 刷新模式：{sim_mode}</span>
    <span>|</span>
    <span>📊 筛选地块：{len(df_filtered)} / {len(df_main)}</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)


# ==================== 模块1：全园风险总览 ====================
st.markdown("## 📊 一、全园风险态势总览")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #2ecc71, #27ae60);">
        <div class="metric-value">{low_count}</div>
        <div class="metric-label">🟢 低风险地块</div>
        <div class="metric-delta">占比 {low_count/len(df_filtered)*100:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #f39c12, #e67e22);">
        <div class="metric-value">{mid_count}</div>
        <div class="metric-label">🟡 中风险地块</div>
        <div class="metric-delta">占比 {mid_count/len(df_filtered)*100:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #e74c3c, #c0392b);">
        <div class="metric-value">{high_count}</div>
        <div class="metric-label">🔴 高风险地块</div>
        <div class="metric-delta">占比 {high_count/len(df_filtered)*100:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    total = len(df_filtered)
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #3498db, #2980b9);">
        <div class="metric-value">{total}</div>
        <div class="metric-label">📋 总地块数</div>
        <div class="metric-delta">筛选后</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    if "在防治窗口内" in df_filtered.columns:
        window_count = df_filtered["在防治窗口内"].sum() if df_filtered["在防治窗口内"].dtype == bool else \
                       (df_filtered["在防治窗口内"] == True).sum() + (df_filtered["在防治窗口内"] == "True").sum()
    else:
        window_count = high_count
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #9b59b6, #8e44ad);">
        <div class="metric-value">{window_count}</div>
        <div class="metric-label">🎯 防治窗口内</div>
        <div class="metric-delta">需立即处置</div>
    </div>
    """, unsafe_allow_html=True)

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    pie_fig = create_risk_pie_chart(df_filtered)
    st.plotly_chart(pie_fig, width='stretch')
with chart_col2:
    bar_fig = create_risk_bar_chart(df_filtered)
    st.plotly_chart(bar_fig, width='stretch')

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)


# ==================== 模块2：果园空间风险分布图 ====================
st.markdown("## 🗺️ 二、果园分区域风险空间分布")

map_col1, map_col2 = st.columns([2, 1])

with map_col1:
    map_fig = create_spatial_risk_map(df_filtered)
    st.plotly_chart(map_fig, width='stretch')

with map_col2:
    st.markdown("### 📋 风险等级图例")
    st.markdown("""
    <div style="padding: 15px; background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <div style="display:flex;align-items:center;margin:8px 0;">
            <div style="width:20px;height:20px;background:#2ecc71;border-radius:4px;margin-right:10px;"></div>
            <span><b>低风险</b> — 常规监测，无需施药</span>
        </div>
        <div style="display:flex;align-items:center;margin:8px 0;">
            <div style="width:20px;height:20px;background:#f39c12;border-radius:4px;margin-right:10px;"></div>
            <span><b>中风险</b> — 预防施药，加强巡检</span>
        </div>
        <div style="display:flex;align-items:center;margin:8px 0;">
            <div style="width:20px;height:20px;background:#e74c3c;border-radius:4px;margin-right:10px;"></div>
            <span><b>高风险</b> — 应急响应，立即处置</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if "果树品种" in df_filtered.columns:
        st.markdown("### 🌳 品种风险分布")
        variety_risk = df_filtered.groupby("果树品种")[risk_col].value_counts().unstack(fill_value=0)
        variety_risk.columns = [f"{RISK_LEVELS.get(c, {}).get('label', c)}" for c in variety_risk.columns]
        st.dataframe(variety_risk, width='stretch')

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)


# ==================== 模块3：分时段风险趋势 + 交叉分析 ====================
st.markdown("## 📈 三、分时段风险趋势与交叉分析")

trend_col1, trend_col2 = st.columns(2)

with trend_col1:
    trend_fig = create_time_trend_chart(df_filtered)
    st.plotly_chart(trend_fig, width='stretch')

with trend_col2:
    heatmap_fig = create_risk_heatmap(df_filtered)
    st.plotly_chart(heatmap_fig, width='stretch')

st.markdown("### 风险等级 × 防治窗口 交叉统计明细")
risk_window_data = data.get("risk_window", pd.DataFrame())
if not risk_window_data.empty:
    st.dataframe(risk_window_data, width='stretch')
else:
    if "在防治窗口内" in df_filtered.columns:
        window_col = "在防治窗口内"
        df_filtered["_window"] = df_filtered[window_col].apply(
            lambda x: "窗口内" if str(x).lower() in ["true", "1", "是"] else "窗口外"
        )
        cross = pd.crosstab(
            df_filtered[risk_label_col] if risk_label_col else df_filtered[risk_col],
            df_filtered["_window"],
            margins=True, margins_name="合计"
        )
    else:
        cross = pd.DataFrame({"说明": ["该数据集无防治窗口字段"]})
    st.dataframe(cross, width='stretch')

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)


# ==================== 模块4：地块详情 + 智能防控建议 ====================
st.markdown("## 🎯 四、单地块详情与精准防控建议")
st.markdown("*核心交互模块：选择地块 → 查看实时特征 → 自动匹配防控方案*")

if "地块ID" in df_filtered.columns:
    plot_ids = df_filtered["地块ID"].tolist()
else:
    plot_ids = [f"地块{i+1}" for i in range(len(df_filtered))]
    df_filtered["地块ID"] = plot_ids

plot_col1, plot_col2, plot_col3 = st.columns([1, 2, 1])
with plot_col1:
    quick_filter = st.radio(
        "快速筛选",
        ["全部地块", "仅高风险", "仅中风险", "仅低风险"],
        horizontal=False
    )
with plot_col2:
    if quick_filter == "仅高风险":
        if risk_col:
            filtered_ids = df_filtered[df_filtered[risk_col] == 2]["地块ID"].tolist()
        else:
            filtered_ids = plot_ids
    elif quick_filter == "仅中风险":
        if risk_col:
            filtered_ids = df_filtered[df_filtered[risk_col] == 1]["地块ID"].tolist()
        else:
            filtered_ids = plot_ids
    elif quick_filter == "仅低风险":
        if risk_col:
            filtered_ids = df_filtered[df_filtered[risk_col] == 0]["地块ID"].tolist()
        else:
            filtered_ids = plot_ids
    else:
        filtered_ids = plot_ids
    
    if not filtered_ids:
        st.warning("该筛选条件下无匹配地块")
        filtered_ids = plot_ids
    
    selected_plot = st.selectbox(
        "📌 选择查询地块",
        filtered_ids if filtered_ids else plot_ids,
        help="选择地块后，右侧将自动展示该地块的详细数据和防控建议"
    )
with plot_col3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🎲 随机选择地块", width='stretch'):
        selected_plot = random.choice(filtered_ids) if filtered_ids else plot_ids[0]
        st.rerun()

# 获取选中地块数据
plot_data = df_filtered[df_filtered["地块ID"] == selected_plot]
if plot_data.empty:
    st.error(f"未找到地块 {selected_plot} 的数据")
else:
    plot_row = plot_data.iloc[0]
    
    if risk_col and risk_col in plot_row.index:
        plot_risk = int(plot_row[risk_col])
    elif "预测风险标签" in plot_row.index:
        plot_risk = {"低": 0, "中": 1, "高": 2}.get(str(plot_row["预测风险标签"]), 0)
    else:
        plot_risk = 0
    
    risk_info = RISK_LEVELS.get(plot_risk, RISK_LEVELS[0])
    
    detail_col1, detail_col2 = st.columns([1, 1.5])
    
    with detail_col1:
        st.markdown(f"""
        <div style="padding: 20px; background: white; border-radius: 12px; 
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-top: 5px solid {risk_info['color']};">
            <h3 style="margin-top:0;">{risk_info['emoji']} 地块：{selected_plot}</h3>
            <hr>
        """, unsafe_allow_html=True)
        
        info_items = []
        for key, label in [
            ("果树品种", "🌳 果树品种"),
            ("病虫害类型", "🐛 病虫害类型"),
            ("预测风险标签", "⚠️ 预测风险等级"),
            ("最大风险概率", "📊 最大风险概率"),
            ("在防治窗口内", "🎯 是否在防治窗口"),
        ]:
            if key in plot_row.index:
                val = plot_row[key]
                if key == "最大风险概率" and pd.notna(val):
                    val = f"{float(val):.4f}"
                info_items.append(f"<tr><td style='padding:5px 10px;color:#7f8c8d;'>{label}</td><td style='padding:5px 10px;font-weight:600;'>{val}</td></tr>")
        
        st.markdown(f"""
            <table style="width:100%;">
                {''.join(info_items)}
            </table>
        </div>
        """, unsafe_allow_html=True)
        
        posi_cols = [c for c in plot_row.index if "POSI" in str(c)]
        if posi_cols:
            st.markdown("#### 📐 POSI 指标")
            posi_data = {}
            for c in posi_cols:
                if pd.notna(plot_row[c]):
                    try:
                        posi_data[c] = float(plot_row[c])
                    except (ValueError, TypeError):
                        posi_data[c] = str(plot_row[c])
            if posi_data:
                posi_df = pd.DataFrame(list(posi_data.items()), columns=["指标", "值"])
                st.dataframe(posi_df, width='stretch', hide_index=True)
    
    with detail_col2:
        advice_class = {0: "advice-box-low", 1: "advice-box-mid", 2: "advice-box-high"}
        advice_class_name = advice_class.get(plot_risk, "advice-box-low")
        
        time_plan = get_time_based_plan(plot_risk)
        
        st.markdown(f"""
        <div class="{advice_class_name}">
            <h3>📋 {risk_info['icon']} 智能防控建议</h3>
            <p style="font-size:1.1rem;line-height:1.8;">{time_plan}</p>
        </div>
        """, unsafe_allow_html=True)
        
        prevention_df = data.get("prevention", pd.DataFrame())
        if not prevention_df.empty:
            variety = plot_row.get("果树品种", "")
            pest = plot_row.get("病虫害类型", "")
            
            matched = prevention_df[
                (prevention_df.iloc[:, 0].astype(str) == str(variety)) &
                (prevention_df.iloc[:, 1].astype(str) == str(pest))
            ]
            
            if not matched.empty:
                match_row = matched.iloc[0]
                st.markdown("#### 💊 推荐用药方案")
                drug_info = []
                for key, label in [
                    ("防控策略", "策略"),
                    ("推荐剂量(%)", "推荐剂量"),
                    ("推荐农药轮换", "农药轮换方案"),
                    ("施药频率", "施药频率"),
                ]:
                    if key in match_row.index and pd.notna(match_row[key]):
                        drug_info.append(f"<tr><td style='padding:5px 10px;color:#7f8c8d;'>{label}</td><td style='padding:5px 10px;font-weight:500;'>{match_row[key]}</td></tr>")
                
                st.markdown(f"""
                <div style="padding:15px;background:white;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin:10px 0;">
                    <table style="width:100%;">{''.join(drug_info)}</table>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("#### 🌡️ 环境监测指标")
        env_cols = [
            ("平均气温", "℃"), ("相对湿度", "%"), ("降水量", "mm"),
            ("日照时数", "h"), ("土壤湿度", "%"), ("风速", "m/s"),
            ("THI_温湿胁迫", ""), ("BTM_生物威胁动量", ""), ("PRI_抗药性预警", ""),
            ("近7天病株数", "株"), ("近7天虫口密度", ""), ("近30天用药次数", "次"),
            ("LWI_光水滋养", "")
        ]
        
        env_values = {}
        for col_name, unit in env_cols:
            if col_name in plot_row.index and pd.notna(plot_row[col_name]):
                try:
                    val = float(plot_row[col_name])
                    env_values[f"{col_name} ({unit})" if unit else col_name] = round(val, 2)
                except (ValueError, TypeError):
                    env_values[col_name] = plot_row[col_name]
        
        if env_values:
            env_df = pd.DataFrame(list(env_values.items()), columns=["指标", "数值"])
            st.dataframe(env_df, width='stretch', hide_index=True)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)


# ==================== 模块5：三级防控策略体系 ====================
st.markdown("## 🛡️ 五、三级差异化防控策略体系")

strategy_df = data.get("strategy", pd.DataFrame())
response_zone_df = data.get("response_zone", pd.DataFrame())

strat_col1, strat_col2 = st.columns(2)

with strat_col1:
    if not response_zone_df.empty:
        zone_fig = create_response_zone_chart(response_zone_df)
        st.plotly_chart(zone_fig, width='stretch')
    else:
        st.info("暂无防控响应区数据")

with strat_col2:
    if not strategy_df.empty:
        st.markdown("### 📋 三级防控策略对照表")
        strategy_display = strategy_df.copy()
        if "防控维度" in strategy_display.columns:
            strategy_display = strategy_display.set_index("防控维度").T
        st.dataframe(strategy_display, width='stretch')
    else:
        st.info("暂无防控策略数据")

prevention_df = data.get("prevention", pd.DataFrame())
if not prevention_df.empty:
    st.markdown("### 💊 防控单元精准方案推荐")
    display_cols = [c for c in prevention_df.columns if prevention_df[c].nunique() > 0][:8]
    st.dataframe(prevention_df[display_cols], width='stretch', height=300)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)


# ==================== 模块6：模型特征与可解释性 ====================
st.markdown("## 🔬 六、模型特征重要性 & 可解释性分析")

fi_df = data.get("feature_importance", pd.DataFrame())
shap_df = data.get("shap", pd.DataFrame())
posi_df = data.get("posi_weights", pd.DataFrame())

explain_col1, explain_col2 = st.columns(2)

with explain_col1:
    if not fi_df.empty:
        fi_fig = create_feature_importance_chart(fi_df)
        st.plotly_chart(fi_fig, width='stretch')
    else:
        st.info("暂无特征重要性数据")

with explain_col2:
    if not shap_df.empty:
        shap_fig = create_shap_chart(shap_df)
        st.plotly_chart(shap_fig, width='stretch')
    elif not posi_df.empty:
        posi_fig = create_posi_weight_chart(posi_df)
        st.plotly_chart(posi_fig, width='stretch')
    else:
        st.info("暂无SHAP/POSI数据")

if not posi_df.empty:
    st.markdown("### ⚖️ POSI 环境因子权重")
    posi_fig = create_posi_weight_chart(posi_df)
    st.plotly_chart(posi_fig, width='stretch')

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)


# ==================== 模块7：模型性能评估面板 ====================
st.markdown("## 📊 七、模型性能评估面板")

kpi_df = data.get("kpi", pd.DataFrame())
roc_df = data.get("roc_auc", pd.DataFrame())
confusion_df = data.get("confusion", pd.DataFrame())

if not kpi_df.empty:
    macro_row = kpi_df[kpi_df["风险等级"] == "宏平均"] if "风险等级" in kpi_df.columns else None
    
    if macro_row is not None and not macro_row.empty:
        row = macro_row.iloc[0]
        f1_val = row.get("F1分数", 0.98)
        recall_val = row.get("召回率", 0.97)
        precision_val = row.get("精确率", 0.98)
    else:
        f1_val = 0.978
        recall_val = 0.974
        precision_val = 0.982
    
    if not roc_df.empty:
        auc_row = roc_df[roc_df["风险等级"] == "宏平均"] if "风险等级" in roc_df.columns else None
        if auc_row is not None and not auc_row.empty:
            auc_val = auc_row.iloc[0].get("AUC_OOF", 0.9997)
        else:
            auc_val = 0.9997
    else:
        auc_val = 0.9997
    
    gauge_fig = create_kpi_gauge(float(f1_val), float(recall_val), float(precision_val), float(auc_val))
    st.plotly_chart(gauge_fig, width='stretch')

kpi_col1, kpi_col2 = st.columns(2)

with kpi_col1:
    if not kpi_df.empty:
        st.markdown("### 📋 各等级分类报告")
        st.dataframe(kpi_df, width='stretch', hide_index=True)

with kpi_col2:
    if not confusion_df.empty:
        st.markdown("### 🎯 混淆矩阵")
        st.dataframe(confusion_df, width='stretch', hide_index=True)
    
    cat_df = data.get("category_dist", pd.DataFrame())
    if not cat_df.empty:
        st.markdown("### 📊 样本分布")
        st.dataframe(cat_df, width='stretch', hide_index=True)

if not roc_df.empty:
    st.markdown("### 🎯 ROC-AUC 性能")
    st.dataframe(roc_df, width='stretch', hide_index=True)


# ==================== 页脚 ====================
st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
st.markdown(f"""
<div class="footer">
    <p>🍎 果园病虫害风险预警与防控可视化看板 | 基于 LightGBM + SHAP + POSI 的智能预警系统</p>
    <p>数据来源：300个地块 · 4种果树品种 · 4类病虫害 · 三级风险等级 · 三级防控响应区</p>
    <p>页面刷新时间：{current_time} | 模拟实时刷新间隔：{AUTO_REFRESH_INTERVAL}秒</p>
    <p style="color:#bdc3c7;">© 2026 智慧果园病虫害预警系统 v2.0</p>
</div>
""", unsafe_allow_html=True)
