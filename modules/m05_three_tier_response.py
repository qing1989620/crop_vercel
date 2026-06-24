"""
模块5：三级差异化防控策略体系（含农药减量 + 成本节约量化展示）
"""
import streamlit as st
import pandas as pd
from utils.charts import create_response_zone_chart

# ==================== 农药减量增效量化参数（基于100亩果园测算口径） ====================
# 传统基准：全园施药 78 元/亩·次
# 红色区节约 = 78 - 36 = 42；黄色区节约 = 78 - 35 = 43；绿色区节约 = 78 - 5 = 73
ZONE_BENEFIT_PARAMS = {
    "红色区(应急防控)": {
        "dose_reduction_pct": 35,
        "cost_per_mu": 36,
        "cost_saved_per_mu": 42,
        "loss_reduction_pct": 28,
        "desc": "病害爆发风险高，需针对性药剂消杀，仍可大幅减少全域无差别用药量",
    },
    "黄色区(预防施药)": {
        "dose_reduction_pct": 55,
        "cost_per_mu": 35,
        "cost_saved_per_mu": 43,
        "loss_reduction_pct": 18,
        "desc": "仅对窗口内地块点状减量施药，非窗口地块只监测不施药，大幅压低用药量",
    },
    "绿色区(常规监测)": {
        "dose_reduction_pct": 94,
        "cost_per_mu": 5,
        "cost_saved_per_mu": 73,
        "loss_reduction_pct": 0,
        "desc": "以常态化监测预警为主，基础管护极低农药投入，仅在 POSI 指标超阈值时针对性微量处置",
    },
}

# 传统方案对照基准（全园打药，无差异化）
TRADITIONAL_COST_PER_MU = 78  # 元/亩 · 次
TOTAL_MU = 100  # 100亩果园测算口径
TOTAL_PARCELS = 300


def _compute_summary(prevention_df):
    """从 prevention_df 按风险等级汇总各防控区地块数，计算全园精准防控效益"""
    if prevention_df.empty:
        return None

    zone_counts = {"红色区(应急防控)": 0, "黄色区(预防施药)": 0, "绿色区(常规监测)": 0}
    for _, row in prevention_df.iterrows():
        risk_level = row.get("风险等级", 0)
        parcels = int(row.get("地块数", 0))
        if risk_level == 2:
            zone_counts["红色区(应急防控)"] += parcels
        elif risk_level == 1:
            zone_counts["黄色区(预防施药)"] += parcels
        else:
            zone_counts["绿色区(常规监测)"] += parcels

    total_monthly_saved = 0
    total_annual_income = 0
    for zone, count in zone_counts.items():
        params = ZONE_BENEFIT_PARAMS.get(zone, {})
        saved_per_mu = params.get("cost_saved_per_mu", 0)
        mu_per_parcel = TOTAL_MU / TOTAL_PARCELS
        total_monthly_saved += count * mu_per_parcel * saved_per_mu
        loss_pct = params.get("loss_reduction_pct", 0) / 100
        total_annual_income += count * mu_per_parcel * 3000 * loss_pct

    return {
        "zone_counts": zone_counts,
        "total_monthly_saved": round(total_monthly_saved, 0),
        "total_annual_income": round(total_annual_income, 0),
    }


def _render_benefit_card(zone_name, params, parcel_count):
    """渲染单个防控区的效益测算卡片"""
    icon = {"红色区(应急防控)": "🔴", "黄色区(预防施药)": "🟡", "绿色区(常规监测)": "🟢"}
    card_color = {"红色区(应急防控)": "#fdedec", "黄色区(预防施药)": "#fef9e7", "绿色区(常规监测)": "#eafaf1"}
    border_color = {"红色区(应急防控)": "#e74c3c", "黄色区(预防施药)": "#f39c12", "绿色区(常规监测)": "#2ecc71"}

    emoji = icon.get(zone_name, "📋")
    bg = card_color.get(zone_name, "#f8f9fa")
    border = border_color.get(zone_name, "#bdc3c7")

    dose_pct = params.get("dose_reduction_pct", 0)
    cost_per_mu = params.get("cost_per_mu", 0)
    cost_saved = params.get("cost_saved_per_mu", 0)
    loss_pct = params.get("loss_reduction_pct", 0)
    desc = params.get("desc", "")

    st.markdown(f"""
    <div style="padding:15px;margin:8px 0;border-radius:8px;border-left:5px solid {border};background:{bg};">
        <b>{emoji} {zone_name}</b>（{parcel_count} 个地块）
        <p style="margin:5px 0;font-size:0.9rem;color:#555;">{desc}</p>
        <table style="width:100%;font-size:0.9rem;margin-top:8px;">
            <tr>
                <td style="color:#7f8c8d;">💊 相较传统模式减少</td>
                <td style="font-weight:700;color:#27ae60;">{dose_pct}%</td>
                <td style="color:#7f8c8d;">单次精准防控成本</td>
                <td style="font-weight:700;">{cost_per_mu} 元/亩</td>
                <td style="color:#7f8c8d;">单次节约</td>
                <td style="font-weight:700;color:#e67e22;">{cost_saved} 元/亩</td>
            </tr>
            <tr>
                <td style="color:#7f8c8d;">📉 病虫害减产损失降低</td>
                <td style="font-weight:700;color:#2980b9;">{loss_pct}%</td>
                <td style="color:#7f8c8d;">📊 传统对照</td>
                <td colspan="3" style="color:#7f8c8d;">传统全园施药：{TRADITIONAL_COST_PER_MU} 元/亩·次</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)


def render(strategy_df, response_zone_df, prevention_df):
    """渲染三级防控策略（响应区图 + 策略对照表 + 效益量化 + 精准方案表）"""
    st.markdown("## 🛡️ 五、三级差异化防控策略体系")
    st.caption(
        "效益测算口径：基于连片 100 亩标准化果园完整生长季测算；"
        "传统全域施药基准成本 78 元/亩·次，精准防控分区分级施策，"
        "数值与数据资产总览模块统一"
    )

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

    # ---- 分级防控效益测算 ----
    st.markdown("### 💰 分级防控效益测算")
    st.caption("各风险等级差异化防控成本与减量效益对比")

    summary = _compute_summary(prevention_df)

    if summary:
        benefit_cols = st.columns(3)
        zones = ["红色区(应急防控)", "黄色区(预防施药)", "绿色区(常规监测)"]
        for i, zone in enumerate(zones):
            with benefit_cols[i]:
                params = ZONE_BENEFIT_PARAMS.get(zone, {})
                count = summary["zone_counts"].get(zone, 0)
                _render_benefit_card(zone, params, count)

    # ---- 汇总面板 ----
    if summary:
        st.markdown("---")
        st.markdown("### 📊 全园精准防控汇总效益")

        sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)

        with sum_col1:
            total_parcels = sum(summary["zone_counts"].values())
            st.markdown(f"""
            <div class="metric-card" style="background:linear-gradient(135deg,#3498db,#2980b9);">
                <div class="metric-value">{total_parcels}</div>
                <div class="metric-label">📋 精准防控覆盖地块</div>
                <div class="metric-delta">100% 差异化施策</div>
            </div>
            """, unsafe_allow_html=True)

        with sum_col2:
            total_saved = summary["total_monthly_saved"]
            st.markdown(f"""
            <div class="metric-card" style="background:linear-gradient(135deg,#27ae60,#2ecc71);">
                <div class="metric-value">{total_saved:.0f}</div>
                <div class="metric-label">💰 月度节约农药成本</div>
                <div class="metric-delta">元/月（100亩）</div>
            </div>
            """, unsafe_allow_html=True)

        with sum_col3:
            annual_saved = total_saved * 12
            st.markdown(f"""
            <div class="metric-card" style="background:linear-gradient(135deg,#f1c40f,#f39c12);">
                <div class="metric-value">{annual_saved:.0f}</div>
                <div class="metric-label">📅 全年预估节约</div>
                <div class="metric-delta">元/年（100亩）</div>
            </div>
            """, unsafe_allow_html=True)

        with sum_col4:
            annual_income = summary["total_annual_income"]
            st.markdown(f"""
            <div class="metric-card" style="background:linear-gradient(135deg,#e74c3c,#c0392b);">
                <div class="metric-value">{annual_income:.0f}</div>
                <div class="metric-label">📈 全年预估增收</div>
                <div class="metric-delta">元/年（减损收益）</div>
            </div>
            """, unsafe_allow_html=True)

    # ---- 精准方案明细表 ----
    if not prevention_df.empty:
        st.markdown("### 💊 防控单元精准方案推荐")
        display_cols = [c for c in prevention_df.columns if prevention_df[c].nunique() > 0][:8]
        st.dataframe(prevention_df[display_cols], use_container_width=True, height=300)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
