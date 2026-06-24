"""
模块6：模型特征重要性 & 可解释性分析（含农业通俗诊断 + 靶向调控建议）
"""
import streamlit as st
import pandas as pd
from utils.charts import create_feature_importance_chart, create_shap_chart, create_posi_weight_chart

# ==================== 特征 → 农事调控建议映射 ====================
FEATURE_SUGGEST_MAP = {
    "近7天病株数": "立即清除病枝病果，带出果园集中销毁，阻断传染源；病株周围喷施保护性杀菌剂隔离",
    "日照时数": "合理修剪过密枝条，改善冠层通风透光条件；高温强日照时段覆盖遮阳网降温",
    "BTM_生物威胁动量": "加密虫情监测频率，检查虫害扩散趋势；对高风险地块周边设置隔离缓冲带",
    "降水量": "及时开沟排水防涝渍，雨后24小时内检查果园积水情况；连续降雨后加密病害巡察",
    "LWI_光水滋养": "调整灌溉制度，避免过量灌溉导致叶片气孔开放时间延长，增加病菌入侵窗口",
    "相对湿度": "修剪枝叶通风降湿，清除园内杂草减少地表蒸发；湿度>85%时启动排风设备",
    "PRI_抗药性预警": "立即轮换农药品种（A→B→C），避免单一药剂连续使用超过2次；选用不同作用机理药剂",
    "风速": "风口地块增设防风林或防风网，减少强风导致的枝叶摩擦伤口（病菌入侵通道）",
    "近7天虫口密度": "投放诱虫灯、性诱捕器物理压低虫源基数；虫口超阈值时傍晚集中喷施杀虫剂",
    "THI_温湿胁迫": "高温时段早晚灌水降温，树盘覆盖稻草或地膜减少蒸发，减轻果树逆境胁迫",
    "平均气温": "关注连续高温预警，提前部署灌溉降温措施；温度异常波动时加密生理指标监测",
    "近30天用药次数": "用药频繁地块评估药害风险，暂停同类型农药；引入生物防治替代化学药剂",
}
# 特征名简写映射（SHAP列名 → 中文简称）
FEATURE_ALIAS = {
    "近7天病株数": "近7天病株数",
    "日照时数": "日照时数",
    "BTM_生物威胁动量": "生物威胁动量(BTM)",
    "降水量": "降水量",
    "LWI_光水滋养": "光水滋养指数(LWI)",
    "相对湿度": "环境相对湿度",
    "PRI_抗药性预警": "抗药性预警(PRI)",
    "风速": "风速",
    "近7天虫口密度": "近7天虫口数量",
    "THI_温湿胁迫": "气温胁迫指数(THI)",
    "平均气温": "平均气温",
    "近30天用药次数": "近30天用药次数",
}


def _extract_top_features(shap_df):
    """从 SHAP 数据提取 TOP 正/负贡献特征"""
    if shap_df.empty:
        return None, None, None, None
    name_col = shap_df.columns[0]
    # SHAP总贡献列
    shap_total_col = "SHAP总贡献" if "SHAP总贡献" in shap_df.columns else None
    if shap_total_col is None:
        for c in shap_df.columns:
            if "SHAP" in str(c) and "总" in str(c):
                shap_total_col = c
                break
    if shap_total_col is None:
        return None, None, None, None

    sdf = shap_df[shap_df[shap_total_col] > 0.001].copy()
    top_pos = sdf.nlargest(1, shap_total_col)
    top_neg = sdf.nsmallest(1, shap_total_col)
    pos_name = top_pos.iloc[0][name_col] if not top_pos.empty else None
    pos_val = round(float(top_pos.iloc[0][shap_total_col]), 2) if not top_pos.empty else 0
    neg_name = top_neg.iloc[0][name_col] if not top_neg.empty else None
    neg_val = round(float(top_neg.iloc[0][shap_total_col]), 2) if not top_neg.empty else 0
    return pos_name, pos_val, neg_name, neg_val


def _get_risk_level(df_filtered):
    """推断当前筛选视角下的主要风险等级"""
    if df_filtered is None or df_filtered.empty:
        return "低"
    for col in ["预测风险标签", "风险等级"]:
        if col in df_filtered.columns:
            counts = df_filtered[col].value_counts()
            if "高" in counts.values or 2 in counts.index:
                high_pct = (counts.get("高", 0) + counts.get(2, 0)) / len(df_filtered)
                if high_pct >= 0.3:
                    return "高"
            if "中" in counts.values or 1 in counts.index:
                mid_pct = (counts.get("中", 0) + counts.get(1, 0)) / len(df_filtered)
                if mid_pct >= 0.3:
                    return "中"
            return "低"
    return "低"


def _generate_diagnosis(risk_level, pos_name, pos_val, neg_name, neg_val):
    """生成农业通俗诊断文案"""
    pos_alias = FEATURE_ALIAS.get(pos_name, pos_name)
    neg_alias = FEATURE_ALIAS.get(neg_name, neg_name)

    if risk_level == "高":
        return (
            f"⚠️ 当前地块判定为**高风险**，主要诱因：**「{pos_alias}」**贡献最大（SHAP={pos_val:.2f}），"
            f"是病虫害爆发的核心驱动因素。**「{neg_alias}」**（SHAP={neg_val:.2f}）对病害发展有轻微抑制作用，"
            f"但不足以抵消高风险因子的助推效应。建议立即启动应急防控响应。"
        )
    elif risk_level == "中":
        return (
            f"⚠️ 当前地块处于**临界中风险**，**「{pos_alias}」**（SHAP={pos_val:.2f}）持续偏高，"
            f"存在短期内升级为高风险的趋势隐患。**「{neg_alias}」**（SHAP={neg_val:.2f}）为保护性因子，"
            f"但仍需加强常态化监测，防止风险恶化。"
        )
    else:
        return (
            f"✅ 当前地块整体**风险可控**，关键致害指标均处于低位。"
            f"{'**「' + pos_alias + '」**贡献相对最高（SHAP=' + str(round(pos_val, 2)) + '），' if pos_name else ''}"
            f"常规管护即可维持低风险状态。"
        )


def _generate_targeted_suggestions(pos_name, neg_name):
    """根据 TOP 正负贡献特征生成靶向田间措施"""
    suggestions = []
    for name in [pos_name, neg_name]:
        if name and name in FEATURE_SUGGEST_MAP:
            alias = FEATURE_ALIAS.get(name, name)
            suggestions.append(f"- **{alias}**：{FEATURE_SUGGEST_MAP[name]}")
    return suggestions


def render(fi_df, shap_df, posi_df, df_filtered=None):
    """渲染模型可解释性（特征重要性 + SHAP + 农业诊断 + 靶向建议）"""
    st.markdown("## 🔬 六、模型特征重要性 & 可解释性分析")
    st.caption("说明：风险判定、特征贡献数据来源于 LightGBM 模型输出 SHAP 值，农事建议结合果园植保病害三角理论制定")

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

    # ---- SHAP 农业通俗诊断 ----
    if not shap_df.empty:
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        st.markdown("### 🩺 模型诊断结论（农业通俗版）")

        pos_name, pos_val, neg_name, neg_val = _extract_top_features(shap_df)
        risk_level = _get_risk_level(df_filtered)

        if pos_name:
            diagnosis = _generate_diagnosis(risk_level, pos_name, pos_val, neg_name, neg_val)
            st.info(diagnosis)

            # 靶向调控建议
            suggestions = _generate_targeted_suggestions(pos_name, neg_name)
            if suggestions:
                st.markdown("#### 🎯 靶向调控建议（精准农事操作）")
                st.markdown("> *根据 SHAP 模型识别的高贡献因子，自动匹配田间调控措施：*")
                for s in suggestions:
                    st.markdown(s)
        else:
            st.info("当前 SHAP 数据量不足，无法生成自动诊断")

    # ---- POSI 环境因子权重 ----
    if not posi_df.empty:
        st.markdown("### ⚖️ POSI 环境因子权重")
        posi_fig = create_posi_weight_chart(posi_df)
        st.plotly_chart(posi_fig, use_container_width=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
