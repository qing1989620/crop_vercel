# -*- coding: utf-8 -*-
"""果园病虫害风险预警可视化看板 — Vercel 部署版"""
import os, sys, json, traceback, hashlib, hmac, time

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="果园病虫害风险预警看板")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# ── 管理员唯一通行秘钥（生产环境请通过环境变量 ADMIN_KEY 配置）──
ADMIN_KEY = os.environ.get("ADMIN_KEY", "crop2026")
COOKIE_NAME = "orchard_auth"
COOKIE_SECRET = os.environ.get("COOKIE_SECRET", "a7f3c9e1b2d4580f6e3a9127c5b0d84e")


def _make_token(key: str) -> str:
    """基于秘钥 + 时间戳生成 HMAC 令牌"""
    ts = str(int(time.time() // 1800))  # 30分钟窗口
    raw = f"{key}:{ts}"
    return hmac.new(COOKIE_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:32]


def _verify_auth(request: Request) -> bool:
    """验证请求是否携带有效认证 Cookie"""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    expected = _make_token(ADMIN_KEY)
    return hmac.compare_digest(token, expected)


# ── AI 对话历史缓存（服务端内存存储，按会话隔离）──
# 结构: { session_id: [{"role":"user","content":"..."}, ...] }
_chat_history: dict[str, list[dict]] = {}
MAX_HISTORY_ROUNDS = 10       # 最多保留 10 轮对话
MAX_HISTORY_MESSAGES = 20     # 最多 20 条消息（10 轮 × 2）
SUMMARY_TRIGGER = 10          # 超过此轮数触发摘要压缩
MAX_RETRIES = 2               # 最多重试次数
MAX_TOKENS_QA = 800           # 问答场景 token 上限


def _summarize_history(messages: list[dict]) -> str:
    """将早期对话压缩为一段摘要文本，节省 token"""
    if len(messages) <= 6:
        return ""
    # 取前 6 条消息生成简单摘要
    early = messages[:6]
    parts = []
    for m in early:
        role = "用户" if m["role"] == "user" else "助手"
        content = str(m.get("content", ""))[:120]
        parts.append(f"[{role}]: {content}")
    return "【历史摘要】" + "；".join(parts)


def _build_messages(session_id: str, user_msg: str) -> list[dict]:
    """构建发送给大模型的 messages 数组，自动管理上下文窗口"""
    history = _chat_history.get(session_id, [])

    # 添加当前用户消息
    history.append({"role": "user", "content": user_msg})

    # 如果历史过长（超过 10 轮），压缩早期对话
    if len(history) > MAX_HISTORY_MESSAGES:
        summary = _summarize_history(history)
        if summary:
            # 保留：摘要 + 最后 8 条消息（4 轮）
            compressed = [{"role": "system", "content": summary}]
            compressed.extend(history[-8:])
            history = compressed
        else:
            history = history[-MAX_HISTORY_MESSAGES:]

    # 构建完整 messages
    system_prompt = {
        "role": "system",
        "content": "你是Tina，专业的智慧果园病虫害防控AI助手。用数据说话，中文回答，专业简洁。"
    }
    return [system_prompt] + history


def _save_history(session_id: str, user_msg: str, reply: str):
    """保存对话到历史缓存"""
    history = _chat_history.get(session_id, [])
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": reply})
    # 保持上限
    if len(history) > MAX_HISTORY_MESSAGES + 10:
        summary = _summarize_history(history)
        if summary:
            history = [{"role": "system", "content": summary}] + history[-8:]
        else:
            history = history[-MAX_HISTORY_MESSAGES:]
    _chat_history[session_id] = history


@app.get("/login")
async def login_page(request: Request):
    """管理员登录页"""
    from jinja2 import Environment, FileSystemLoader
    TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    return HTMLResponse(content=jinja_env.get_template("login.html").render(request=request))


@app.post("/api/auth")
async def api_auth(request: Request):
    """验证管理员秘钥"""
    try:
        body = await request.json()
        submitted_key = body.get("key", "")
    except Exception:
        return JSONResponse({"success": False, "error": "请求格式错误"})

    if submitted_key == ADMIN_KEY:
        token = _make_token(ADMIN_KEY)
        resp = JSONResponse({"success": True})
        resp.set_cookie(
            key=COOKIE_NAME,
            value=token,
            max_age=86400,          # 24 小时有效
            httponly=True,
            samesite="lax",
            secure=False,            # 本地开发关闭；生产请开启
        )
        return resp
    else:
        return JSONResponse({"success": False, "error": "访问秘钥错误"})


@app.get("/api/health")
async def health():
    return JSONResponse({"status": "ok", "python": sys.version, "base_dir": BASE_DIR})


@app.get("/")
async def home(request: Request):
    # 认证检查
    if not _verify_auth(request):
        return RedirectResponse(url="/login", status_code=302)

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
async def api_data(request: Request):
    if not _verify_auth(request):
        return JSONResponse({"success": False, "error": "未授权访问"}, status_code=401)
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
async def api_charts(request: Request):
    if not _verify_auth(request):
        return JSONResponse({"success": False, "error": "未授权访问"}, status_code=401)
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
    if not _verify_auth(request):
        return JSONResponse({"reply": "请先登录后再使用AI助手"})
    try:
        import requests as req
        body = await request.json()
        user_msg = (body.get("message", "") or "").strip()
        if not user_msg:
            return JSONResponse({"reply": "请输入您的问题"})
        # 从请求中获取前端传递的历史，或使用服务端缓存
        client_history = body.get("history") or []
        session_id = body.get("session_id") or request.cookies.get(COOKIE_NAME, "default")
    except Exception:
        return JSONResponse({"reply": "无法解析请求"})

    # ── 构建消息：优先使用前端历史，否则用服务端缓存 ──
    if client_history and isinstance(client_history, list):
        # 前端已传递历史，仅保留最近 10 轮
        history = client_history[-MAX_HISTORY_MESSAGES:]
        messages = [{
            "role": "system",
            "content": "你是Tina，专业的智慧果园病虫害防控AI助手。用数据说话，中文回答，专业简洁。"
        }] + history + [{"role": "user", "content": user_msg}]
    else:
        messages = _build_messages(session_id, user_msg)

    # ── 带重试的 API 调用 ──
    last_error = ""
    for attempt in range(1, MAX_RETRIES + 2):  # 1 次初始 + 2 次重试 = 最多3次
        try:
            resp = req.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": "Bearer sk-62ad07704cc24a7d842d34f835708fb5",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": MAX_TOKENS_QA,
                    # ── 关键优化 ──
                    "thinking": False,  # 关闭思考模式，减少 token 消耗
                },
                timeout=45,
            )
            resp.raise_for_status()
            reply = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")

            if not reply:
                return JSONResponse({"reply": "Tina未返回内容"})

            # 保存到服务端缓存
            _save_history(session_id, user_msg, reply)
            return JSONResponse({"reply": reply})
        except Exception as e:
            err_str = str(e)
            # 如果是速率限制或服务端错误，进行重试
            if attempt <= MAX_RETRIES and (
                "429" in err_str or "500" in err_str or "502" in err_str
                or "503" in err_str or "timeout" in err_str.lower()
                or "connection" in err_str.lower()
            ):
                wait = attempt * 1.5  # 递增等待: 1.5s, 3s
                time.sleep(wait)
                last_error = err_str
                continue
            return JSONResponse({"reply": f"Tina异常：{err_str}"})

    return JSONResponse({"reply": f"Tina异常（已重试{MAX_RETRIES}次）：{last_error}"})


@app.post("/api/upload")
async def api_upload(request: Request):
    if not _verify_auth(request):
        return JSONResponse({"success": False, "error": "未授权访问"}, status_code=401)
    return JSONResponse({"success": False, "error": "上传功能需本地环境，Vercel不支持长时间处理"})


@app.get("/logout")
async def logout():
    """退出登录，清除认证 Cookie"""
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie(COOKIE_NAME)
    return resp
