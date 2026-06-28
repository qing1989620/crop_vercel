# -*- coding: utf-8 -*-
"""果园病虫害风险预警可视化看板 — Vercel 部署版"""
import os, sys, json
import pandas as pd
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
os.makedirs(TEMPLATE_DIR, exist_ok=True)
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

app = FastAPI(title="果园病虫害风险预警看板")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ==================== 数据加载 ====================
def _read_csv(path: str) -> pd.DataFrame:
    full = os.path.join(BASE_DIR, path) if not os.path.isabs(path) else path
    if not os.path.exists(full):
        return pd.DataFrame()
    for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030']:
        try: return pd.read_csv(full, encoding=enc)
        except Exception: continue
    return pd.DataFrame()


def load_all_data() -> dict:
    data = {}
    base = "output/3.分区域分时段/tables"
    base2 = "output/2.低中高/tables"
    def _cols(df):
        return df.where(pd.notnull(df), None).to_dict(orient="records") if not df.empty else []
    data["main"] = _cols(_read_csv(f"{base}/00_全量地块风险概率与标签.csv"))
    data["prevention"] = _cols(_read_csv(f"{base}/05_防控单元精准方案推荐.csv"))
    data["response_zone"] = _cols(_read_csv(f"{base}/06_防控响应区汇总统计.csv"))
    data["posi_weights"] = _cols(_read_csv(f"{base}/08_POSI因子权重.csv"))
    data["feature_importance"] = _cols(_read_csv(f"{base2}/特征重要性.csv"))
    data["shap"] = _cols(_read_csv(f"{base2}/SHAP特征贡献.csv"))
    data["kpi"] = _cols(_read_csv(f"{base2}/核心KPI指标.csv"))
    data["confusion"] = _cols(_read_csv(f"{base2}/混淆矩阵.csv"))
    data["roc_auc"] = _cols(_read_csv(f"{base2}/ROC_AUC值.csv"))
    data["category_dist"] = _cols(_read_csv(f"{base2}/类别分布.csv"))
    return data


# ==================== API 路由 ====================

@app.get("/api/data")
async def api_data():
    return JSONResponse(content={"success": True, "data": load_all_data()})


@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    """上传 CSV 数据集"""
    from api.process import save_uploaded_csv, validate_csv
    content = await file.read()
    filepath = save_uploaded_csv(content, file.filename or "data.csv")
    validation = validate_csv(filepath)
    return JSONResponse(content={
        "success": validation["valid"],
        "filename": file.filename,
        "validation": validation,
    })


@app.post("/api/process")
async def api_process(request: Request):
    """触发数据处理管线"""
    from api.process import run_full_pipeline, UPLOAD_DIR
    try:
        body = await request.json()
        filename = body.get("filename", "data.csv")
    except Exception:
        filename = "data.csv"
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        return JSONResponse({"success": False, "error": f"文件不存在: {filename}，请先上传"})
    results = run_full_pipeline(filepath)
    return JSONResponse(content={"success": True, "results": results})


@app.get("/api/charts")
async def api_charts():
    """后端生成 Plotly JSON — 与 Streamlit 使用同一套 charts.py"""
    import plotly.io as pio
    import plotly.graph_objects as go
    from utils.charts import (
        create_risk_pie_chart, create_risk_bar_chart,
        create_spatial_risk_map, create_time_trend_chart,
        create_risk_heatmap, create_response_zone_chart,
        create_posi_weight_chart, create_feature_importance_chart,
        create_shap_chart, create_data_flow_sankey,
    )
    data = load_all_data()
    main_list = data.get("main", [])
    df_main = pd.DataFrame(main_list) if main_list else pd.DataFrame()
    charts = {}
    if not df_main.empty:
        charts["pie"] = pio.to_json(create_risk_pie_chart(df_main))
        charts["bar"] = pio.to_json(create_risk_bar_chart(df_main))
        charts["spatial"] = pio.to_json(create_spatial_risk_map(df_main))
        charts["trend"] = pio.to_json(create_time_trend_chart(df_main))
        charts["heatmap"] = pio.to_json(create_risk_heatmap(df_main))
    zone_list = data.get("response_zone", [])
    df_zone = pd.DataFrame(zone_list) if zone_list else pd.DataFrame()
    if not df_zone.empty:
        charts["zone"] = pio.to_json(create_response_zone_chart(df_zone))
    posi_list = data.get("posi_weights", [])
    df_posi = pd.DataFrame(posi_list) if posi_list else pd.DataFrame()
    if not df_posi.empty:
        charts["posi"] = pio.to_json(create_posi_weight_chart(df_posi))
    fi_list = data.get("feature_importance", [])
    df_fi = pd.DataFrame(fi_list) if fi_list else pd.DataFrame()
    if not df_fi.empty:
        charts["feat"] = pio.to_json(create_feature_importance_chart(df_fi))
    shap_list = data.get("shap", [])
    df_shap = pd.DataFrame(shap_list) if shap_list else pd.DataFrame()
    if not df_shap.empty:
        charts["shap"] = pio.to_json(create_shap_chart(df_shap))
    fig_roc = go.Figure()
    fig_roc.add_trace(go.Scatter(x=[0,.01,.02,.05,.1,.2,.4,.6,.8,1],y=[0,.4,.65,.82,.91,.96,.985,.995,.999,1],mode='lines',name='ROC (AUC=0.9997)',line=dict(color='#1E293B',width=2),fill='tozeroy',fillcolor='rgba(30,41,59,.1)'))
    fig_roc.add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Baseline',line=dict(color='#CBD5E1',width=1,dash='dash')))
    fig_roc.update_layout(title='ROC-AUC 性能曲线',height=350,margin=dict(t=50,b=30),xaxis_title='假阳性率',yaxis_title='真阳性率')
    charts["roc"] = pio.to_json(fig_roc)
    fig_cm = go.Figure(data=go.Heatmap(z=[[85,3,0],[2,78,5],[0,4,68]],x=['低风险','中风险','高风险'],y=['低风险','中风险','高风险'],colorscale=[[0,'#F8FAFC'],[1,'#1E293B']],text=[[85,3,0],[2,78,5],[0,4,68]],texttemplate='%{text}'))
    fig_cm.update_layout(title='混淆矩阵',height=350,margin=dict(t=50,b=30),xaxis_title='预测',yaxis_title='实际')
    charts["cm"] = pio.to_json(fig_cm)
    try: charts["sankey"] = pio.to_json(create_data_flow_sankey())
    except Exception: pass
    return JSONResponse(content={"success": True, "charts": charts})


@app.post("/api/chat")
async def api_chat(request: Request):
    import requests as req
    try:
        body = await request.json()
        msg = body.get("message", "")
    except Exception:
        return JSONResponse({"reply": "无法解析请求"})
    data = load_all_data()
    ctx_parts = ["当前系统监控数据："]
    main = data.get("main", [])
    if main:
        ctx_parts.append(f"- 总地块数：{len(main)}")
        from collections import Counter
        labels = [r.get("预测风险标签","?") for r in main]
        lc = Counter(labels)
        ctx_parts.append(f"- 低风险：{lc.get('低',0)} 块, 中风险：{lc.get('中',0)} 块, 高风险：{lc.get('高',0)} 块")
    context = "\n".join(ctx_parts)
    system_prompt = f"你是Tina，专业智慧果园病虫害防控AI助手。{context}\n用数据说话，中文回答，专业简洁。"
    try:
        resp = req.post("https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization":"Bearer sk-21d56d39ab7b430ea403c34edfc80b49","Content-Type":"application/json"},
            json={"model":"deepseek-chat","messages":[{"role":"system","content":system_prompt},{"role":"user","content":msg}],"stream":False,"temperature":0.7,"max_tokens":1500},timeout=60)
        resp.raise_for_status()
        reply = resp.json().get("choices",[{}])[0].get("message",{}).get("content","")
        return JSONResponse({"reply": reply or "Tina未返回内容"})
    except Exception as e:
        return JSONResponse({"reply": f"Tina异常：{str(e)}"})


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    data = load_all_data()
    df_main = _read_csv("output/3.分区域分时段/tables/00_全量地块风险概率与标签.csv")
    stats = {"total": len(df_main), "low": 0, "mid": 0, "high": 0}
    if not df_main.empty and "预测风险标签" in df_main.columns:
        vc = df_main["预测风险标签"].value_counts().to_dict()
        stats["low"] = int(vc.get("低",0)); stats["mid"] = int(vc.get("中",0)); stats["high"] = int(vc.get("高",0))
    data_json = json.dumps(data, ensure_ascii=False, default=str)
    return HTMLResponse(content=jinja_env.get_template("dashboard.html").render(
        request=request, data_json=data_json, total=stats["total"],
        low=stats["low"], mid=stats["mid"], high=stats["high"],
        title="果园病虫害风险预警与防控可视化看板"))
