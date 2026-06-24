"""
全局配置文件 - 看板参数集中管理
"""
import os

# ==================== 路径配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# ==================== 看板基础配置 ====================
APP_TITLE = "🍎 果园病虫害风险预警与防控可视化看板"
APP_SUBTITLE = "基于 LightGBM + SHAP 的智能预警系统"
APP_LAYOUT = "wide"
APP_ICON = "🍎"

# ==================== 实时刷新配置 ====================
# 自动刷新间隔（秒）——模拟实时数据更新
AUTO_REFRESH_INTERVAL = 8
# 是否启用自动刷新
ENABLE_AUTO_REFRESH = True

# ==================== 风险等级配置 ====================
RISK_LEVELS = {
    0: {"label": "低风险", "color": "#2ecc71", "icon": "✅", "emoji": "🟢"},
    1: {"label": "中风险", "color": "#f39c12", "icon": "⚠️", "emoji": "🟡"},
    2: {"label": "高风险", "color": "#e74c3c", "icon": "🚨", "emoji": "🔴"},
}

RISK_LABEL_MAP = {0: "低风险", 1: "中风险", 2: "高风险"}
RISK_LABEL_REVERSE = {"低风险": 0, "中风险": 1, "高风险": 2, "低": 0, "中": 1, "高": 2}

# ==================== 防控方案配置 ====================
# 基础防控方案（按风险等级）
BASE_CONTROL_PLANS = {
    0: "【低风险】地块健康，执行常规巡检，无需施药。推荐巡检时段：每日上午9:00，频率：每7天1次。",
    1: "【中风险】局部发病，窗口期内点状施药。傍晚17:00喷施预防性药剂（减量），每3天1次监测，农药2种轮换(B→C)。",
    2: "【高风险】⚠️ 紧急！立即隔离地块，上午8:00完成全覆盖应急施药（全量），每天1次监测，农药3种轮换(A→B→C)。"
}

# 分时段防控建议
TIME_BASED_PLANS = {
    0: {
        "morning": (6, 12),
        "afternoon": (12, 17),
        "evening": (17, 21),
    },
    1: {
        "morning": (6, 12),
        "afternoon": (12, 17),
        "evening": (17, 21),
    },
    2: {
        "morning": (6, 12),
        "afternoon": (12, 17),
        "evening": (17, 21),
    }
}

# ==================== 地图颜色方案 ====================
MAP_COLORS = {
    "risk_low": "#2ecc71",
    "risk_medium": "#f39c12",
    "risk_high": "#e74c3c",
    "background": "#f8f9fa",
    "grid": "rgba(200,200,200,0.3)",
}

# ==================== 图表通用配置 ====================
CHART_FONT_FAMILY = "Microsoft YaHei, SimHei, sans-serif"
CHART_TEMPLATE = "plotly_white"
CHART_HEIGHT_DEFAULT = 400

# ==================== 模拟实时数据配置 ====================
SIMULATION_MODES = ["静态数据", "模拟实时（随机扰动）", "模拟实时（时段循环）"]
DEFAULT_SIMULATION_MODE = "模拟实时（随机扰动）"

# ==================== 数据资产运营中心配置 ====================
# 数据资产演示模块专用配置（仿真数据固定种子、页面标题）
OPS_RANDOM_SEED = 99
OPS_SECTION_TITLE = "🏢 数据资产与要素价值链运营中心"
OPS_SECTION_SUBTITLE = "多源数据 → 标准化资产 → 数据产品 → 行业服务价值流转全链路展示"
