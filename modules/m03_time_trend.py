"""
模块3：分时段风险趋势与交叉分析
"""
import streamlit as st
import pandas as pd
from utils.charts import create_time_trend_chart, create_risk_heatmap


def render(df_filtered, risk_window_df, risk_label_col, risk_col):
    """渲染分时段风险趋势（折线图 + 热力图 + 交叉统计表）"""
    st.markdown("## 📈 三、分时段风险趋势与交叉分析")

    trend_col1, trend_col2 = st.columns(2)

    with trend_col1:
        trend_fig = create_time_trend_chart(df_filtered)
        st.plotly_chart(trend_fig, use_container_width=True)

    with trend_col2:
        heatmap_fig = create_risk_heatmap(df_filtered)
        st.plotly_chart(heatmap_fig, use_container_width=True)

    st.markdown("### 风险等级 × 防治窗口 交叉统计明细")
    if not risk_window_df.empty:
        st.dataframe(risk_window_df, use_container_width=True)
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
        st.dataframe(cross, use_container_width=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
