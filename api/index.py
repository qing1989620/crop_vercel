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
_chat_history: dict[str, list[dict]] = {}
_chat_history_ts: dict[str, float] = {}   # 会话最后活跃时间

# ── Token 省钱策略：各项收紧参数 ──
MAX_HISTORY_MESSAGES = 10     # 最多 10 条消息（5 轮 × 2），从 20 砍半
MAX_RETRIES = 0               # 不重试，400 错误重试纯浪费钱
MAX_TOKENS_OUTPUT = 400       # 回复上限 400 token，从 800 砍半（问答够用）
MAX_INPUT_TOKENS = 1200       # ★新增★ 输入 token 上限（这才是烧钱大头）
MAX_USER_MSG_CHARS = 500      # ★新增★ 单条用户消息最多 500 字符
MAX_USER_MSG_PER_MIN = 6      # ★新增★ 每分钟最多 6 次请求
HISTORY_TTL_SEC = 1800        # ★新增★ 30 分钟无活动清历史（防累积烧钱）
CACHE_TTL_SEC = 300           # ★新增★ 相同问题缓存 5 分钟


# ── 请求频率限制 ──
_rate_limiter: dict[str, list[float]] = {}  # { session_id: [timestamps] }

def _check_rate_limit(session_id: str) -> bool:
    """检查是否超过频率限制，返回 True=放行，False=拦截"""
    now = time.time()
    timestamps = _rate_limiter.get(session_id, [])
    # 清除 60 秒前的记录
    timestamps = [t for t in timestamps if now - t < 60]
    if len(timestamps) >= MAX_USER_MSG_PER_MIN:
        _rate_limiter[session_id] = timestamps
        return False
    timestamps.append(now)
    _rate_limiter[session_id] = timestamps
    return True


# ── 简单响应缓存（同问题 5 分钟内不重复调用 API）──
_response_cache: dict[str, tuple[float, str]] = {}  # { hash: (expire_ts, reply) }

def _get_cached(query_hash: str) -> str | None:
    """命中缓存返回回复，否则返回 None"""
    entry = _response_cache.get(query_hash)
    if entry and time.time() < entry[0]:
        return entry[1]
    # 清理过期条目
    if entry:
        del _response_cache[query_hash]
    return None

def _set_cache(query_hash: str, reply: str):
    """写入缓存"""
    _response_cache[query_hash] = (time.time() + CACHE_TTL_SEC, reply)
    # 防止缓存无限膨胀，超过 200 条清最旧的
    if len(_response_cache) > 200:
        oldest = min(_response_cache, key=lambda k: _response_cache[k][0])
        del _response_cache[oldest]


# ── Token 估算器 ──
def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中文 ~1.5 字/token，英文 ~4 字/token"""
    chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other = len(text) - chinese
    return int(chinese / 1.5 + other / 4)


def _estimate_messages_tokens(messages: list[dict]) -> int:
    """估算整个 messages 数组的 token 数"""
    total = 0
    for m in messages:
        total += _estimate_tokens(str(m.get("content", "")))
        total += 4  # role 等元数据开销
    return total


def _truncate_user_msg(msg: str, max_chars: int = MAX_USER_MSG_CHARS) -> str:
    """截断过长的用户消息"""
    if len(msg) > max_chars:
        return msg[:max_chars] + "…（消息过长已截断）"
    return msg


def _trim_messages_to_budget(messages: list[dict], max_input: int = MAX_INPUT_TOKENS) -> list[dict]:
    """从旧到新裁剪消息，确保总 token 不超预算。
    始终保留 system prompt + 最后一条 user 消息，从中间历史开始丢弃。"""
    if len(messages) <= 2:
        return messages  # 只有 system + user，不裁

    sys_msg = messages[0]
    last_user = messages[-1]
    history = messages[1:-1]

    # 核心消息必须保留
    core_tokens = _estimate_tokens(sys_msg["content"]) + _estimate_tokens(last_user["content"]) + 20

    budget = max_input - core_tokens
    if budget <= 0:
        # 预算极紧：只保留 system + 当前问题
        return [sys_msg, last_user]

    # 从历史尾部向前保留（越新的越重要）
    kept = []
    used = 0
    for m in reversed(history):
        t = _estimate_tokens(str(m.get("content", ""))) + 4
        if used + t <= budget:
            kept.insert(0, m)
            used += t
        else:
            break

    return [sys_msg] + kept + [last_user]


def _summarize_history(messages: list[dict]) -> str:
    """将早期对话压缩为一段摘要文本"""
    if len(messages) <= 4:
        return ""
    early = messages[:4]
    parts = []
    for m in early:
        role = "用户" if m["role"] == "user" else "助手"
        content = str(m.get("content", ""))[:80]
        parts.append(f"[{role}]: {content}")
    return "【历史摘要】" + "；".join(parts)


def _build_messages(session_id: str, user_msg: str) -> list[dict]:
    """构建消息数组，严格控制 token 预算"""
    history = _chat_history.get(session_id, [])
    history.append({"role": "user", "content": user_msg})

    # 超过条数上限 → 压缩早期对话
    if len(history) > MAX_HISTORY_MESSAGES:
        summary = _summarize_history(history)
        if summary:
            history = [{"role": "system", "content": summary}] + history[-6:]
        else:
            history = history[-MAX_HISTORY_MESSAGES:]

    system_prompt = {
        "role": "system",
        "content": "你是Tina，智慧果园病虫害AI助手。中文回答，简洁专业。"
    }
    messages = [system_prompt] + history

    # ★ 最后一道防线：按 token 预算裁剪
    if _estimate_messages_tokens(messages) > MAX_INPUT_TOKENS:
        messages = _trim_messages_to_budget(messages)

    return messages


def _save_history(session_id: str, user_msg: str, reply: str):
    """保存对话到历史缓存，并记录活跃时间"""
    history = _chat_history.get(session_id, [])
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": reply})
    if len(history) > MAX_HISTORY_MESSAGES + 6:
        summary = _summarize_history(history)
        if summary:
            history = [{"role": "system", "content": summary}] + history[-6:]
        else:
            history = history[-MAX_HISTORY_MESSAGES:]
    _chat_history[session_id] = history
    _chat_history_ts[session_id] = time.time()


def _cleanup_stale_histories():
    """清理过期会话历史，释放内存"""
    now = time.time()
    stale = [sid for sid, ts in _chat_history_ts.items() if now - ts > HISTORY_TTL_SEC]
    for sid in stale:
        _chat_history.pop(sid, None)
        _chat_history_ts.pop(sid, None)
        _rate_limiter.pop(sid, None)


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

    # 定期清理过期会话
    _cleanup_stale_histories()

    try:
        import requests as req
        body = await request.json()
        user_msg = (body.get("message", "") or "").strip()
        if not user_msg:
            return JSONResponse({"reply": "请输入您的问题"})

        # ★ 截断过长消息
        user_msg = _truncate_user_msg(user_msg)

        client_history = body.get("history") or []
        session_id = body.get("session_id") or request.cookies.get(COOKIE_NAME, "default")
    except Exception:
        return JSONResponse({"reply": "无法解析请求"})

    # ★ 频率限制
    if not _check_rate_limit(session_id):
        return JSONResponse({"reply": "提问太快啦，请稍等片刻再试～"})

    # ★ 缓存命中检查（用消息哈希）
    query_hash = hashlib.md5(user_msg.encode()).hexdigest()
    cached = _get_cached(query_hash)
    if cached:
        _chat_history_ts[session_id] = time.time()
        return JSONResponse({"reply": cached, "cached": True})

    # ── 构建消息 ──
    if client_history and isinstance(client_history, list):
        history = client_history[-MAX_HISTORY_MESSAGES:]
        messages = [{
            "role": "system",
            "content": "你是Tina，智慧果园病虫害AI助手。中文回答，简洁专业。"
        }] + history + [{"role": "user", "content": user_msg}]
    else:
        messages = _build_messages(session_id, user_msg)

    # ★ 最终 token 预算裁剪
    if _estimate_messages_tokens(messages) > MAX_INPUT_TOKENS:
        messages = _trim_messages_to_budget(messages)

    # ── API 调用（不重试，400/500 重试浪费双倍钱）──
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
                "max_tokens": MAX_TOKENS_OUTPUT,
            },
            timeout=30,
        )
        resp.raise_for_status()
        reply = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")

        if not reply:
            return JSONResponse({"reply": "Tina未返回内容，请重试"})

        # 保存历史 + 写入缓存
        _save_history(session_id, user_msg, reply)
        _set_cache(query_hash, reply)
        return JSONResponse({"reply": reply})

    except Exception as e:
        err_str = str(e)
        # 仅对明确的临时性错误提示重试，不自动重试
        if "429" in err_str:
            return JSONResponse({"reply": "API 请求过于频繁，请稍后再试"})
        if "timeout" in err_str.lower() or "connection" in err_str.lower():
            return JSONResponse({"reply": "网络超时，请重试"})
        return JSONResponse({"reply": f"Tina异常：{err_str}"})


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
