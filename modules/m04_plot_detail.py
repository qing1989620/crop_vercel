"""
模块4：单地块详情与精准防控建议
"""
import streamlit as st
import pandas as pd
import random
from config import RISK_LEVELS
from utils.data_loader import get_time_based_plan


def render(df_filtered, risk_col, risk_label_col, prevention_df):
    """渲染单地块详情（地块选择器 + POSI 指标 + 防控建议 + 环境监测）"""
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
        if st.button("🎲 随机选择地块", use_container_width=True):
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
                    st.dataframe(posi_df, use_container_width=True, hide_index=True)

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
                st.dataframe(env_df, use_container_width=True, hide_index=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
