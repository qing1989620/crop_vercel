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
import os
import sys

# 将当前目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    APP_TITLE, APP_LAYOUT, AUTO_REFRESH_INTERVAL, ENABLE_AUTO_REFRESH,
    SIMULATION_MODES, DEFAULT_SIMULATION_MODE,
)
from utils.data_loader import (
    load_main_dataset, load_prevention_plan, load_response_zone_summary,
    load_three_tier_summary, load_strategy_system, load_risk_window_cross,
    load_feature_importance, load_shap_contributions, load_kpi_metrics,
    load_confusion_matrix, load_roc_auc, load_category_distribution,
    load_posi_weights,
)
from utils.css_style import inject_custom_css
from modules import (
    m01_full_risk_overview, m02_spatial_risk_map, m03_time_trend,
    m04_plot_detail, m05_three_tier_response, m06_model_explain,
    m07_model_performance, m08_data_asset_ops,
)

# ==================== 页面基础配置 ====================
st.set_page_config(
    page_title="果园病虫害预警看板",
    page_icon="🍎",
    layout=APP_LAYOUT,
    initial_sidebar_state="expanded"
)

# ==================== 自定义 CSS 样式 ====================
inject_custom_css()

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

# 存一份 sim_mode 到 session_state，Module 8 中用到
st.session_state["sim_mode"] = sim_mode

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


# ==================== 模块调用 ====================
m01_full_risk_overview.render(df_filtered, risk_col, risk_label_col, low_count, mid_count, high_count)
m02_spatial_risk_map.render(df_filtered, risk_col)
m03_time_trend.render(df_filtered, data.get("risk_window", pd.DataFrame()), risk_label_col, risk_col)
m04_plot_detail.render(df_filtered, risk_col, risk_label_col, data.get("prevention", pd.DataFrame()))
m05_three_tier_response.render(
    data.get("strategy", pd.DataFrame()),
    data.get("response_zone", pd.DataFrame()),
    data.get("prevention", pd.DataFrame()),
)
m06_model_explain.render(
    data.get("feature_importance", pd.DataFrame()),
    data.get("shap", pd.DataFrame()),
    data.get("posi_weights", pd.DataFrame()),
    df_filtered,
)
m07_model_performance.render(
    data.get("kpi", pd.DataFrame()),
    data.get("roc_auc", pd.DataFrame()),
    data.get("confusion", pd.DataFrame()),
    data.get("category_dist", pd.DataFrame()),
)
m08_data_asset_ops.render()

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
