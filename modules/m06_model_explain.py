"""
模块6：模型特征重要性 & 可解释性分析
"""
import streamlit as st
import pandas as pd
from utils.charts import create_feature_importance_chart, create_shap_chart, create_posi_weight_chart


def render(fi_df, shap_df, posi_df):
    """渲染模型可解释性（特征重要性 + SHAP + POSI 权重）"""
    st.markdown("## 🔬 六、模型特征重要性 & 可解释性分析")

    explain_col1, explain_col2 = st.columns(2)

    with explain_col1:
        if not fi_df.empty:
            fi_fig = create_feature_importance_chart(fi_df)
            st.plotly_chart(fi_fig, use_container_width=True)
        else:
            st.info("暂无特征重要性数据")

    with explain_col2:
        if not shap_df.empty:
            shap_fig = create_shap_chart(shap_df)
            st.plotly_chart(shap_fig, use_container_width=True)
        elif not posi_df.empty:
            posi_fig = create_posi_weight_chart(posi_df)
            st.plotly_chart(posi_fig, use_container_width=True)
        else:
            st.info("暂无SHAP/POSI数据")

    if not posi_df.empty:
        st.markdown("### ⚖️ POSI 环境因子权重")
        posi_fig = create_posi_weight_chart(posi_df)
        st.plotly_chart(posi_fig, use_container_width=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
