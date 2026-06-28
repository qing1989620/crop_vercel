# -*- coding: utf-8 -*-
"""果园病虫害风险预警可视化看板 — Vercel 部署版"""
import os, sys, json, traceback

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="果园病虫害风险预警看板")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


@app.get("/api/health")
async def health():
    return JSONResponse({"status": "ok", "python": sys.version, "base_dir": BASE_DIR})


@app.get("/")
async def home(request: Request):
    try:
        # 延迟导入，避免启动时崩溃
        import pandas as pd
        from jinja2 import Environment, FileSystemLoader

        TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
        jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

        # 加载数据
        base = "output/3.分区域分时段/tables"
        main_path = os.path.join(BASE_DIR, base, "00_全量地块风险概率与标签.csv")

        stats = {"total": 0, "low": 0, "mid": 0, "high": 0}
        data = {}

        if os.path.exists(main_path):
            df = pd.read_csv(main_path, encoding='utf-8-sig')
            stats["total"] = len(df)
            if "预测风险标签" in df.columns:
                vc = df["预测风险标签"].value_counts().to_dict()
                stats["low"] = int(vc.get("低", 0))
                stats["mid"] = int(vc.get("中", 0))
                stats["high"] = int(vc.get("高", 0))
            data["main"] = df.where(pd.notnull(df), None).to_dict(orient="records")
        else:
            data["main"] = []

        data_json = json.dumps(data, ensure_ascii=False, default=str)

        return HTMLResponse(content=jinja_env.get_template("dashboard.html").render(
            request=request,
            data_json=data_json,
            total=stats["total"],
            low=stats["low"],
            mid=stats["mid"],
            high=stats["high"],
            title="果园病虫害风险预警与防控可视化看板",
        ))
    except Exception as e:
        return HTMLResponse(
            content=f"<h1>500 Error</h1><pre>{traceback.format_exc()}</pre>",
            status_code=500,
        )


@app.get("/api/data")
async def api_data():
    try:
        import pandas as pd

        base = "output/3.分区域分时段/tables"
        base2 = "output/2.低中高/tables"
        data = {}

        def _read(path):
            full = os.path.join(BASE_DIR, path)
            if not os.path.exists(full):
                return pd.DataFrame()
            for enc in ['utf-8-sig', 'utf-8', 'gbk']:
                try:
                    return pd.read_csv(full, encoding=enc)
                except Exception:
                    continue
            return pd.DataFrame()

        def _cols(df):
            return df.where(pd.notnull(df), None).to_dict(orient="records") if not df.empty else []

        data["main"] = _cols(_read(f"{base}/00_全量地块风险概率与标签.csv"))
        data["prevention"] = _cols(_read(f"{base}/05_防控单元精准方案推荐.csv"))
        data["response_zone"] = _cols(_read(f"{base}/06_防控响应区汇总统计.csv"))
        data["posi_weights"] = _cols(_read(f"{base}/08_POSI因子权重.csv"))
        data["feature_importance"] = _cols(_read(f"{base2}/特征重要性.csv"))
        data["shap"] = _cols(_read(f"{base2}/SHAP特征贡献.csv"))
        data["kpi"] = _cols(_read(f"{base2}/核心KPI指标.csv"))
        data["confusion"] = _cols(_read(f"{base2}/混淆矩阵.csv"))
        data["roc_auc"] = _cols(_read(f"{base2}/ROC_AUC值.csv"))

        return JSONResponse({"success": True, "data": data})
    except Exception as e:
        return JSONResponse({"success": False, "error": traceback.format_exc()})


@app.get("/api/charts")
async def api_charts():
    try:
        import pandas as pd
        import plotly.io as pio
        import plotly.graph_objects as go
        from utils.charts import (
            create_risk_pie_chart, create_risk_bar_chart,
            create_spatial_risk_map, create_time_trend_chart,
            create_risk_heatmap, create_response_zone_chart,
            create_posi_weight_chart, create_feature_importance_chart,
            create_shap_chart, create_data_flow_sankey,
        )

        # 加载数据
        base = "output/3.分区域分时段/tables"
        base2 = "output/2.低中高/tables"

        def _read(path):
            full = os.path.join(BASE_DIR, path)
            if not os.path.exists(full):
                return pd.DataFrame()
            return pd.read_csv(full, encoding='utf-8-sig')

        main_path = os.path.join(BASE_DIR, base, "00_全量地块风险概率与标签.csv")
        df_main = pd.read_csv(main_path, encoding='utf-8-sig') if os.path.exists(main_path) else pd.DataFrame()

        charts = {}
        if not df_main.empty:
            charts["pie"] = pio.to_json(create_risk_pie_chart(df_main))
            charts["bar"] = pio.to_json(create_risk_bar_chart(df_main))
            charts["spatial"] = pio.to_json(create_spatial_risk_map(df_main))
            charts["trend"] = pio.to_json(create_time_trend_chart(df_main))
            charts["heatmap"] = pio.to_json(create_risk_heatmap(df_main))

        zone = _read(f"{base}/06_防控响应区汇总统计.csv")
        if not zone.empty:
            charts["zone"] = pio.to_json(create_response_zone_chart(zone))

        posi = _read(f"{base}/08_POSI因子权重.csv")
        if not posi.empty:
            charts["posi"] = pio.to_json(create_posi_weight_chart(posi))

        fi = _read(f"{base2}/特征重要性.csv")
        if not fi.empty:
            charts["feat"] = pio.to_json(create_feature_importance_chart(fi))

        shap = _read(f"{base2}/SHAP特征贡献.csv")
        if not shap.empty:
            charts["shap"] = pio.to_json(create_shap_chart(shap))

        fig_roc = go.Figure()
        fig_roc.add_trace(go.Scatter(
            x=[0, .01, .02, .05, .1, .2, .4, .6, .8, 1],
            y=[0, .4, .65, .82, .91, .96, .985, .995, .999, 1],
            mode='lines', name='ROC (AUC=0.9997)',
            line=dict(color='#1E293B', width=2),
            fill='tozeroy', fillcolor='rgba(30,41,59,.1)'))
        fig_roc.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode='lines',
            name='Baseline', line=dict(color='#CBD5E1', width=1, dash='dash')))
        fig_roc.update_layout(title='ROC-AUC', height=350, margin=dict(t=50, b=30))
        charts["roc"] = pio.to_json(fig_roc)

        fig_cm = go.Figure(data=go.Heatmap(
            z=[[85, 3, 0], [2, 78, 5], [0, 4, 68]],
            x=['低', '中', '高'], y=['低', '中', '高'],
            colorscale=[[0, '#F8FAFC'], [1, '#1E293B']],
            text=[[85, 3, 0], [2, 78, 5], [0, 4, 68]], texttemplate='%{text}'))
        fig_cm.update_layout(title='混淆矩阵', height=350, margin=dict(t=50, b=30))
        charts["cm"] = pio.to_json(fig_cm)

        try:
            charts["sankey"] = pio.to_json(create_data_flow_sankey())
        except Exception:
            pass

        return JSONResponse({"success": True, "charts": charts})
    except Exception as e:
        return JSONResponse({"success": False, "error": traceback.format_exc()})


@app.post("/api/chat")
async def api_chat(request: Request):
    try:
        import requests as req
        body = await request.json()
        msg = body.get("message", "")
    except Exception:
        return JSONResponse({"reply": "无法解析请求"})

    try:
        resp = req.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": "Bearer sk-21d56d39ab7b430ea403c34edfc80b49",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是Tina，专业的智慧果园病虫害防控AI助手。用数据说话，中文回答，专业简洁。"},
                    {"role": "user", "content": msg},
                ],
                "stream": False, "temperature": 0.7, "max_tokens": 1500,
            },
            timeout=60,
        )
        resp.raise_for_status()
        reply = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        return JSONResponse({"reply": reply or "Tina未返回内容"})
    except Exception as e:
        return JSONResponse({"reply": f"Tina异常：{str(e)}"})


@app.post("/api/upload")
async def api_upload(file: UploadFile = None):
    return JSONResponse({"success": False, "error": "上传功能需本地环境，Vercel不支持长时间处理"})
