"""
模块8：数据资产与要素价值链运营中心
"""
import streamlit as st
import pandas as pd
from config import OPS_SECTION_TITLE, OPS_SECTION_SUBTITLE
from utils.data_loader import generate_ops_metrics
from utils.charts import (
    create_data_flow_sankey, create_asset_increment_chart, create_service_call_chart,
    create_raw_data_bar_chart, create_product_output_chart, create_value_growth_chart,
)

# 指标卡色系映射
CARD_GRADIENTS = {
    "blue": "linear-gradient(135deg, #3498db, #2980b9)",
    "teal": "linear-gradient(135deg, #1abc9c, #16a085)",
    "green": "linear-gradient(135deg, #2ecc71, #27ae60)",
    "orange": "linear-gradient(135deg, #f39c12, #e67e22)",
    "red": "linear-gradient(135deg, #e74c3c, #c0392b)",
    "purple": "linear-gradient(135deg, #9b59b6, #8e44ad)",
    "gold": "linear-gradient(135deg, #f1c40f, #f39c12)",
}


def _make_cards_html(cards, cols_per_row=4):
    """渲染指标卡行"""
    n = len(cards)
    for row_start in range(0, n, cols_per_row):
        row_cards = cards[row_start:row_start + cols_per_row]
        cols = st.columns(len(row_cards))
        for i, card in enumerate(row_cards):
            grad = CARD_GRADIENTS.get(card["color"], CARD_GRADIENTS["blue"])
            with cols[i]:
                st.markdown(f"""
                <div class="metric-card" style="background:{grad};">
                    <div class="metric-label">{card['label']}</div>
                    <div class="metric-value">{card['value']}</div>
                    <div class="metric-delta">{card['delta']}</div>
                </div>
                """, unsafe_allow_html=True)


def render():
    """渲染数据资产运营中心（Sankey + 5 个子模块）"""
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown(f"## {OPS_SECTION_TITLE}")
    st.markdown(f"*{OPS_SECTION_SUBTITLE}*")

    ops = generate_ops_metrics()

    # --- 数据价值链 Sankey 流转图 ---
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    sankey_fig = create_data_flow_sankey()
    st.plotly_chart(sankey_fig, use_container_width=True)
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # ===== ① 原始多源数据台账 =====
    st.markdown("### ① 原始多源数据台账")
    raw = ops["raw_data_ledger"]
    _make_cards_html(raw["cards"])

    raw_col1, raw_col2 = st.columns([3, 2])
    with raw_col1:
        fig_raw = create_raw_data_bar_chart(raw["chart_data"])
        st.plotly_chart(fig_raw, use_container_width=True)
    with raw_col2:
        st.markdown("#### 数据源质量概况")
        st.dataframe(raw["table_df"], use_container_width=True, hide_index=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # ===== ② 标准化特征资产库统计 =====
    st.markdown("### ② 标准化特征资产库统计")
    feat = ops["feature_assets"]
    _make_cards_html(feat["cards"])

    asset_fig = create_asset_increment_chart(
        feat["months"], feat["cum_features"],
        feat["cum_reusable"], feat["cum_governance"]
    )
    st.plotly_chart(asset_fig, use_container_width=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # ===== ③ 核心数据产品产出统计 =====
    st.markdown("### ③ 核心数据产品产出统计")
    prod = ops["data_products"]
    _make_cards_html(prod["cards"], cols_per_row=3)

    prod_col1, prod_col2 = st.columns([2, 1])
    with prod_col1:
        fig_prod = create_product_output_chart(
            prod["months"], prod["daily"], prod["weekly"], prod["monthly"]
        )
        st.plotly_chart(fig_prod, use_container_width=True)
    with prod_col2:
        st.markdown("#### 产品产出概要")
        prod_summary = pd.DataFrame({
            "产出类型": ["日度风险指数", "周度风险指数", "月度风险指数", "地块评级数据集"],
            "累计产出": [
                f"{sum(prod['daily'])} 份",
                f"{sum(prod['weekly'])} 份",
                f"{sum(prod['monthly'])} 份",
                "300 地块",
            ],
        })
        st.dataframe(prod_summary, use_container_width=True, hide_index=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # ===== ④ 数据服务调用统计 =====
    st.markdown("### ④ 数据服务调用统计")
    svc = ops["service_calls"]
    _make_cards_html(svc["cards"], cols_per_row=3)

    svc_fig = create_service_call_chart(
        svc["months"], svc["warning_calls"],
        svc["plan_pushes"], svc["insurance_exports"]
    )
    st.plotly_chart(svc_fig, use_container_width=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # ===== ⑤ 数据价值量化看板 =====
    st.markdown("### ⑤ 数据价值量化看板")
    val = ops["value_quant"]
    _make_cards_html(val["cards"])

    val_fig = create_value_growth_chart(
        val["months"], val["cum_savings"],
        val["cum_loss_reduction"], val["cum_income_increase"]
    )
    st.plotly_chart(val_fig, use_container_width=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
