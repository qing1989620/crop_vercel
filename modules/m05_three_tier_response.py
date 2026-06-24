"""
模块5：三级差异化防控策略体系
"""
import streamlit as st
import pandas as pd
from utils.charts import create_response_zone_chart


def render(strategy_df, response_zone_df, prevention_df):
    """渲染三级防控策略（响应区图 + 策略对照表 + 精准方案表）"""
    st.markdown("## 🛡️ 五、三级差异化防控策略体系")

    strat_col1, strat_col2 = st.columns(2)

    with strat_col1:
        if not response_zone_df.empty:
            zone_fig = create_response_zone_chart(response_zone_df)
            st.plotly_chart(zone_fig, use_container_width=True)
        else:
            st.info("暂无防控响应区数据")

    with strat_col2:
        if not strategy_df.empty:
            st.markdown("### 📋 三级防控策略对照表")
            strategy_display = strategy_df.copy()
            if "防控维度" in strategy_display.columns:
                strategy_display = strategy_display.set_index("防控维度").T
            st.dataframe(strategy_display, use_container_width=True)
        else:
            st.info("暂无防控策略数据")

    if not prevention_df.empty:
        st.markdown("### 💊 防控单元精准方案推荐")
        display_cols = [c for c in prevention_df.columns if prevention_df[c].nunique() > 0][:8]
        st.dataframe(prevention_df[display_cols], use_container_width=True, height=300)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
