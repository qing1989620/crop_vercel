# -*- coding: utf-8 -*-
"""
果园病虫害风险预警可视化看板 — Vercel 部署版
FastAPI + Plotly.js
"""
import os, sys, json
import pandas as pd
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from fastapi.middleware.cors import CORSMiddleware

# 路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

os.makedirs(TEMPLATE_DIR, exist_ok=True)

app = FastAPI(title="果园病虫害风险预警看板")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

from jinja2 import Environment, FileSystemLoader
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


# ==================== 数据加载 ====================
def _read_csv(path: str) -> pd.DataFrame:
    """安全读取CSV"""
    full = os.path.join(BASE_DIR, path) if not os.path.isabs(path) else path
    if not os.path.exists(full):
        return pd.DataFrame()
    for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030']:
        try:
            return pd.read_csv(full, encoding=enc)
        except Exception:
            continue
    return pd.DataFrame()

def load_all_data():
    data = {}
    base = "output/3.分区域分时段/tables"
    base2 = "output/2.低中高/tables"

    df = _read_csv(f"{base}/00_全量地块风险概率与标签.csv")
    data["main"] = df.where(pd.notnull(df), None).to_dict(orient="records") if not df.empty else []

    prev = _read_csv(f"{base}/05_防控单元精准方案推荐.csv")
    data["prevention"] = prev.where(pd.notnull(prev), None).to_dict(orient="records") if not prev.empty else []

    zone = _read_csv(f"{base}/06_防控响应区汇总统计.csv")
    data["response_zone"] = zone.where(pd.notnull(zone), None).to_dict(orient="records") if not zone.empty else []

    strategy = _read_csv(f"{base}/表3-5_三级差异化防控策略体系.csv")
    data["strategy"] = strategy.where(pd.notnull(strategy), None).to_dict(orient="records") if not strategy.empty else []

    rw = _read_csv(f"{base}/表3-4_风险等级与防治窗口交叉统计.csv")
    data["risk_window"] = rw.where(pd.notnull(rw), None).to_dict(orient="records") if not rw.empty else []

    posi = _read_csv(f"{base}/08_POSI因子权重.csv")
    data["posi_weights"] = posi.where(pd.notnull(posi), None).to_dict(orient="records") if not posi.empty else []

    rri = _read_csv(f"{base}/01_RRI区域风险指数与Jenks分区.csv")
    data["rri_jenks"] = rri.where(pd.notnull(rri), None).to_dict(orient="records") if not rri.empty else []

    feat = _read_csv(f"{base2}/特征重要性.csv")
    data["feature_importance"] = feat.where(pd.notnull(feat), None).to_dict(orient="records") if not feat.empty else []

    shap = _read_csv(f"{base2}/SHAP特征贡献.csv")
    data["shap"] = shap.where(pd.notnull(shap), None).to_dict(orient="records") if not shap.empty else []

    kpi = _read_csv(f"{base2}/核心KPI指标.csv")
    data["kpi"] = kpi.where(pd.notnull(kpi), None).to_dict(orient="records") if not kpi.empty else []

    cm = _read_csv(f"{base2}/混淆矩阵.csv")
    data["confusion"] = cm.where(pd.notnull(cm), None).to_dict(orient="records") if not cm.empty else []

    roc = _read_csv(f"{base2}/ROC_AUC值.csv")
    data["roc_auc"] = roc.where(pd.notnull(roc), None).to_dict(orient="records") if not roc.empty else []

    cat = _read_csv(f"{base2}/类别分布.csv")
    data["category_dist"] = cat.where(pd.notnull(cat), None).to_dict(orient="records") if not cat.empty else []

    return data


# ==================== 路由 ====================
@app.get("/api/data", response_class=HTMLResponse)
async def api_data():
    data = load_all_data()
    from fastapi.responses import JSONResponse
    return JSONResponse(content={"success": True, "data": data})


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    import json as _json
    data = load_all_data()
    df_main = _read_csv("output/3.分区域分时段/tables/00_全量地块风险概率与标签.csv")
    stats = {"total": len(df_main), "low": 0, "mid": 0, "high": 0}
    if not df_main.empty and "预测风险标签" in df_main.columns:
        vc = df_main["预测风险标签"].value_counts().to_dict()
        stats["low"] = int(vc.get("低", 0))
        stats["mid"] = int(vc.get("中", 0))
        stats["high"] = int(vc.get("高", 0))

    # 将 data 转为 JSON 字符串避免 Jinja2 unhashable 问题
    data_json = _json.dumps(data, ensure_ascii=False, default=str)

    return HTMLResponse(content=jinja_env.get_template("dashboard.html").render(
        request=request,
        data_json=data_json,
        total=stats["total"],
        low=stats["low"],
        mid=stats["mid"],
        high=stats["high"],
        title="果园病虫害风险预警与防控可视化看板"
    ))
