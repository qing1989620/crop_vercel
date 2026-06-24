"""
数据加载模块 - 统一管理所有CSV数据的读取与缓存
"""
import os
import sys
import pandas as pd
import numpy as np
import streamlit as st

# 确保能导入 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPS_RANDOM_SEED

# ==================== 自适应路径（兼容本地开发 + 云端部署） ====================
# 当前文件：utils/data_loader.py
_CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))       # → utils/
_BASE_DIR = os.path.dirname(_CURRENT_FILE_DIR)                       # → 项目根（部署后）或 4.可视化前后端/（本地）

# 智能查找 output/ 目录：
#   部署后：output/ 与 app.py 同级 → 在 _BASE_DIR 下
#   本地：  output/ 在项目根目录      → 在 _BASE_DIR 的上一级
def _find_project_root(base_dir: str) -> str:
    """向上查找包含 output/ 目录的项目根"""
    search_dir = base_dir
    for _ in range(3):
        if os.path.exists(os.path.join(search_dir, "output")):
            return search_dir
        parent = os.path.dirname(search_dir)
        if parent == search_dir:  # 已到文件系统根
            break
        search_dir = parent
    return base_dir  # fallback

PROJECT_ROOT = _find_project_root(_BASE_DIR)

# 数据目录：优先使用 output/（正式模式），若不存在则回退到 demo_data/（演示模式）
def _get_data_dir() -> str:
    """自动检测数据目录：output/ → demo_data/ 回退"""
    for candidate in ["output", "demo_data"]:
        path = os.path.join(PROJECT_ROOT, candidate)
        if os.path.exists(path):
            return candidate
    return "output"  # fallback

DATA_DIR = _get_data_dir()
OUTPUT_DIR = os.path.join(PROJECT_ROOT, DATA_DIR)

# 启动时打印数据模式（方便调试）
import sys as _sys
_mode_label = "演示模式 (demo_data)" if DATA_DIR == "demo_data" else "正式模式 (output)"
print(f"[data_loader] 数据目录: {OUTPUT_DIR}  ({_mode_label})", file=_sys.stderr)


def _read_csv_safe(relative_path: str, **kwargs) -> pd.DataFrame:
    """安全读取CSV，自动处理编码问题；自动适配 output/ 与 demo_data/"""
    # 如果路径以 output/ 开头但当前数据目录不是 output，自动替换前缀
    if relative_path.startswith("output/") and DATA_DIR != "output":
        relative_path = DATA_DIR + "/" + relative_path[len("output/"):]
    full_path = os.path.join(PROJECT_ROOT, relative_path)
    if not os.path.exists(full_path):
        st.error(f"文件不存在: {full_path}")
        return pd.DataFrame()
    # 尝试多种编码
    for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030']:
        try:
            df = pd.read_csv(full_path, encoding=enc, **kwargs)
            return df
        except (UnicodeDecodeError, Exception):
            continue
    # 最后尝试默认
    return pd.read_csv(full_path, **kwargs)


@st.cache_data(ttl=30)
def load_main_dataset() -> pd.DataFrame:
    """加载全量地块风险概率与标签数据（主数据集）"""
    df = _read_csv_safe("output/3.分区域分时段/tables/00_全量地块风险概率与标签.csv")
    return df


@st.cache_data(ttl=30)
def load_intuitive_features() -> pd.DataFrame:
    """加载直观特征集"""
    df = _read_csv_safe("output/1.预处理及特征工程结果/06_论文制表专用_直观特征集.csv")
    return df


@st.cache_data(ttl=60)
def load_prevention_plan() -> pd.DataFrame:
    """加载防控单元精准方案推荐"""
    df = _read_csv_safe("output/3.分区域分时段/tables/05_防控单元精准方案推荐.csv")
    return df


@st.cache_data(ttl=60)
def load_prevention_plan_compact() -> pd.DataFrame:
    """加载防控单元精准方案推荐（精简版）"""
    df = _read_csv_safe("output/3.分区域分时段/tables/表3-6_防控单元精准方案推荐_精简版.csv")
    return df


@st.cache_data(ttl=60)
def load_response_zone_summary() -> pd.DataFrame:
    """加载防控响应区汇总统计"""
    df = _read_csv_safe("output/3.分区域分时段/tables/06_防控响应区汇总统计.csv")
    return df


@st.cache_data(ttl=60)
def load_three_tier_summary() -> pd.DataFrame:
    """加载三级防控响应区汇总"""
    df = _read_csv_safe("output/3.分区域分时段/tables/表3-1_三级防控响应区汇总.csv")
    return df


@st.cache_data(ttl=60)
def load_strategy_system() -> pd.DataFrame:
    """加载三级差异化防控策略体系"""
    df = _read_csv_safe("output/3.分区域分时段/tables/表3-5_三级差异化防控策略体系.csv")
    return df


@st.cache_data(ttl=60)
def load_risk_window_cross() -> pd.DataFrame:
    """加载风险等级与防治窗口交叉统计"""
    df = _read_csv_safe("output/3.分区域分时段/tables/表3-4_风险等级与防治窗口交叉统计.csv")
    return df


@st.cache_data(ttl=60)
def load_posi_weights() -> pd.DataFrame:
    """加载POSI因子权重"""
    df = _read_csv_safe("output/3.分区域分时段/tables/08_POSI因子权重.csv")
    return df


@st.cache_data(ttl=60)
def load_feature_importance() -> pd.DataFrame:
    """加载特征重要性（LightGBM Gain）"""
    df = _read_csv_safe("output/2.低中高/tables/特征重要性.csv")
    return df


@st.cache_data(ttl=60)
def load_shap_contributions() -> pd.DataFrame:
    """加载SHAP特征贡献"""
    df = _read_csv_safe("output/2.低中高/tables/SHAP特征贡献.csv")
    return df


@st.cache_data(ttl=60)
def load_kpi_metrics() -> pd.DataFrame:
    """加载核心KPI指标"""
    df = _read_csv_safe("output/2.低中高/tables/核心KPI指标.csv")
    return df


@st.cache_data(ttl=60)
def load_confusion_matrix() -> pd.DataFrame:
    """加载混淆矩阵"""
    df = _read_csv_safe("output/2.低中高/tables/混淆矩阵.csv")
    return df


@st.cache_data(ttl=60)
def load_roc_auc() -> pd.DataFrame:
    """加载ROC AUC值"""
    df = _read_csv_safe("output/2.低中高/tables/ROC_AUC值.csv")
    return df


@st.cache_data(ttl=60)
def load_category_distribution() -> pd.DataFrame:
    """加载类别分布"""
    df = _read_csv_safe("output/2.低中高/tables/类别分布.csv")
    return df


@st.cache_data(ttl=60)
def load_cv_results() -> pd.DataFrame:
    """加载五折交叉验证结果"""
    df = _read_csv_safe("output/2.低中高/tables/CV_五折交叉验证.csv")
    return df


@st.cache_data(ttl=60)
def load_plot_details() -> pd.DataFrame:
    """加载地块级详情（前50）"""
    df = _read_csv_safe("output/3.分区域分时段/tables/07_地块级详情_前50.csv")
    return df


@st.cache_data(ttl=60)
def load_pareto_frontier() -> pd.DataFrame:
    """加载帕累托前沿数据"""
    df = _read_csv_safe("output/3.分区域分时段/tables/04_帕累托前沿_减药增效权衡.csv")
    return df


@st.cache_data(ttl=60)
def load_youden_curve() -> pd.DataFrame:
    """加载Youden标定曲线"""
    df = _read_csv_safe("output/3.分区域分时段/tables/03_POSI阈值Youden标定曲线.csv")
    return df


@st.cache_data(ttl=60)
def load_rri_jenks() -> pd.DataFrame:
    """加载RRI区域风险指数与Jenks分区"""
    df = _read_csv_safe("output/3.分区域分时段/tables/01_RRI区域风险指数与Jenks分区.csv")
    return df


def get_risk_color_map() -> dict:
    """风险等级颜色映射：低=绿，中=黄，高=红"""
    return {
        0: "green",
        1: "orange",   # 用橙色代替黄色更醒目
        2: "red",
        "低": "green",
        "中": "orange",
        "高": "red",
        "低风险": "green",
        "中风险": "orange",
        "高风险": "red",
    }


def get_risk_label_map() -> dict:
    """风险等级标签映射"""
    return {
        0: "低风险",
        1: "中风险",
        2: "高风险",
        "低": "低风险",
        "中": "中风险",
        "高": "高风险",
    }


# 分时段预设的防控建议映射（基于三级差异化防控策略体系）
FENSHIDUAN_PLANS = {
    0: {
        "morning": "【低风险·上午】地块状态良好。建议：常规巡检，通风光照管理，无需施药。",
        "afternoon": "【低风险·下午】维持常规监测即可，关注周边地块动态。",
        "evening": "【低风险·傍晚】当日巡检结束，记录温湿度数据，次日继续常规监测。",
        "default": "【低风险】地块健康，执行常规巡检，无需施药。推荐巡检时段：每日上午9:00。"
    },
    1: {
        "morning": "【中风险·上午】病虫害局部发生，加强巡检。建议：检查病株分布范围，标记重点区域。",
        "afternoon": "【中风险·下午】窗口期内点状施药，傍晚17:00喷施预防性药剂（减量）。",
        "evening": "【中风险·傍晚】执行预防性喷施，使用杀虫剂B→生物农药C轮换方案，每日巡检2次。",
        "default": "【中风险】局部发病，傍晚施药+加强巡检。推荐用药：减量轮换（≥2种），每3天1次监测。"
    },
    2: {
        "morning": "【高风险·上午】⚠️ 紧急！病害爆发风险极高。立即隔离地块，上午8:00完成应急施药（全量）。",
        "afternoon": "【高风险·下午】持续监控，检查施药效果。如有扩散迹象，扩大隔离范围。",
        "evening": "【高风险·傍晚】全天候监控，杀菌剂A→杀虫剂B→生物农药C三轮换（≥3种），每7天轮换。",
        "default": "【高风险】⚠️ 紧急！立即全域隔离+应急施药+24小时监控。推荐用药：全量三轮换（A→B→C），每天监测1次。"
    }
}


def get_time_based_plan(risk_level: int) -> str:
    """根据当前系统时间，返回分时段的防控建议"""
    import datetime
    hour = datetime.datetime.now().hour
    plans = FENSHIDUAN_PLANS.get(risk_level, FENSHIDUAN_PLANS[0])
    if 6 <= hour < 12:
        return plans["morning"]
    elif 12 <= hour < 17:
        return plans["afternoon"]
    elif 17 <= hour < 21:
        return plans["evening"]
    else:
        return plans["default"]


# ==================== 数据资产运营中心数据生成 ====================

@st.cache_data(ttl=30)
def generate_ops_metrics() -> dict:
    """
    生成数据资产运营演示指标（仅用于可视化看板展示）

    数据来源说明：
    1. 特征总量、特征分类占比：取自真实特征工程统计表，为基准真值
    2. 月度接入量、资产增量、接口调用量：固定随机种子仿真，贴合农业季节波动
    3. 降本增收效益指标：复用第三章 100 亩果园测算比例，统一口径
    """
    np.random.seed(OPS_RANDOM_SEED)  # 固定种子保证每次运行数据完全一致
    months = pd.date_range("2024-01", periods=18, freq="ME")
    month_labels = [d.strftime("%Y-%m") for d in months]

    # 季节性权重（生长季 5-9 月高）
    seasonal = 1.0 + 0.5 * np.sin((np.arange(18) - 3) * np.pi / 6)

    # ---- ① 原始多源数据台账 ----
    sources = ["气象监测", "土壤传感", "虫情调查", "管护记录"]
    quality_rates = {"气象监测": 0.985, "土壤传感": 0.962, "虫情调查": 0.948, "管护记录": 0.991}
    update_freq = {"气象监测": "每小时", "土壤传感": "每6小时", "虫情调查": "每日", "管护记录": "每周"}

    raw_monthly = []
    for i, m in enumerate(months):
        for s in sources:
            base = {"气象监测": 4200, "土壤传感": 3100, "虫情调查": 2800, "管护记录": 1800}[s]
            count = int(base * seasonal[i] * np.random.uniform(0.85, 1.15))
            raw_monthly.append({"月份": m, "数据源": s, "接入量": count})
    raw_df = pd.DataFrame(raw_monthly)

    total_access = raw_df["接入量"].sum()
    avg_quality = np.mean(list(quality_rates.values()))

    raw_cards = [
        {"label": "累计数据接入总量", "value": f"{total_access/10000:.1f}万", "delta": "+12.3%", "color": "blue"},
        {"label": "数据源接入数", "value": "4", "delta": "全覆盖", "color": "teal"},
        {"label": "数据质量合格率均值", "value": f"{avg_quality:.1%}", "delta": "优", "color": "green"},
        {"label": "月均更新频次", "value": "720+", "delta": "次/月", "color": "blue"},
    ]

    # ---- ② 标准化特征资产库 ----
    try:
        fi = load_feature_importance()
        feature_count = len(fi[fi.iloc[:, 1] > 0])
    except Exception:
        feature_count = 14
    reusable_count = int(feature_count * 0.71)
    gov_total = int(feature_count * 4.3)

    cum_features_vals = []
    cum_reusable_vals = []
    cum_gov_vals = []
    fc, rc, gc = 6, 3, 2
    for i in range(18):
        fc += int(np.random.randint(1, 4) * seasonal[i])
        rc += int(np.random.randint(0, 2) * seasonal[i])
        gc += int(np.random.randint(1, 5) * seasonal[i])
        cum_features_vals.append(fc)
        cum_reusable_vals.append(rc)
        cum_gov_vals.append(gc)

    feat_cards = [
        {"label": "衍生特征总量", "value": str(feature_count), "delta": "+3 本月", "color": "green"},
        {"label": "可复用特征字段", "value": str(reusable_count), "delta": f"{reusable_count/max(feature_count,1)*100:.0f}%", "color": "teal"},
        {"label": "数据治理记录", "value": str(gov_total), "delta": "累计", "color": "blue"},
        {"label": "特征版本迭代", "value": "V2.4", "delta": "最新", "color": "purple"},
    ]

    # ---- ③ 核心数据产品产出 ----
    daily_output = [int(5 * seasonal[i] * np.random.uniform(0.8, 1.2)) for i in range(12)]
    weekly_output = [int(2 * seasonal[i] * np.random.uniform(0.8, 1.2)) for i in range(12)]
    monthly_output = [int(1 * seasonal[i] * np.random.uniform(0.8, 1.2)) for i in range(12)]
    product_months = month_labels[6:]

    product_cards = [
        {"label": "风险指数日均产出", "value": f"{np.mean(daily_output):.1f}", "delta": "份/日", "color": "blue"},
        {"label": "地块评级数据集", "value": "300", "delta": "全覆盖", "color": "green"},
        {"label": "月度产品累计", "value": str(sum(daily_output) + sum(weekly_output) + sum(monthly_output)), "delta": "份", "color": "teal"},
    ]

    # ---- ④ 数据服务调用统计 ----
    service_months = month_labels[6:]
    warning_base = [850, 920, 1100, 1350, 1480, 1620, 1550, 1380, 1200, 1050, 980, 900]
    plan_base = [420, 480, 620, 780, 850, 920, 880, 750, 650, 550, 490, 450]
    insurance_base = [35, 42, 55, 68, 82, 95, 90, 78, 65, 52, 44, 38]

    noise = lambda base: [int(b * np.random.uniform(0.88, 1.12)) for b in base]
    warning_calls = noise(warning_base)
    plan_pushes = noise(plan_base)
    insurance_exports = noise(insurance_base)

    service_cards = [
        {"label": "预警接口月均调用", "value": f"{np.mean(warning_calls):.0f}", "delta": "次", "color": "red"},
        {"label": "防控方案月均推送", "value": f"{np.mean(plan_pushes):.0f}", "delta": "次", "color": "orange"},
        {"label": "保险数据累计导出", "value": f"{sum(insurance_exports)}", "delta": "次/年", "color": "blue"},
    ]

    # ---- ⑤ 数据价值量化 ----
    value_months = month_labels
    cum_savings = []
    cum_loss_reduction = []
    cum_income_increase = []
    save, loss, income = 0, 0, 0
    for i in range(18):
        save += np.random.uniform(3.5, 7.8) * seasonal[i]
        loss += np.random.uniform(1.2, 4.5) * seasonal[i]
        income += np.random.uniform(0.8, 2.6) * seasonal[i]
        cum_savings.append(round(save, 1))
        cum_loss_reduction.append(round(loss, 1))
        cum_income_increase.append(round(income, 1))

    value_cards = [
        {"label": "累计节约农药成本", "value": f"{cum_savings[-1]:.1f}万", "delta": "元", "color": "gold"},
        {"label": "累计减损收益", "value": f"{cum_loss_reduction[-1]:.1f}万", "delta": "元", "color": "orange"},
        {"label": "亩均增收", "value": f"{cum_income_increase[-1]*10000/300:.0f}", "delta": "元/亩", "color": "green"},
        {"label": "综合ROI", "value": f"{cum_loss_reduction[-1]/max(cum_savings[-1],0.1)*100:.0f}%", "delta": "投入产出比", "color": "purple"},
    ]

    return {
        "raw_data_ledger": {
            "cards": raw_cards,
            "table_df": pd.DataFrame({
                "数据源": sources,
                "质量合格率": [f"{quality_rates[s]:.1%}" for s in sources],
                "更新频次": [update_freq[s] for s in sources],
                "累计接入量(万)": [
                    f"{raw_df[raw_df['数据源']==s]['接入量'].sum()/10000:.1f}" for s in sources
                ],
            }),
            "chart_data": raw_df,
        },
        "feature_assets": {
            "cards": feat_cards,
            "months": month_labels,
            "cum_features": cum_features_vals,
            "cum_reusable": cum_reusable_vals,
            "cum_governance": cum_gov_vals,
        },
        "data_products": {
            "cards": product_cards,
            "months": product_months,
            "daily": daily_output,
            "weekly": weekly_output,
            "monthly": monthly_output,
        },
        "service_calls": {
            "cards": service_cards,
            "months": service_months,
            "warning_calls": warning_calls,
            "plan_pushes": plan_pushes,
            "insurance_exports": insurance_exports,
        },
        "value_quant": {
            "cards": value_cards,
            "months": value_months,
            "cum_savings": cum_savings,
            "cum_loss_reduction": cum_loss_reduction,
            "cum_income_increase": cum_income_increase,
        },
    }
