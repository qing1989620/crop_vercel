"""
模块2：果园分区域风险空间分布
"""
import streamlit as st
from config import RISK_LEVELS
from utils.charts import create_spatial_risk_map


def render(df_filtered, risk_col):
    """渲染空间风险分布（散点地图 + 品种风险表）"""
    st.markdown("## 🗺️ 二、果园分区域风险空间分布")

    map_col1, map_col2 = st.columns([2, 1])

    with map_col1:
        map_fig = create_spatial_risk_map(df_filtered)
        st.plotly_chart(map_fig, use_container_width=True)

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
            st.dataframe(variety_risk, use_container_width=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
