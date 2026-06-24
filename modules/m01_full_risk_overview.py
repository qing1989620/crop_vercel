"""
模块1：全园风险态势总览
"""
import streamlit as st
import pandas as pd
from config import RISK_LEVELS
from utils.charts import create_risk_pie_chart, create_risk_bar_chart


def render(df_filtered, risk_col, risk_label_col, low_count, mid_count, high_count):
    """渲染全园风险态势总览（指标卡 + 饼图 + 柱状图）"""
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
        st.plotly_chart(pie_fig, use_container_width=True)
    with chart_col2:
        bar_fig = create_risk_bar_chart(df_filtered)
        st.plotly_chart(bar_fig, use_container_width=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
